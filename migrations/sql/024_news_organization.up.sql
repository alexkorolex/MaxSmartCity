ALTER TABLE news.news_post ADD COLUMN organization_id UUID;

-- statement-breakpoint

ALTER TABLE news.news_post ADD CONSTRAINT fk_news_post_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id);

-- statement-breakpoint

CREATE INDEX ix_news_news_post_organization_id ON news.news_post (organization_id);

-- statement-breakpoint

-- Existing posts belong to their author's organization; the platform admin's stay platform-wide.
UPDATE news.news_post AS post
SET organization_id = member.organization_id
FROM identity.organization_member AS member
WHERE member.user_id = post.author_operator_id AND member.is_active;
