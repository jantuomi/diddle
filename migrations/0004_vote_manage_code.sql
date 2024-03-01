ALTER TABLE votes ADD COLUMN manage_code uuid DEFAULT uuid_generate_v4();
