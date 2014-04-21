ALTER TABLE contests
ADD COLUMN max_printouts INTEGER;

UPDATE contests SET
max_printouts = 0;

ALTER TABLE contests
ALTER COLUMN max_printouts SET NOT NULL;

ALTER TABLE contests
ADD CONSTRAINT contests_max_printouts_check
CHECK (max_printouts >= 0);


CREATE TABLE IF NOT EXISTS printouts (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	filename VARCHAR NOT NULL,
	digest VARCHAR NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY (user_id) REFERENCES users(id)
	ON UPDATE CASCADE ON DELETE CASCADE
);
