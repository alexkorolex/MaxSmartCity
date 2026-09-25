DROP INDEX notifications.ix_notification_pending_push;

-- statement-breakpoint

ALTER TABLE notifications.notification DROP COLUMN pushed_at;

-- statement-breakpoint

ALTER TABLE identity.resident DROP COLUMN max_chat_id;
