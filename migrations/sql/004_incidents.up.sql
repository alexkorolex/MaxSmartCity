CREATE SCHEMA incidents;

-- statement-breakpoint

CREATE TABLE incidents.incident (
	id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	category_id UUID NOT NULL, 
	status VARCHAR(21) DEFAULT 'NEW' NOT NULL, 
	priority VARCHAR(8) DEFAULT 'NORMAL' NOT NULL, 
	affected_area geometry(MULTIPOLYGON,4326), 
	first_report_at TIMESTAMP WITH TIME ZONE, 
	last_report_at TIMESTAMP WITH TIME ZONE, 
	expected_resolution_at TIMESTAMP WITH TIME ZONE, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER DEFAULT '1' NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_incident PRIMARY KEY (id), 
	CONSTRAINT fk_incident_category_id_problem_category FOREIGN KEY(category_id) REFERENCES reports.problem_category (id), 
	CONSTRAINT ck_incident_incident_status CHECK (status IN ('NEW', 'TRIAGE', 'CONFIRMED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'AWAITING_CONFIRMATION', 'CLOSED', 'REJECTED', 'CANCELLED', 'MERGED', 'RESOLUTION_DISPUTED', 'REOPENED')), 
	CONSTRAINT ck_incident_incident_priority CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL'))
);

-- statement-breakpoint

CREATE INDEX idx_incident_affected_area ON incidents.incident USING gist (affected_area);

-- statement-breakpoint

CREATE TABLE incidents.incident_affected_house (
	incident_id UUID NOT NULL, 
	house_id UUID NOT NULL, 
	source VARCHAR(9) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_incident_affected_house PRIMARY KEY (incident_id, house_id), 
	CONSTRAINT fk_incident_affected_house_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_incident_affected_house_house_id_house FOREIGN KEY(house_id) REFERENCES geo.house (id), 
	CONSTRAINT ck_incident_affected_house_incident_affected_house_source CHECK (source IN ('MANUAL', 'REPORT', 'INGESTION', 'GEO'))
);

-- statement-breakpoint

CREATE TABLE incidents.incident_relation (
	id UUID NOT NULL, 
	source_incident_id UUID NOT NULL, 
	target_incident_id UUID NOT NULL, 
	type VARCHAR(11) NOT NULL, 
	created_by UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_incident_relation PRIMARY KEY (id), 
	CONSTRAINT ck_incident_relation_incident_relation_distinct_incidents CHECK (source_incident_id <> target_incident_id), 
	CONSTRAINT fk_incident_relation_source_incident_id_incident FOREIGN KEY(source_incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_incident_relation_target_incident_id_incident FOREIGN KEY(target_incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT ck_incident_relation_incident_relation_type CHECK (type IN ('MERGED_INTO', 'SPLIT_FROM')), 
	CONSTRAINT fk_incident_relation_created_by_operator_user FOREIGN KEY(created_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_incidents_incident_relation_source_incident_id ON incidents.incident_relation (source_incident_id);

-- statement-breakpoint

CREATE INDEX ix_incidents_incident_relation_target_incident_id ON incidents.incident_relation (target_incident_id);

-- statement-breakpoint

CREATE TABLE incidents.incident_status_history (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	from_status VARCHAR(21), 
	to_status VARCHAR(21) NOT NULL, 
	changed_by_type VARCHAR(8) NOT NULL, 
	changed_by_id UUID, 
	reason TEXT, 
	request_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_incident_status_history PRIMARY KEY (id), 
	CONSTRAINT fk_incident_status_history_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT ck_incident_status_history_incident_previous_status CHECK (from_status IN ('NEW', 'TRIAGE', 'CONFIRMED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'AWAITING_CONFIRMATION', 'CLOSED', 'REJECTED', 'CANCELLED', 'MERGED', 'RESOLUTION_DISPUTED', 'REOPENED')), 
	CONSTRAINT ck_incident_status_history_incident_next_status CHECK (to_status IN ('NEW', 'TRIAGE', 'CONFIRMED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'AWAITING_CONFIRMATION', 'CLOSED', 'REJECTED', 'CANCELLED', 'MERGED', 'RESOLUTION_DISPUTED', 'REOPENED')), 
	CONSTRAINT ck_incident_status_history_incident_changed_by_type CHECK (changed_by_type IN ('RESIDENT', 'OPERATOR', 'SERVICE', 'SYSTEM'))
);

-- statement-breakpoint

CREATE INDEX ix_incidents_incident_status_history_incident_id ON incidents.incident_status_history (incident_id);

-- statement-breakpoint

CREATE TABLE incidents.incident_report_link (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	report_id UUID NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	link_source VARCHAR(9) NOT NULL, 
	score NUMERIC, 
	reason_codes JSONB, 
	linked_by_user_id UUID, 
	linked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	unlinked_at TIMESTAMP WITH TIME ZONE, 
	unlink_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_incident_report_link PRIMARY KEY (id), 
	CONSTRAINT fk_incident_report_link_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_incident_report_link_report_id_report FOREIGN KEY(report_id) REFERENCES reports.report (id), 
	CONSTRAINT ck_incident_report_link_incident_link_source CHECK (link_source IN ('MANUAL', 'ML', 'RULE', 'INGESTION')), 
	CONSTRAINT fk_incident_report_link_linked_by_user_id_operator_user FOREIGN KEY(linked_by_user_id) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_incidents_incident_report_link_incident_id ON incidents.incident_report_link (incident_id);

-- statement-breakpoint

CREATE UNIQUE INDEX uq_incident_report_active ON incidents.incident_report_link (report_id) WHERE is_active = true;

-- statement-breakpoint

CREATE TABLE incidents.resolution_dispute (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	resident_id UUID NOT NULL, 
	report_id UUID, 
	status VARCHAR(8) DEFAULT 'OPEN' NOT NULL, 
	comment TEXT, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	resolved_by UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_resolution_dispute PRIMARY KEY (id), 
	CONSTRAINT fk_resolution_dispute_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_resolution_dispute_resident_id_resident FOREIGN KEY(resident_id) REFERENCES identity.resident (id), 
	CONSTRAINT fk_resolution_dispute_report_id_report FOREIGN KEY(report_id) REFERENCES reports.report (id), 
	CONSTRAINT ck_resolution_dispute_resolution_dispute_status CHECK (status IN ('OPEN', 'ACCEPTED', 'REJECTED', 'RESOLVED')), 
	CONSTRAINT fk_resolution_dispute_resolved_by_operator_user FOREIGN KEY(resolved_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_incidents_resolution_dispute_incident_id ON incidents.resolution_dispute (incident_id);
