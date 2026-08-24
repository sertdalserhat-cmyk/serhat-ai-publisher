PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source (
  id             TEXT PRIMARY KEY,
  kind           TEXT NOT NULL,
  source_family  TEXT NOT NULL,
  url            TEXT,
  locale         TEXT,
  retrieved_at   TEXT NOT NULL,
  ingested_at    TEXT NOT NULL,
  raw_hash       TEXT NOT NULL UNIQUE,
  snapshot_path  TEXT NOT NULL,
  content_type   TEXT NOT NULL,
  byte_size      INTEGER NOT NULL,
  legal_status   TEXT NOT NULL,
  reliability    TEXT NOT NULL,
  ttl_days       INTEGER NOT NULL,
  collector      TEXT NOT NULL,
  supersedes_id  TEXT REFERENCES source(id),
  note           TEXT
);
CREATE INDEX IF NOT EXISTS ix_source_family ON source(source_family);
CREATE INDEX IF NOT EXISTS ix_source_retrieved ON source(retrieved_at);

CREATE TABLE IF NOT EXISTS opportunity (
  id            TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  channel       TEXT NOT NULL,
  product_type  TEXT NOT NULL,
  niche         TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'DRAFT',
  dedup_hash    TEXT NOT NULL UNIQUE,
  is_active     INTEGER NOT NULL DEFAULT 0,
  notes         TEXT,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_single_active
  ON opportunity(is_active) WHERE is_active = 1;

CREATE TABLE IF NOT EXISTS claim (
  id             TEXT PRIMARY KEY,
  source_id      TEXT NOT NULL REFERENCES source(id),
  opportunity_id TEXT REFERENCES opportunity(id),
  claim_type     TEXT NOT NULL,
  subject        TEXT NOT NULL,
  value_num      REAL,
  value_text     TEXT,
  unit           TEXT,
  market         TEXT,
  observed_at    TEXT NOT NULL,
  confidence     TEXT NOT NULL,
  extracted_by   TEXT NOT NULL,
  quote          TEXT,
  locator        TEXT,
  supersedes_id  TEXT REFERENCES claim(id),
  status         TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at     TEXT NOT NULL,
  CHECK (value_num IS NOT NULL OR value_text IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_claim_dedup
  ON claim(source_id, claim_type, subject, observed_at);
CREATE INDEX IF NOT EXISTS ix_claim_opp ON claim(opportunity_id);
CREATE INDEX IF NOT EXISTS ix_claim_type ON claim(claim_type);

CREATE TABLE IF NOT EXISTS decision_log (
  id          TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id   TEXT,
  actor       TEXT NOT NULL,
  action      TEXT NOT NULL,
  rationale   TEXT NOT NULL,
  created_at  TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS trg_decision_no_update
BEFORE UPDATE ON decision_log
BEGIN SELECT RAISE(ABORT, 'decision_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_decision_no_delete
BEFORE DELETE ON decision_log
BEGIN SELECT RAISE(ABORT, 'decision_log is append-only'); END;

CREATE TABLE IF NOT EXISTS llm_call (
  id           TEXT PRIMARY KEY,
  task_key     TEXT NOT NULL,
  model        TEXT NOT NULL,
  in_tokens    INTEGER NOT NULL,
  out_tokens   INTEGER NOT NULL,
  cost_usd     REAL NOT NULL,
  pricing_ver  TEXT NOT NULL,
  schema_valid INTEGER NOT NULL,
  retry_count  INTEGER NOT NULL DEFAULT 0,
  input_hash   TEXT NOT NULL,
  created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_blueprint (
  opportunity_id    TEXT PRIMARY KEY REFERENCES opportunity(id),
  audience          TEXT NOT NULL,
  customer_problem  TEXT NOT NULL,
  product_promise   TEXT NOT NULL,
  age_min           INTEGER NOT NULL,
  age_max           INTEGER NOT NULL,
  page_count        INTEGER NOT NULL,
  activity_count    INTEGER NOT NULL,
  differentiator    TEXT NOT NULL,
  target_price      REAL NOT NULL,
  currency          TEXT NOT NULL,
  content_structure TEXT NOT NULL,
  ip_review_status  TEXT NOT NULL DEFAULT 'PENDING',
  version           INTEGER NOT NULL DEFAULT 1,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  CHECK (age_min >= 0 AND age_max >= age_min),
  CHECK (page_count > 0 AND activity_count > 0),
  CHECK (target_price > 0),
  CHECK (ip_review_status IN ('PENDING','PASS','HOLD','REJECT'))
);
