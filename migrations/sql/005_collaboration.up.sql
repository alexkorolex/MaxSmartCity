CREATE SCHEMA collaboration;

-- statement-breakpoint

CREATE TABLE collaboration.assignment (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	role VARCHAR(17) NOT NULL, 
	status VARCHAR(11) DEFAULT 'PROPOSED' NOT NULL, 
	required BOOLEAN DEFAULT true NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE, 
	accepted_at TIMESTAMP WITH TIME ZONE, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER DEFAULT '1' NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_assignment PRIMARY KEY (id), 
	CONSTRAINT uq_assignment_context UNIQUE (id, incident_id, organization_id), 
	CONSTRAINT fk_assignment_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_assignment_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id), 
	CONSTRAINT ck_assignment_assignment_role CHECK (role IN ('OWNER', 'EXECUTOR', 'CO_EXECUTOR', 'OBSERVER', 'ESCALATION_TARGET')), 
	CONSTRAINT ck_assignment_assignment_status CHECK (status IN ('PROPOSED', 'ACCEPTED', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'MONITORING'))
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_assignment_incident_id ON collaboration.assignment (incident_id);

-- statement-breakpoint

CREATE INDEX ix_collaboration_assignment_organization_id ON collaboration.assignment (organization_id);

-- statement-breakpoint

