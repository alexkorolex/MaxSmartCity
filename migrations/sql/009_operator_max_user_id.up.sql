ALTER TABLE identity.operator_user ADD COLUMN max_user_id BIGINT;

-- statement-breakpoint

ALTER TABLE identity.operator_user ADD CONSTRAINT uq_operator_user_max_user_id UNIQUE (max_user_id);
