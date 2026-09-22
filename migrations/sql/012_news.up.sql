CREATE SCHEMA news;

-- statement-breakpoint

CREATE TABLE news.news_post (
	id UUID NOT NULL,
	title VARCHAR(500) NOT NULL,
	body TEXT NOT NULL,
	is_published BOOLEAN DEFAULT false NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE,
	author_operator_id UUID,
	sa_orm_sentinel INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_news_post PRIMARY KEY (id),
	CONSTRAINT fk_news_post_author_operator_id_operator_user FOREIGN KEY(author_operator_id) REFERENCES identity.operator_user (id)
);

-- statement-breakpoint

CREATE INDEX ix_news_news_post_is_published ON news.news_post (is_published);

-- statement-breakpoint

CREATE INDEX ix_news_news_post_published_at ON news.news_post (published_at);
