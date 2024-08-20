PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 1000000000;
PRAGMA foreign_keys = true;
PRAGMA temp_store = memory;

CREATE TABLE IF NOT EXISTS polls (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' ||
                                 substr(lower(hex(randomblob(2))), 1, 4) || '-' ||
                                 substr('4' || substr(lower(hex(randomblob(2))), 2, 3), 1, 4) || '-' ||
                                 substr(hex((random() & 0x3fff) | 0x8000), 1, 4) || '-' ||
                                 lower(hex(randomblob(6)))),
    title TEXT NOT NULL,
    description TEXT,
    pub_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_name TEXT NOT NULL,
    author_email TEXT,
    manage_code TEXT DEFAULT (lower(hex(randomblob(4))) || '-' ||
                              substr(lower(hex(randomblob(2))), 1, 4) || '-' ||
                              substr('4' || substr(lower(hex(randomblob(2))), 2, 3), 1, 4) || '-' ||
                              substr(hex((random() & 0x3fff) | 0x8000), 1, 4) || '-' ||
                              lower(hex(randomblob(6)))),
    whole_day INTEGER NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS choices (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' ||
                                 substr(lower(hex(randomblob(2))), 1, 4) || '-' ||
                                 substr('4' || substr(lower(hex(randomblob(2))), 2, 3), 1, 4) || '-' ||
                                 substr(hex((random() & 0x3fff) | 0x8000), 1, 4) || '-' ||
                                 lower(hex(randomblob(6)))),
    poll_id TEXT NOT NULL,
    start_datetime TEXT NOT NULL,
    end_datetime TEXT NOT NULL,
    FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE
) STRICT;

CREATE TABLE IF NOT EXISTS votes (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' ||
                                 substr(lower(hex(randomblob(2))), 1, 4) || '-' ||
                                 substr('4' || substr(lower(hex(randomblob(2))), 2, 3), 1, 4) || '-' ||
                                 substr(hex((random() & 0x3fff) | 0x8000), 1, 4) || '-' ||
                                 lower(hex(randomblob(6)))),
    manage_code TEXT DEFAULT (lower(hex(randomblob(4))) || '-' ||
                              substr(lower(hex(randomblob(2))), 1, 4) || '-' ||
                              substr('4' || substr(lower(hex(randomblob(2))), 2, 3), 1, 4) || '-' ||
                              substr(hex((random() & 0x3fff) | 0x8000), 1, 4) || '-' ||
                              lower(hex(randomblob(6)))),
    poll_id TEXT NOT NULL,
    choice_id TEXT NOT NULL,
    voter_name TEXT NOT NULL,
    value INTEGER NOT NULL,
    UNIQUE (poll_id, choice_id, voter_name),
    FOREIGN KEY (choice_id) REFERENCES choices (id) ON DELETE CASCADE,
    FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE
) STRICT;

CREATE INDEX IF NOT EXISTS idx_votes_poll_id_voter_name ON votes (poll_id, voter_name);
CREATE INDEX IF NOT EXISTS idx_choices_poll_id_start_datetime ON choices (poll_id, start_datetime);
CREATE INDEX IF NOT EXISTS idx_votes_choice_id ON votes (choice_id);
CREATE INDEX IF NOT EXISTS idx_votes_manage_code ON votes (manage_code);
CREATE INDEX IF NOT EXISTS idx_polls_manage_code_pub_date ON polls (manage_code, pub_date);
