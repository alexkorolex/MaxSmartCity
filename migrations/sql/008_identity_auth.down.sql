ALTER TABLE identity.organization_member DROP CONSTRAINT fk_organization_member_department_id_department;

-- statement-breakpoint

DROP INDEX identity.ix_identity_organization_member_department_id;

-- statement-breakpoint

ALTER TABLE identity.organization_member DROP COLUMN department_id;

-- statement-breakpoint

ALTER TABLE identity.operator_user DROP CONSTRAINT uq_operator_user_keycloak_subject;

-- statement-breakpoint

ALTER TABLE identity.operator_user DROP COLUMN keycloak_subject;

-- statement-breakpoint

DROP INDEX identity.ix_identity_department_organization_id;

-- statement-breakpoint

DROP TABLE identity.department;
