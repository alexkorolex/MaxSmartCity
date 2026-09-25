DELETE FROM notifications.notification WHERE type = 'CHAT_MESSAGE';

-- statement-breakpoint

ALTER TABLE notifications.notification DROP CONSTRAINT ck_notification_notification_type;

-- statement-breakpoint

ALTER TABLE notifications.notification ADD CONSTRAINT ck_notification_notification_type
    CHECK (type IN ('REPORT_STATUS_CHANGED', 'INCIDENT_STATUS_CHANGED', 'RESOLUTION_REQUESTED', 'NEWS', 'GENERIC'));

-- statement-breakpoint

DROP TABLE reports.report_message;
