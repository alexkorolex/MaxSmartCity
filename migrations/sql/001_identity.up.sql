CREATE SCHEMA identity;

-- statement-breakpoint

CREATE TABLE identity.operator_user (
	id UUID NOT NULL, 
	login VARCHAR(255) NOT NULL, 
	display_name VARCHAR(255) NOT NULL, 
	email VARCHAR(255), 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_operator_user PRIMARY KEY (id), 
	CONSTRAINT uq_operator_user_login UNIQUE (login)
);

-- statement-breakpoint

CREATE TABLE identity.organization (
	id UUID NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	type VARCHAR(14) NOT NULL, 
	enabled BOOLEAN DEFAULT true NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_organization PRIMARY KEY (id), 
	CONSTRAINT uq_organization_code UNIQUE (code), 
	CONSTRAINT ck_organization_organization_type CHECK (type IN ('ADMINISTRATION', 'POWER_GRID', 'WATER_UTILITY', 'EMERGENCY'))
);

-- statement-breakpoint

CREATE TABLE identity.permission (
	id UUID NOT NULL, 
	code VARCHAR(128) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	CONSTRAINT pk_permission PRIMARY KEY (id), 
	CONSTRAINT uq_permission_code UNIQUE (code)
);

-- statement-breakpoint

CREATE TABLE identity.resident (
	id UUID NOT NULL, 
	max_user_id BIGINT, 
	username VARCHAR(255), 
	display_name VARCHAR(255), 
	bot_status VARCHAR(7) DEFAULT 'STARTED' NOT NULL, 
	notifications_enabled BOOLEAN DEFAULT true NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_resident PRIMARY KEY (id), 
	CONSTRAINT uq_resident_max_user_id UNIQUE (max_user_id), 
	CONSTRAINT ck_resident_resident_bot_status CHECK (bot_status IN ('STARTED', 'STOPPED'))
);

-- statement-breakpoint

CREATE TABLE identity.role (
	id UUID NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	CONSTRAINT pk_role PRIMARY KEY (id), 
	CONSTRAINT uq_role_code UNIQUE (code)
);

-- statement-breakpoint

CREATE TABLE identity.organization_member (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role_id UUID NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_organization_member PRIMARY KEY (id), 
	CONSTRAINT uq_organization_member_organization_user UNIQUE (organization_id, user_id), 
	CONSTRAINT uq_organization_member_context UNIQUE (id, organization_id), 
	CONSTRAINT fk_organization_member_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id), 
	CONSTRAINT fk_organization_member_user_id_operator_user FOREIGN KEY(user_id) REFERENCES identity.operator_user (id), 
	CONSTRAINT fk_organization_member_role_id_role FOREIGN KEY(role_id) REFERENCES identity.role (id)
);

-- statement-breakpoint

CREATE INDEX ix_identity_organization_member_organization_id ON identity.organization_member (organization_id);

-- statement-breakpoint

CREATE INDEX ix_identity_organization_member_role_id ON identity.organization_member (role_id);

-- statement-breakpoint

CREATE INDEX ix_identity_organization_member_user_id ON identity.organization_member (user_id);

-- statement-breakpoint

CREATE TABLE identity.role_permission (
	role_id UUID NOT NULL, 
	permission_id UUID NOT NULL, 
	CONSTRAINT pk_role_permission PRIMARY KEY (role_id, permission_id), 
	CONSTRAINT fk_role_permission_role_id_role FOREIGN KEY(role_id) REFERENCES identity.role (id), 
	CONSTRAINT fk_role_permission_permission_id_permission FOREIGN KEY(permission_id) REFERENCES identity.permission (id)
);
