ALTER TABLE votes ADD CONSTRAINT idx_votes_unique_voter_name UNIQUE (poll_id, choice_id, voter_name);

CREATE INDEX idx_votes_manage_code ON votes (manage_code);
CREATE INDEX idx_polls_manage_code_pub_date ON polls (manage_code, pub_date);
