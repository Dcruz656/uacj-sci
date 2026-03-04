-- Schema SQLite (local dev)
CREATE TABLE IF NOT EXISTS researchers (
    id TEXT PRIMARY KEY,
    orcid TEXT UNIQUE,
    openalex_id TEXT,
    full_name TEXT NOT NULL,
    works_count INTEGER DEFAULT 0,
    cited_by_count INTEGER DEFAULT 0,
    h_index INTEGER DEFAULT 0,
    institution TEXT DEFAULT 'UACJ',
    last_synced_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY,
    doi TEXT,
    title TEXT,
    publication_year INTEGER,
    type TEXT,
    is_oa INTEGER DEFAULT 0,
    oa_type TEXT,
    cited_by_count INTEGER DEFAULT 0,
    openalex_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS authorships (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    researcher_id TEXT REFERENCES researchers(id),
    affiliation_status TEXT,
    raw_affiliation_string TEXT,
    verified_by TEXT,
    verified_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(work_id, researcher_id)
);

CREATE TABLE IF NOT EXISTS sdg_classifications (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    sdg_number INTEGER,
    sdg_label TEXT,
    confidence REAL,
    method TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(work_id, sdg_number)
);

CREATE TABLE IF NOT EXISTS apc_payments (
    id TEXT PRIMARY KEY,
    work_id TEXT REFERENCES works(id),
    amount_usd REAL,
    amount_mxn REAL,
    is_estimated INTEGER DEFAULT 1,
    estimation_basis TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
