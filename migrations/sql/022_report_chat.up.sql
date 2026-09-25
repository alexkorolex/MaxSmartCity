CREATE TABLE reports.report_message (
	id UUID NOT NULL,
	report_id UUID NOT NULL,
	author_type VARCHAR(8) NOT NULL,
	author_resident_id UUID,
	author_operator_id UUID,
	organization_id UUID,
	text TEXT NOT NULL,
	read_at TIMESTAMP WITH TIME ZONE,
	notified_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	sa_orm_sentinel INTEGER,
	CONSTRAINT pk_report_message PRIMARY KEY (id),
	CONSTRAINT ck_report_message_author_present CHECK ((author_type = 'RESIDENT' AND author_resident_id IS NOT NULL) OR (author_type = 'OPERATOR' AND author_operator_id IS NOT NULL)),
	CONSTRAINT fk_report_message_report_id_report FOREIGN KEY(report_id) REFERENCES reports.report (id),
	CONSTRAINT ck_report_message_report_message_author_type CHECK (author_type IN ('RESIDENT', 'OPERATOR', 'SERVICE', 'SYSTEM')),
	CONSTRAINT fk_report_message_author_resident_id_resident FOREIGN KEY(author_resident_id) REFERENCES identity.resident (id),
	CONSTRAINT fk_report_message_author_operator_id_operator_user FOREIGN KEY(author_operator_id) REFERENCES identity.operator_user (id),
	CONSTRAINT fk_report_message_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id)
);

-- statement-breakpoint

CREATE INDEX ix_report_message_report_created ON reports.report_message (report_id, created_at);

-- statement-breakpoint

CREATE INDEX ix_report_message_pending_notification ON reports.report_message (created_at) WHERE read_at IS NULL AND notified_at IS NULL;

-- statement-breakpoint

ALTER TABLE notifications.notification DROP CONSTRAINT ck_notification_notification_type;

-- statement-breakpoint

ALTER TABLE notifications.notification ADD CONSTRAINT ck_notification_notification_type
    CHECK (type IN ('REPORT_STATUS_CHANGED', 'INCIDENT_STATUS_CHANGED', 'RESOLUTION_REQUESTED', 'NEWS', 'CHAT_MESSAGE', 'GENERIC'));
