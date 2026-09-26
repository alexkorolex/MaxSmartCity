DROP INDEX news.ix_news_news_post_organization_id;

-- statement-breakpoint

ALTER TABLE news.news_post DROP COLUMN organization_id;
