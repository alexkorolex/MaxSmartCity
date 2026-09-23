import { useState, type FormEvent } from 'react';

import {
  useCreateNews,
  useDeleteNews,
  useNewsList,
  useUpdateNews,
  type NewsPost,
} from '@/entities/news';
import { isAdmin, useMe } from '@/entities/session';
import { formatDateTime } from '@/shared/lib';
import { AsyncState, EmptyState, NewsIcon, Pill } from '@/shared/ui';

function NewsRowActions({ post, canManage }: { post: NewsPost; canManage: boolean }) {
  const updateNews = useUpdateNews(post.id);
  const deleteNews = useDeleteNews();

  if (!canManage) return null;

  function togglePublish() {
    updateNews.mutate({
      is_published: !post.is_published,
      published_at: !post.is_published ? new Date().toISOString() : null,
    });
  }

  return (
    <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
      <button type="button" className="btn btn--ghost btn--small" onClick={togglePublish} disabled={updateNews.isPending}>
        {post.is_published ? 'Снять с публикации' : 'Опубликовать'}
      </button>
      <button
        type="button"
        className="btn btn--danger btn--small"
        onClick={() => {
          if (window.confirm('Удалить публикацию?')) deleteNews.mutate(post.id);
        }}
        disabled={deleteNews.isPending}
      >
        Удалить
      </button>
    </div>
  );
}

export function NewsPage() {
  const { data, isLoading, error, refetch } = useNewsList();
  const { data: principal } = useMe();
  const createNews = useCreateNews();

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [publishNow, setPublishNow] = useState(false);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || !body.trim()) return;
    createNews.mutate(
      {
        title: title.trim(),
        body: body.trim(),
        is_published: publishNow,
        published_at: publishNow ? new Date().toISOString() : null,
      },
      {
        onSuccess: () => {
          setTitle('');
          setBody('');
          setPublishNow(false);
        },
      },
    );
  }

  return (
    <>
      <div className="card">
        <div className="card__header">
          <div className="card__title">Новая публикация</div>
        </div>
        <div className="card__body">
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <div>
              <label className="field-label" htmlFor="news-title">
                Заголовок
              </label>
              <input
                id="news-title"
                className="field"
                style={{ width: '100%' }}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="news-body">
                Текст
              </label>
              <textarea
                id="news-body"
                className="field"
                style={{ width: '100%' }}
                value={body}
                onChange={(event) => setBody(event.target.value)}
              />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 13 }}>
              <input
                type="checkbox"
                checked={publishNow}
                onChange={(event) => setPublishNow(event.target.checked)}
              />
              Опубликовать сразу
            </label>
            <div>
              <button type="submit" className="btn" disabled={createNews.isPending || !title.trim() || !body.trim()}>
                {createNews.isPending ? 'Публикуем…' : 'Сохранить'}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <div className="card__title">Публикации</div>
        </div>
        <div className="card__body" style={{ padding: 0 }}>
          <AsyncState isLoading={isLoading} error={error} onRetry={() => void refetch()}>
            {!data || data.length === 0 ? (
              <EmptyState icon={<NewsIcon />} title="Публикаций пока нет" />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Заголовок</th>
                      <th>Статус</th>
                      <th>Опубликовано</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((post) => {
                      const canManage =
                        Boolean(principal) &&
                        (isAdmin(principal) || post.author_operator_id === principal?.actor_id);
                      return (
                        <tr key={post.id}>
                          <td>
                            <div className="cell-primary">{post.title}</div>
                            <div className="cell-muted">{post.body.slice(0, 120)}</div>
                          </td>
                          <td>
                            <Pill
                              tone={post.is_published ? 'success' : 'neutral'}
                              label={post.is_published ? 'Опубликовано' : 'Черновик'}
                            />
                          </td>
                          <td className="cell-muted">
                            {post.published_at ? formatDateTime(post.published_at) : '—'}
                          </td>
                          <td>
                            <NewsRowActions post={post} canManage={canManage} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </AsyncState>
        </div>
      </div>
    </>
  );
}
