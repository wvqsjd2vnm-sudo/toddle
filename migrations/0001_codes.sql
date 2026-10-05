CREATE TABLE IF NOT EXISTS codes (
  code    TEXT PRIMARY KEY,
  label   TEXT NOT NULL DEFAULT '',
  used_at INTEGER,          -- unix ms of redemption, NULL = still unused
  used_ua TEXT,             -- browser of the redeemer (for your own checking)
  used_ip TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
  ip TEXT NOT NULL,
  at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_ip ON attempts(ip, at);
