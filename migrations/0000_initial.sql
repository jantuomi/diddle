CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS polls (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    pub_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    author_name TEXT NOT NULL,
    author_email TEXT,
    manage_code uuid DEFAULT uuid_generate_v4()
);

CREATE TABLE IF NOT EXISTS choices (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    poll_id uuid NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS votes (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    poll_id uuid NOT NULL,
    choice_id uuid NOT NULL,
    voter_name TEXT NOT NULL,
    FOREIGN KEY (choice_id) REFERENCES choices (id) ON DELETE CASCADE,
    FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE
);