CREATE TABLE collaboration.collaboration_link (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	type VARCHAR(8) NOT NULL, 
	title VARCHAR(255), 
	url TEXT NOT NULL, 
	created_by UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_collaboration_link PRIMARY KEY (id), 
	CONSTRAINT fk_collaboration_link_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT ck_collaboration_link_collaboration_link_type CHECK (type IN ('MAX', 'VIDEO', 'INTERNAL', 'OTHER')), 
	CONSTRAINT fk_collaboration_link_created_by_operator_user FOREIGN KEY(created_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_collaboration_link_incident_id ON collaboration.collaboration_link (incident_id);

-- statement-breakpoint

CREATE TABLE collaboration.assignment_status_history (
	id UUID NOT NULL, 
	assignment_id UUID NOT NULL, 
	from_status VARCHAR(11), 
	to_status VARCHAR(11) NOT NULL, 
	changed_by UUID NOT NULL, 
	reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_assignment_status_history PRIMARY KEY (id), 
	CONSTRAINT fk_assignment_status_history_assignment_id_assignment FOREIGN KEY(assignment_id) REFERENCES collaboration.assignment (id), 
	CONSTRAINT ck_assignment_status_history_assignment_from_status CHECK (from_status IN ('PROPOSED', 'ACCEPTED', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'MONITORING')), 
	CONSTRAINT ck_assignment_status_history_assignment_to_status CHECK (to_status IN ('PROPOSED', 'ACCEPTED', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'MONITORING')), 
	CONSTRAINT fk_assignment_status_history_changed_by_operator_user FOREIGN KEY(changed_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_assignment_status_history_assignment_id ON collaboration.assignment_status_history (assignment_id);

-- statement-breakpoint

CREATE TABLE collaboration.transfer_request (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	assignment_id UUID NOT NULL, 
	from_organization_id UUID NOT NULL, 
	to_organization_id UUID NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(22) DEFAULT 'PENDING' NOT NULL, 
	created_by UUID NOT NULL, 
	responded_by UUID, 
	response_reason TEXT, 
	responded_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_transfer_request PRIMARY KEY (id), 
	CONSTRAINT ck_transfer_request_transfer_organizations_differ CHECK (from_organization_id <> to_organization_id), 
	CONSTRAINT fk_transfer_assignment_context FOREIGN KEY(assignment_id, incident_id, from_organization_id) REFERENCES collaboration.assignment (id, incident_id, organization_id), 
	CONSTRAINT fk_transfer_request_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_transfer_request_from_organization_id_organization FOREIGN KEY(from_organization_id) REFERENCES identity.organization (id), 
	CONSTRAINT fk_transfer_request_to_organization_id_organization FOREIGN KEY(to_organization_id) REFERENCES identity.organization (id), 
	CONSTRAINT ck_transfer_request_transfer_status CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'CLARIFICATION_REQUIRED', 'CANCELLED')), 
	CONSTRAINT fk_transfer_request_created_by_operator_user FOREIGN KEY(created_by) REFERENCES identity.operator_user (id), 
	CONSTRAINT fk_transfer_request_responded_by_operator_user FOREIGN KEY(responded_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_transfer_request_assignment_id ON collaboration.transfer_request (assignment_id);

-- statement-breakpoint

CREATE INDEX ix_collaboration_transfer_request_incident_id ON collaboration.transfer_request (incident_id);

-- statement-breakpoint

CREATE TABLE collaboration.work_item (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	assignment_id UUID, 
	organization_id UUID NOT NULL, 
	assignee_member_id UUID, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	status VARCHAR(11) DEFAULT 'TODO' NOT NULL, 
	priority VARCHAR(8) DEFAULT 'NORMAL' NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	version INTEGER DEFAULT '1' NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_work_item PRIMARY KEY (id), 
	CONSTRAINT fk_work_item_assignment_context FOREIGN KEY(assignment_id, incident_id, organization_id) REFERENCES collaboration.assignment (id, incident_id, organization_id), 
	CONSTRAINT fk_work_item_assignee_organization FOREIGN KEY(assignee_member_id, organization_id) REFERENCES identity.organization_member (id, organization_id), 
	CONSTRAINT fk_work_item_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_work_item_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id), 
	CONSTRAINT ck_work_item_work_item_status CHECK (status IN ('TODO', 'IN_PROGRESS', 'BLOCKED', 'COMPLETED', 'CANCELLED')), 
	CONSTRAINT ck_work_item_work_item_priority CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')), 
	CONSTRAINT fk_work_item_created_by_operator_user FOREIGN KEY(created_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_work_item_assignee_member_id ON collaboration.work_item (assignee_member_id);

-- statement-breakpoint

CREATE INDEX ix_collaboration_work_item_assignment_id ON collaboration.work_item (assignment_id);

-- statement-breakpoint

CREATE INDEX ix_collaboration_work_item_incident_id ON collaboration.work_item (incident_id);

-- statement-breakpoint

CREATE INDEX ix_collaboration_work_item_organization_id ON collaboration.work_item (organization_id);

-- statement-breakpoint

CREATE TABLE collaboration.incident_comment (
	id UUID NOT NULL, 
	incident_id UUID NOT NULL, 
	assignment_id UUID, 
	work_item_id UUID, 
	author_user_id UUID NOT NULL, 
	visibility VARCHAR(8) DEFAULT 'INTERNAL' NOT NULL, 
	text TEXT NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_incident_comment PRIMARY KEY (id), 
	CONSTRAINT fk_incident_comment_incident_id_incident FOREIGN KEY(incident_id) REFERENCES incidents.incident (id), 
	CONSTRAINT fk_incident_comment_assignment_id_assignment FOREIGN KEY(assignment_id) REFERENCES collaboration.assignment (id), 
	CONSTRAINT fk_incident_comment_work_item_id_work_item FOREIGN KEY(work_item_id) REFERENCES collaboration.work_item (id), 
	CONSTRAINT fk_incident_comment_author_user_id_operator_user FOREIGN KEY(author_user_id) REFERENCES identity.operator_user (id), 
	CONSTRAINT ck_incident_comment_comment_visibility CHECK (visibility IN ('INTERNAL', 'PUBLIC'))
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_incident_comment_incident_id ON collaboration.incident_comment (incident_id);

-- statement-breakpoint

CREATE TABLE collaboration.work_item_attachment (
	id UUID NOT NULL, 
	work_item_id UUID NOT NULL, 
	storage_key TEXT NOT NULL, 
	filename TEXT NOT NULL, 
	mime_type VARCHAR(255) NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	checksum VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_work_item_attachment PRIMARY KEY (id), 
	CONSTRAINT ck_work_item_attachment_work_item_attachment_size_nonnegative CHECK (size_bytes >= 0), 
	CONSTRAINT fk_work_item_attachment_work_item_id_work_item FOREIGN KEY(work_item_id) REFERENCES collaboration.work_item (id)
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_work_item_attachment_work_item_id ON collaboration.work_item_attachment (work_item_id);

-- statement-breakpoint

CREATE TABLE collaboration.work_item_blocker (
	id UUID NOT NULL, 
	work_item_id UUID NOT NULL, 
	reason TEXT NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	created_by UUID NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_work_item_blocker PRIMARY KEY (id), 
	CONSTRAINT fk_work_item_blocker_work_item_id_work_item FOREIGN KEY(work_item_id) REFERENCES collaboration.work_item (id), 
	CONSTRAINT fk_work_item_blocker_created_by_operator_user FOREIGN KEY(created_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_collaboration_work_item_blocker_work_item_id ON collaboration.work_item_blocker (work_item_id);

-- statement-breakpoint

CREATE TABLE collaboration.comment_mention (
	comment_id UUID NOT NULL, 
	organization_member_id UUID NOT NULL, 
	CONSTRAINT pk_comment_mention PRIMARY KEY (comment_id, organization_member_id), 
	CONSTRAINT fk_comment_mention_comment_id_incident_comment FOREIGN KEY(comment_id) REFERENCES collaboration.incident_comment (id), 
	CONSTRAINT fk_comment_mention_organization_member_id_organization_member FOREIGN KEY(organization_member_id) REFERENCES identity.organization_member (id)
);
