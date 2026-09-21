ALTER TABLE identity.operator_user DROP CONSTRAINT uq_operator_user_max_user_id;

-- statement-breakpoint

ALTER TABLE identity.operator_user DROP COLUMN max_user_id;
