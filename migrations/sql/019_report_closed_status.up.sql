ALTER TABLE reports.report DROP CONSTRAINT ck_report_report_status;

-- statement-breakpoint

ALTER TABLE reports.report ADD CONSTRAINT ck_report_report_status
    CHECK (status IN ('RECEIVED', 'PROCESSING', 'READY_FOR_TRIAGE', 'LINKED', 'NEEDS_CLARIFICATION', 'REJECTED', 'WITHDRAWN', 'CLOSED'));

-- statement-breakpoint

ALTER TABLE reports.report_status_history DROP CONSTRAINT ck_report_status_history_report_previous_status;

-- statement-breakpoint

ALTER TABLE reports.report_status_history ADD CONSTRAINT ck_report_status_history_report_previous_status
    CHECK (from_status IN ('RECEIVED', 'PROCESSING', 'READY_FOR_TRIAGE', 'LINKED', 'NEEDS_CLARIFICATION', 'REJECTED', 'WITHDRAWN', 'CLOSED'));

-- statement-breakpoint

ALTER TABLE reports.report_status_history DROP CONSTRAINT ck_report_status_history_report_next_status;

-- statement-breakpoint

ALTER TABLE reports.report_status_history ADD CONSTRAINT ck_report_status_history_report_next_status
    CHECK (to_status IN ('RECEIVED', 'PROCESSING', 'READY_FOR_TRIAGE', 'LINKED', 'NEEDS_CLARIFICATION', 'REJECTED', 'WITHDRAWN', 'CLOSED'));
