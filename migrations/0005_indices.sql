ALTER TABLE votes ADD CONSTRAINT idx_votes_unique_voter_name UNIQUE (poll_id, choice_id, voter_name);

CREATE INDEX idx_votes_poll_id_voter_name ON votes (poll_id, voter_name);
CREATE INDEX idx_choices_poll_id_start_datetime ON choices (poll_id, start_datetime);
CREATE INDEX idx_votes_choice_id ON votes (choice_id);
CREATE INDEX idx_votes_manage_code ON votes (manage_code);
CREATE INDEX idx_polls_manage_code_pub_date ON polls (manage_code, pub_date);
