ALTER TABLE geo.administrative_area ALTER COLUMN geometry DROP NOT NULL;

-- statement-breakpoint

ALTER TABLE geo.administrative_area ALTER COLUMN type TYPE VARCHAR(20);

-- statement-breakpoint

ALTER TABLE geo.administrative_area DROP CONSTRAINT ck_administrative_area_administrative_area_type;

-- statement-breakpoint

ALTER TABLE geo.administrative_area ADD CONSTRAINT ck_administrative_area_administrative_area_type CHECK (type IN ('CITY', 'ADMINISTRATIVE_OKRUG', 'DISTRICT', 'MUNICIPALITY', 'SETTLEMENT', 'OTHER'));

-- statement-breakpoint

ALTER TABLE geo.administrative_area ADD CONSTRAINT ck_administrative_area_root_is_city CHECK (parent_id IS NOT NULL OR type = 'CITY');

-- statement-breakpoint

CREATE UNIQUE INDEX uq_administrative_area_parent_name ON geo.administrative_area (COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid), lower(trim(name)));

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN authority_kind VARCHAR(23);

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN territory_id UUID;

-- statement-breakpoint

ALTER TABLE identity.organization ADD CONSTRAINT ck_organization_organization_authority_kind CHECK (authority_kind IN ('CITY_ADMINISTRATION', 'PREFECTURE', 'DISTRICT_ADMINISTRATION', 'DISTRICT_UPRAVA', 'INTRACITY_MUNICIPALITY', 'LOCAL_ADMINISTRATION'));

-- statement-breakpoint

ALTER TABLE identity.organization ADD CONSTRAINT fk_organization_territory_id_administrative_area FOREIGN KEY(territory_id) REFERENCES geo.administrative_area (id);

-- statement-breakpoint

CREATE INDEX ix_identity_organization_territory_id ON identity.organization (territory_id);

-- statement-breakpoint

ALTER TABLE identity.organization ADD CONSTRAINT ck_organization_authority_has_territory CHECK ((type = 'ADMINISTRATION') = (authority_kind IS NOT NULL AND territory_id IS NOT NULL)) NOT VALID;

-- statement-breakpoint

CREATE SCHEMA correspondence;

-- statement-breakpoint

CREATE TABLE correspondence.conversation (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	counterpart_organization_id UUID,
	subject VARCHAR(255) NOT NULL,
	created_by UUID NOT NULL,
	last_message_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	organization_read_at TIMESTAMP WITH TIME ZONE,
	counterpart_read_at TIMESTAMP WITH TIME ZONE,
	sa_orm_sentinel INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_conversation PRIMARY KEY (id),
	CONSTRAINT ck_conversation_distinct_sides CHECK (counterpart_organization_id IS NULL OR counterpart_organization_id <> organization_id),
	CONSTRAINT fk_conversation_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id),
	CONSTRAINT fk_conversation_counterpart_organization_id_organization FOREIGN KEY(counterpart_organization_id) REFERENCES identity.organization (id),
	CONSTRAINT fk_conversation_created_by_operator_user FOREIGN KEY(created_by) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_conversation_organization_last_message ON correspondence.conversation (organization_id, last_message_at);

-- statement-breakpoint

CREATE INDEX ix_conversation_counterpart_last_message ON correspondence.conversation (counterpart_organization_id, last_message_at);

-- statement-breakpoint

CREATE TABLE correspondence.message (
	id UUID NOT NULL,
	conversation_id UUID NOT NULL,
	author_operator_id UUID NOT NULL,
	author_organization_id UUID,
	text TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	sa_orm_sentinel INTEGER,
	CONSTRAINT pk_message PRIMARY KEY (id),
	CONSTRAINT fk_message_conversation_id_conversation FOREIGN KEY(conversation_id) REFERENCES correspondence.conversation (id),
	CONSTRAINT fk_message_author_operator_id_operator_user FOREIGN KEY(author_operator_id) REFERENCES identity.operator_user (id),
	CONSTRAINT fk_message_author_organization_id_organization FOREIGN KEY(author_organization_id) REFERENCES identity.organization (id)
);

-- statement-breakpoint

CREATE INDEX ix_message_conversation_created ON correspondence.message (conversation_id, created_at);
