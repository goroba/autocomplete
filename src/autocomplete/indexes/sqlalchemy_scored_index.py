from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select, update

from autocomplete.click_buffers import ClickBuffer, NoopClickBuffer
from autocomplete.indexes import Index
from autocomplete.metadata import MetadataStorage, NullMetadataStorage
from autocomplete.normalizers import NoopNormalizer, Normalizer
from autocomplete.schemas.sqlalchemy import dialect_insert, prefix_table, vocabulary_table
from autocomplete.tokenizers import NoopTokenizer, Tokenizer

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


class SqlAlchemyScoredIndex(Index):
    def __init__(
        self,
        name: str,
        engine: Engine,
        *,
        top_n: int = 5,
        trim: bool = True,
        normalizer: Normalizer | None = None,
        tokenizer: Tokenizer | None = None,
        metadata_storage: MetadataStorage | None = None,
        click_buffer: ClickBuffer | None = None,
    ) -> None:
        self.name = name
        self.engine = engine
        self.top_n = top_n
        self.trim = trim
        self.normalizer = normalizer or NoopNormalizer()
        self.tokenizer = tokenizer or NoopTokenizer()
        self.metadata_storage = metadata_storage or NullMetadataStorage()
        self.click_buffer = click_buffer or NoopClickBuffer()

    def _upsert_vocabulary(
        self,
        conn: Connection,
        text: str,
        score: float,
    ) -> None:
        stmt = (
            dialect_insert(conn, vocabulary_table)
            .values(index_name=self.name, text=text, score=score)
            .on_conflict_do_update(
                index_elements=[
                    vocabulary_table.c.index_name,
                    vocabulary_table.c.text,
                ],
                set_={"score": score},
            )
        )
        conn.execute(stmt)

    def _upsert_prefix(
        self,
        conn: Connection,
        prefix: str,
        text: str,
        score: float,
    ) -> None:
        stmt = (
            dialect_insert(conn, prefix_table)
            .values(
                index_name=self.name,
                prefix=prefix,
                text=text,
                score=score,
            )
            .on_conflict_do_update(
                index_elements=[
                    prefix_table.c.index_name,
                    prefix_table.c.prefix,
                    prefix_table.c.text,
                ],
                set_={"score": score},
            )
        )
        conn.execute(stmt)

    def _get_vocabulary_score(
        self,
        conn: Connection,
        text: str,
    ) -> float | None:
        return conn.execute(
            select(vocabulary_table.c.score).where(
                vocabulary_table.c.index_name == self.name,
                vocabulary_table.c.text == text,
            )
        ).scalar_one_or_none()

    def _trim_prefix_set(self, conn: Connection, prefix: str) -> None:
        if not self.trim:
            return

        ranked = (
            select(
                prefix_table.c.text,
                func.row_number()
                .over(order_by=prefix_table.c.score.desc())
                .label("rn"),
            )
            .where(
                prefix_table.c.index_name == self.name,
                prefix_table.c.prefix == prefix,
            )
            .subquery()
        )
        conn.execute(
            delete(prefix_table).where(
                prefix_table.c.index_name == self.name,
                prefix_table.c.prefix == prefix,
                prefix_table.c.text.in_(
                    select(ranked.c.text).where(ranked.c.rn > self.top_n)
                ),
            )
        )

    def _rebuild_prefix_set(self, conn: Connection, prefix: str) -> None:
        if not self.trim:
            return

        upper = prefix + "\xff"
        members = conn.execute(
            select(vocabulary_table.c.text, vocabulary_table.c.score)
            .where(
                vocabulary_table.c.index_name == self.name,
                vocabulary_table.c.text >= prefix,
                vocabulary_table.c.text < upper,
            )
            .order_by(vocabulary_table.c.score.desc())
            .limit(self.top_n)
        ).all()

        conn.execute(
            delete(prefix_table).where(
                prefix_table.c.index_name == self.name,
                prefix_table.c.prefix == prefix,
            )
        )
        for member in members:
            conn.execute(
                dialect_insert(conn, prefix_table)
                .values(
                    index_name=self.name,
                    prefix=prefix,
                    text=member.text,
                    score=member.score,
                )
                .on_conflict_do_update(
                    index_elements=[
                        prefix_table.c.index_name,
                        prefix_table.c.prefix,
                        prefix_table.c.text,
                    ],
                    set_={"score": member.score},
                )
            )

    def _store_prefixes(
        self,
        conn: Connection,
        normalized_text: str,
        score: float,
    ) -> None:
        for token in self.tokenizer.tokenize(normalized_text):
            for i in range(len(token), 0, -1):
                prefix = token[:i]
                self._upsert_prefix(conn, prefix, normalized_text, score)
                self._trim_prefix_set(conn, prefix)

    def _apply_score_delta(
        self,
        conn: Connection,
        normalized_text: str,
        delta_score: float,
    ) -> None:
        conn.execute(
            update(vocabulary_table)
            .where(
                vocabulary_table.c.index_name == self.name,
                vocabulary_table.c.text == normalized_text,
            )
            .values(score=vocabulary_table.c.score + delta_score)
        )
        score = self._get_vocabulary_score(conn, normalized_text)
        if score is None:
            return
        for token in self.tokenizer.tokenize(normalized_text):
            for i in range(len(token), 0, -1):
                prefix = token[:i]
                self._upsert_prefix(conn, prefix, normalized_text, score)
                if delta_score < 0:
                    self._rebuild_prefix_set(conn, prefix)
                else:
                    self._trim_prefix_set(conn, prefix)

    def store(
        self,
        text: str,
        *,
        score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        member_score = score if score is not None else 0
        normalized_text = self.normalizer.normalize(text)

        with self.engine.begin() as conn:
            self._upsert_vocabulary(conn, normalized_text, member_score)
            self._store_prefixes(conn, normalized_text, member_score)

        if metadata is not None:
            self.metadata_storage.set(normalized_text, metadata)

    def search(self, query: str) -> list[tuple[str, float, dict[str, Any]]]:
        normalized_query = self.normalizer.normalize(query)
        tokens = self.tokenizer.tokenize(normalized_query)
        if not tokens:
            return []

        with self.engine.connect() as conn:
            if len(tokens) == 1:
                results = conn.execute(
                    select(prefix_table.c.text, prefix_table.c.score)
                    .where(
                        prefix_table.c.index_name == self.name,
                        prefix_table.c.prefix == tokens[0],
                    )
                    .order_by(prefix_table.c.score.desc())
                    .limit(self.top_n)
                ).all()
            else:
                results = conn.execute(
                    select(
                        prefix_table.c.text,
                        func.max(prefix_table.c.score).label("score"),
                    )
                    .where(
                        prefix_table.c.index_name == self.name,
                        prefix_table.c.prefix.in_(tokens),
                    )
                    .group_by(prefix_table.c.text)
                    .having(
                        func.count(func.distinct(prefix_table.c.prefix))
                        == len(tokens)
                    )
                    .order_by(func.max(prefix_table.c.score).desc())
                    .limit(self.top_n)
                ).all()

        return [
            (row.text, row.score, self.metadata_storage.get(row.text) or {})
            for row in results
        ]

    def click(self, text: str, *, clicks: int = 1) -> None:
        self.click_buffer.click(text, clicks=clicks)

    def rescore(self, text: str, delta_score: float) -> None:
        normalized_text = self.normalizer.normalize(text)
        with self.engine.begin() as conn:
            self._apply_score_delta(conn, normalized_text, delta_score)

    def flush(self) -> None:
        for text, delta_score in self.click_buffer.flush():
            normalized_text = self.normalizer.normalize(text)
            with self.engine.begin() as conn:
                self._apply_score_delta(conn, normalized_text, delta_score)

    def delete(self, text: str) -> None:
        normalized_text = self.normalizer.normalize(text)
        with self.engine.begin() as conn:
            conn.execute(
                delete(vocabulary_table).where(
                    vocabulary_table.c.index_name == self.name,
                    vocabulary_table.c.text == normalized_text,
                )
            )
            for token in self.tokenizer.tokenize(normalized_text):
                for i in range(len(token), 0, -1):
                    prefix = token[:i]
                    conn.execute(
                        delete(prefix_table).where(
                            prefix_table.c.index_name == self.name,
                            prefix_table.c.prefix == prefix,
                            prefix_table.c.text == normalized_text,
                        )
                    )
                    self._rebuild_prefix_set(conn, prefix)
        self.metadata_storage.delete(normalized_text)
