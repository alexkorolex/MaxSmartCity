CREATE TABLE identity.department (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	code VARCHAR(64) NOT NULL,
	name VARCHAR(255) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	sa_orm_sentinel INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_department PRIMARY KEY (id),
	CONSTRAINT fk_department_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id),
	CONSTRAINT uq_department_organization_code UNIQUE (organization_id, code)
);

-- statement-breakpoint

CREATE INDEX ix_identity_department_organization_id ON identity.department (organization_id);

-- statement-breakpoint

ALTER TABLE identity.operator_user ADD COLUMN keycloak_subject VARCHAR(64);

-- statement-breakpoint

ALTER TABLE identity.operator_user ADD CONSTRAINT uq_operator_user_keycloak_subject UNIQUE (keycloak_subject);

-- statement-breakpoint

ALTER TABLE identity.organization_member ADD COLUMN department_id UUID;

-- statement-breakpoint

CREATE INDEX ix_identity_organization_member_department_id ON identity.organization_member (department_id);

-- statement-breakpoint

ALTER TABLE identity.organization_member ADD CONSTRAINT fk_organization_member_department_id_department FOREIGN KEY(department_id) REFERENCES identity.department (id);
