export interface NewsPost {
  id: string;
  title: string;
  body: string;
  is_published: boolean;
  published_at: string | null;
  author_operator_id: string | null;
  /** Who published it - `null` for the platform admin's posts, which every resident gets. */
  organization_id: string | null;
}

export interface NewsPostCreatePayload {
  title: string;
  body: string;
  is_published?: boolean;
  published_at?: string | null;
}

export type NewsPostUpdatePayload = Partial<NewsPostCreatePayload>;
