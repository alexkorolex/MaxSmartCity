export interface NewsPost {
  id: string;
  title: string;
  body: string;
  is_published: boolean;
  published_at: string | null;
  author_operator_id: string | null;
}

export interface NewsPostCreatePayload {
  title: string;
  body: string;
  is_published?: boolean;
  published_at?: string | null;
}

export type NewsPostUpdatePayload = Partial<NewsPostCreatePayload>;
