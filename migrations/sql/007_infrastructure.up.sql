CREATE SCHEMA infrastructure;

-- statement-breakpoint

CREATE TABLE infrastructure.idempotency_record (
	id UUID NOT NULL, 
	scope VARCHAR(128) NOT NULL, 
	key VARCHAR(500) NOT NULL, 
	status VARCHAR(10) DEFAULT 'PROCESSING' NOT NULL, 
	result_entity_type VARCHAR(128), 
	result_entity_id UUID, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_idempotency_record PRIMARY KEY (id), 
	CONSTRAINT uq_idempotency_record_scope UNIQUE (scope, key), 
	CONSTRAINT ck_idempotency_record_idempotency_status CHECK (status IN ('PROCESSING', 'COMPLETED', 'FAILED'))
);

-- statement-breakpoint

CREATE TABLE infrastructure.inbound_webhook_event (
	id UUID NOT NULL, 
	provider VARCHAR(3) NOT NULL, 
	external_event_id VARCHAR(255), 
	idempotency_key VARCHAR(500) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(9) DEFAULT 'RECEIVED' NOT NULL, 
	received_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	processed_at TIMESTAMP WITH TIME ZONE, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_inbound_webhook_event PRIMARY KEY (id), 
	CONSTRAINT uq_inbound_webhook_event_provider UNIQUE (provider, idempotency_key), 
	CONSTRAINT ck_inbound_webhook_event_webhook_provider CHECK (provider IN ('MAX')), 
	CONSTRAINT ck_inbound_webhook_event_webhook_status CHECK (status IN ('RECEIVED', 'QUEUED', 'PROCESSED', 'FAILED'))
);

-- statement-breakpoint

CREATE TABLE infrastructure.outbox_event (
	id UUID NOT NULL, 
	aggregate_type VARCHAR(128) NOT NULL, 
	aggregate_id UUID NOT NULL, 
	event_type VARCHAR(255) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(9) DEFAULT 'PENDING' NOT NULL, 
	attempts INTEGER DEFAULT '0' NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	next_retry_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_outbox_event PRIMARY KEY (id), 
	CONSTRAINT ck_outbox_event_outbox_attempts_nonnegative CHECK (attempts >= 0), 
	CONSTRAINT ck_outbox_event_outbox_status CHECK (status IN ('PENDING', 'PUBLISHED', 'FAILED'))
);

-- statement-breakpoint

CREATE INDEX ix_infrastructure_outbox_event_aggregate_id ON infrastructure.outbox_event (aggregate_id);

-- statement-breakpoint

CREATE INDEX ix_infrastructure_outbox_event_next_retry_at ON infrastructure.outbox_event (next_retry_at);

-- statement-breakpoint

CREATE INDEX ix_infrastructure_outbox_event_status ON infrastructure.outbox_event (status);
