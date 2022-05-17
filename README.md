# arango_wal

[![Build](https://github.com/adolfosilva/arango_wal/actions/workflows/python-test.yaml/badge.svg?branch=main)](https://github.com/adolfosilva/arango_wal/actions/workflows/python-test.yaml)

Listen to ArangoDB's WAL changes.

## Example

```python
from arango_wal import ArangoWAL

wal = ArangoWAL("http://localhost:8529")

wal.subscribe("users", lambda event, data: print(event))

wal.start()

wal.on('error', print)
```

## License

Distributed under the MIT license. See [LICENSE](./LICENSE) for details.
