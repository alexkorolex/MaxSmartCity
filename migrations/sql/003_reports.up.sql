CREATE SCHEMA reports;

-- statement-breakpoint

CREATE TABLE reports.problem_category (
	id UUID NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	is_critical BOOLEAN DEFAULT false NOT NULL, 
	enabled BOOLEAN DEFAULT true NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_problem_category PRIMARY KEY (id), 
	CONSTRAINT uq_problem_category_code UNIQUE (code)
);

-- statement-breakpoint

CREATE TABLE reports.report (
	id UUID NOT NULL, 
	resident_id UUID, 
	source_type VARCHAR(9) NOT NULL, 
	source_external_id VARCHAR(255), 
	text TEXT, 
	status VARCHAR(19) DEFAULT 'RECEIVED' NOT NULL, 
	category_id UUID, 
	urgency VARCHAR(8) DEFAULT 'NORMAL' NOT NULL, 
	location geography(POINT,4326), 
	address_id UUID, 
	house_id UUID, 
	affected_object_id UUID, 
	danger_flags JSONB DEFAULT '{}' NOT NULL, 
	extracted_features JSONB DEFAULT '{}' NOT NULL, 
	problem_continues BOOLEAN, 
	occurred_at TIMESTAMP WITH TIME ZONE, 
	received_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_report PRIMARY KEY (id), 
	CONSTRAINT fk_report_resident_id_resident FOREIGN KEY(resident_id) REFERENCES identity.resident (id), 
	CONSTRAINT ck_report_report_source_type CHECK (source_type IN ('MAX', 'INGESTION', 'OPERATOR', 'SYSTEM')), 
	CONSTRAINT ck_report_report_status CHECK (status IN ('RECEIVED', 'PROCESSING', 'READY_FOR_TRIAGE', 'LINKED', 'NEEDS_CLARIFICATION', 'REJECTED', 'WITHDRAWN')), 
	CONSTRAINT fk_report_category_id_problem_category FOREIGN KEY(category_id) REFERENCES reports.problem_category (id), 
	CONSTRAINT ck_report_report_urgency CHECK (urgency IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')), 
	CONSTRAINT fk_report_address_id_address FOREIGN KEY(address_id) REFERENCES geo.address (id), 
	CONSTRAINT fk_report_house_id_house FOREIGN KEY(house_id) REFERENCES geo.house (id), 
	CONSTRAINT fk_report_affected_object_id_affected_object FOREIGN KEY(affected_object_id) REFERENCES geo.affected_object (id)
);

-- statement-breakpoint

CREATE INDEX idx_report_location ON reports.report USING gist (location);

-- statement-breakpoint

CREATE TABLE reports.report_attachment (
	id UUID NOT NULL, 
	report_id UUID NOT NULL, 
	type VARCHAR(5) NOT NULL, 
	storage_key TEXT NOT NULL, 
	original_name TEXT, 
	mime_type VARCHAR(255) NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	checksum VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_report_attachment PRIMARY KEY (id), 
	CONSTRAINT ck_report_attachment_report_attachment_size_nonnegative CHECK (size_bytes >= 0), 
	CONSTRAINT fk_report_attachment_report_id_report FOREIGN KEY(report_id) REFERENCES reports.report (id), 
	CONSTRAINT ck_report_attachment_report_attachment_type CHECK (type IN ('IMAGE', 'FILE'))
);

-- statement-breakpoint

CREATE INDEX ix_reports_report_attachment_report_id ON reports.report_attachment (report_id);

-- statement-breakpoint

CREATE TABLE reports.report_status_history (
	id UUID NOT NULL, 
	report_id UUID NOT NULL, 
	from_status VARCHAR(19), 
	to_status VARCHAR(19) NOT NULL, 
	changed_by_type VARCHAR(8) NOT NULL, 
	changed_by_id UUID, 
	reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_report_status_history PRIMARY KEY (id), 
	CONSTRAINT fk_report_status_history_report_id_report FOREIGN KEY(report_id) REFERENCES reports.report (id), 
	CONSTRAINT ck_report_status_history_report_previous_status CHECK (from_status IN ('RECEIVED', 'PROCESSING', 'READY_FOR_TRIAGE', 'LINKED', 'NEEDS_CLARIFICATION', 'REJECTED', 'WITHDRAWN')), 
	CONSTRAINT ck_report_status_history_report_next_status CHECK (to_status IN ('RECEIVED', 'PROCESSING', 'READY_FOR_TRIAGE', 'LINKED', 'NEEDS_CLARIFICATION', 'REJECTED', 'WITHDRAWN')), 
	CONSTRAINT ck_report_status_history_report_changed_by_type CHECK (changed_by_type IN ('RESIDENT', 'OPERATOR', 'SERVICE', 'SYSTEM'))
);

-- statement-breakpoint

CREATE INDEX ix_reports_report_status_history_report_id ON reports.report_status_history (report_id);
