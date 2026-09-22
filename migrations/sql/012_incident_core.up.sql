-- Incident Core follows the GIS ЖКХ pilot migration.
CREATE UNIQUE INDEX uq_report_source_external_id
ON reports.report (source_type, source_external_id)
WHERE source_external_id IS NOT NULL;

-- statement-breakpoint

CREATE INDEX ix_report_grouping_candidates
ON reports.report (house_id, category_id, status, received_at);

-- statement-breakpoint

CREATE INDEX ix_incident_grouping_candidates
ON incidents.incident (category_id, status, last_report_at);

-- statement-breakpoint

CREATE INDEX ix_incident_affected_house_house
ON incidents.incident_affected_house (house_id, incident_id);

-- statement-breakpoint

CREATE TABLE incidents.incident_grouping_decision (
	id UUID NOT NULL,
	report_id UUID NOT NULL,
	outcome VARCHAR(19) NOT NULL,
	selected_incident_id UUID,
	score NUMERIC(7, 6),
	runner_up_score NUMERIC(7, 6),
	candidate_incident_ids JSONB DEFAULT '[]' NOT NULL,
	reason_codes JSONB DEFAULT '[]' NOT NULL,
	policy_version VARCHAR(64) NOT NULL,
	scorer_version VARCHAR(64) NOT NULL,
	request_id UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	sa_orm_sentinel INTEGER,
	CONSTRAINT pk_incident_grouping_decision PRIMARY KEY (id),
	CONSTRAINT fk_grouping_decision_report FOREIGN KEY(report_id) REFERENCES reports.report (id),
	CONSTRAINT fk_grouping_decision_incident FOREIGN KEY(selected_incident_id) REFERENCES incidents.incident (id),
	CONSTRAINT ck_incident_grouping_decision_grouping_outcome CHECK (outcome IN ('ATTACHED', 'CREATED', 'NEEDS_CLARIFICATION'))
);

-- statement-breakpoint

CREATE INDEX ix_incidents_incident_grouping_decision_report_id
ON incidents.incident_grouping_decision (report_id);

-- statement-breakpoint

CREATE INDEX ix_incidents_incident_grouping_decision_selected_incident_id
ON incidents.incident_grouping_decision (selected_incident_id);
