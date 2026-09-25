ALTER TABLE identity.resident ADD COLUMN max_chat_id BIGINT;

-- statement-breakpoint

ALTER TABLE notifications.notification ADD COLUMN pushed_at TIMESTAMP WITH TIME ZONE;

-- statement-breakpoint

-- Notifications created before the push existed are not sent to MAX retroactively.
UPDATE notifications.notification SET pushed_at = created_at;

-- statement-breakpoint

CREATE INDEX ix_notification_pending_push ON notifications.notification (created_at) WHERE pushed_at IS NULL;
