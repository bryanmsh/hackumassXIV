# Databases

## Choose quickly
- In-memory list / JSON: disposable proof of concept.
- SQLite: local structured data, no service setup.
- Hosted Postgres: persistence/shared team access; configure credentials through env vars.

```python
import sqlite3
con = sqlite3.connect('demo.db')
con.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, title TEXT NOT NULL)')
con.execute('INSERT INTO events(title) VALUES (?)', ('Sample',))
con.commit()
print(con.execute('SELECT id,title FROM events').fetchall())
con.close()
```
Use parameterized SQL. For a 10-hour event, don't introduce a database unless it supports the demo.
