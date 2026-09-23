CREATE SCHEMA notifications;

-- statement-breakpoint

CREATE TABLE notifications.notification (
	id UUID NOT NULL,
	resident_id UUID NOT NULL,
	type VARCHAR(23) NOT NULL,
	title VARCHAR(255) NOT NULL,
	body TEXT NOT NULL,
	incident_id UUID,
	report_id UUID,
	is_read BOOLEAN DEFAULT false NOT NULL,
	read_at TIMESTAMP WITH TIME ZONE,
	sa_orm_sentinel INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_notification PRIMARY KEY (id),
	CONSTRAINT fk_notification_resident_id_resident FOREIGN KEY(resident_id) REFERENCES identity.resident (id),
	CONSTRAINT ck_notification_notification_type CHECK (type IN ('REPORT_STATUS_CHANGED', 'INCIDENT_STATUS_CHANGED', 'RESOLUTION_REQUESTED', 'NEWS', 'GENERIC')),
	CONSTRAINT fk_notification_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id),
	CONSTRAINT fk_notification_report_id_report FOREIGN KEY(report_id) REFERENCES reports.report (id)
);

-- statement-breakpoint

CREATE INDEX ix_notifications_notification_resident_id ON notifications.notification (resident_id);
