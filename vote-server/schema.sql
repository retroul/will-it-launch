-- Game requests and votes. Voters are stored only as a salted hash of their IP.
CREATE TABLE IF NOT EXISTS requests (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT    NOT NULL,
  slug       TEXT    NOT NULL UNIQUE,
  created_by TEXT    NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS votes (
  request_id INTEGER NOT NULL,
  voter      TEXT    NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (request_id, voter)
);

CREATE INDEX IF NOT EXISTS requests_by_creator ON requests (created_by, created_at);
