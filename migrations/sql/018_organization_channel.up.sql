CREATE TABLE notifications.organization_channel (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	type VARCHAR(11) NOT NULL,
	target TEXT,
	secret VARCHAR(255),
	is_active BOOLEAN DEFAULT true NOT NULL,
	sa_orm_sentinel INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_organization_channel PRIMARY KEY (id),
	CONSTRAINT fk_organization_channel_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id),
	CONSTRAINT ck_organization_channel_organization_channel_type CHECK (type IN ('MAX_MEMBERS', 'MAX_CHAT', 'EMAIL', 'WEBHOOK'))
);

-- statement-breakpoint

CREATE INDEX ix_notifications_organization_channel_organization_id ON notifications.organization_channel (organization_id);
