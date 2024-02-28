CREATE INDEX IF NOT EXISTS idx_votes_poll_id_voter_name ON votes (poll_id, voter_name);
CREATE INDEX IF NOT EXISTS idx_choices_poll_id_start_datetime ON choices (poll_id, start_datetime);
CREATE INDEX IF NOT EXISTS idx_votes_choice_id ON votes (choice_id);
