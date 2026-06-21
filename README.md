# autocomplete

A Python library for autocomplete functionality.

## Installation

```bash
pip install autocomplete
```

The base install has no third-party dependencies. Storage bridges are opt-in extras.

### Optional backends

| Extra | Installs | Bridge |
|-------|----------|--------|
| `redis7` | `redis` 5.x | Plain Redis 7.x (sorted sets, etc.) |
| `redis8` | `redis` 6.x+ | Plain Redis 8.x |
| `redisearch` | _(nothing extra)_ | RediSearch `FT.SUG*` bridge |
| `sqlalchemy` | `sqlalchemy` 2.x | SQL-backed storage |

```bash
# Plain Redis bridges
pip install "autocomplete[redis7]"
pip install "autocomplete[redis8]"

# SQL bridge
pip install "autocomplete[sqlalchemy]"

# RediSearch bridge (must combine with a redis extra)
pip install "autocomplete[redis7,redisearch]"
pip install "autocomplete[redis8,redisearch]"

# Multiple bridges
pip install "autocomplete[redis8,redisearch,sqlalchemy]"
```

Notes:

- `redis7` and `redis8` are mutually exclusive — they pin different `redis` major lines. Pick one based on your Redis server version; do not install both.
- `redisearch` is separate from `redis7`/`redis8` — it does not pull in redis-py by itself. Always combine it with `redis7` or `redis8`.
- `redisearch` requires RediSearch on the server — the extra only enables the Python bridge. Your Redis instance must have search available (Redis Stack / module on Redis 7, or built-in on Redis 8).
- `sqlalchemy` composes freely — it can be installed alongside either redis extra and/or `redisearch`.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Build and publish

```bash
python -m build
twine check dist/*
twine upload dist/*
```
