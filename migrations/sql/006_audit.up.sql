CREATE SCHEMA audit;

-- statement-breakpoint

CREATE TABLE audit.audit_log (
	id UUID NOT NULL, 
	entity_type VARCHAR(128) NOT NULL, 
	entity_id UUID NOT NULL, 
	action VARCHAR(128) NOT NULL, 
	old_values JSONB, 
	new_values JSONB, 
	actor_type VARCHAR(8) NOT NULL, 
	actor_id UUID, 
	request_id UUID, 
	entity_version INTEGER, 
	reason TEXT, 
	technical_source VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_audit_log PRIMARY KEY (id), 
	CONSTRAINT ck_audit_log_audit_actor_type CHECK (actor_type IN ('RESIDENT', 'OPERATOR', 'SERVICE', 'SYSTEM'))
);

-- statement-breakpoint

CREATE INDEX ix_audit_audit_log_entity_id ON audit.audit_log (entity_id);

-- statement-breakpoint

CREATE INDEX ix_audit_audit_log_entity_type ON audit.audit_log (entity_type);

-- statement-breakpoint

CREATE INDEX ix_audit_audit_log_request_id ON audit.audit_log (request_id);
