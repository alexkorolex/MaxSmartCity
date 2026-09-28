import { useState, type FormEvent } from 'react';

import {
  CHANNEL_META,
  CHANNEL_TYPES,
  channelTargetError,
  useCreateOrganizationChannel,
  useDeleteOrganizationChannel,
  useOrganizationChannels,
  useSetOrganizationChannelActive,
  useTestOrganizationChannel,
  type ChannelTestResult,
  type ChannelType,
} from '@/entities/notification-channel';
import type { OrganizationMember } from '@/entities/organization';
import { useLinkMaxAccount } from '@/entities/session';
import { apiErrorMessage } from '@/shared/lib';
import { AsyncState, Pill } from '@/shared/ui';

import './OrganizationChannelsCard.css';

interface OrganizationChannelsCardProps {
  organizationId: string;
  isAdmin: boolean;
  ownMember: OrganizationMember | undefined;
}

function LinkMaxAccount({ member }: { member: OrganizationMember }) {
  const [maxId, setMaxId] = useState('');
  const link = useLinkMaxAccount();

  if (member.has_max_account && !link.isSuccess) {
    return <div className="form-success">Ваш MAX привязан — личные уведомления о заявках будут приходить туда.</div>;
  }
  if (link.isSuccess) {
    return <div className="form-success">MAX привязан. Теперь уведомления о заявках будут приходить вам лично.</div>;
  }
  return (
    <form
      className="channels__link-max"
      onSubmit={(event: FormEvent) => {
        event.preventDefault();
        if (/^\d+$/.test(maxId.trim())) link.mutate(Number(maxId.trim()));
      }}
    >
      <div>
        <label className="field-label" htmlFor="own-max-id">
          Мой MAX ID
        </label>
        <input
          id="own-max-id"
          className="field"
          inputMode="numeric"
          placeholder="Напишите боту Smart City /id — он пришлёт номер"
          value={maxId}
          onChange={(event) => setMaxId(event.target.value.replace(/\D/g, ''))}
        />
      </div>
      <button type="submit" className="btn btn--ghost" disabled={!maxId || link.isPending}>
        Привязать
      </button>
      {link.isError && <div className="form-error">{apiErrorMessage(link.error)}</div>}
    </form>
  );
}

export function OrganizationChannelsCard({ organizationId, isAdmin, ownMember }: OrganizationChannelsCardProps) {
  const channels = useOrganizationChannels(organizationId);
  const create = useCreateOrganizationChannel(organizationId);
  const setActive = useSetOrganizationChannelActive(organizationId);
  const remove = useDeleteOrganizationChannel(organizationId);
  const testChannel = useTestOrganizationChannel();
  const [testResults, setTestResults] = useState<Record<string, ChannelTestResult>>({});

  const availableTypes = CHANNEL_TYPES.filter((type) => isAdmin || !CHANNEL_META[type].adminOnly);
  const [type, setType] = useState<ChannelType>(availableTypes[0] ?? 'MAX_CHAT');
  const [target, setTarget] = useState('');
  const [secret, setSecret] = useState('');
  const meta = CHANNEL_META[type];
  const targetError = meta.targetLabel && target ? channelTargetError(type, target) : null;
  const canAdd = !meta.targetLabel || (Boolean(target.trim()) && !channelTargetError(type, target));

  function handleAdd(event: FormEvent) {
    event.preventDefault();
    if (!canAdd) return;
    create.mutate(
      {
        organization_id: organizationId,
        type,
        target: meta.targetLabel ? target.trim() : null,
        secret: type === 'WEBHOOK' && secret.trim() ? secret.trim() : null,
      },
      {
        onSuccess: () => {
          setTarget('');
          setSecret('');
        },
      },
    );
  }

  function runTest(channelId: string) {
    testChannel.mutate(channelId, {
      onSuccess: (result) => setTestResults((current) => ({ ...current, [channelId]: result })),
    });
  }

  const activeCount = channels.data?.filter((channel) => channel.is_active).length ?? 0;

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Уведомления о заявках</div>
          <div className="card__meta">
            Куда организация получает новые заявки жителей по своим домам, назначения, оспаривания и закрытия.
            {activeCount === 0 && ' Пока каналов нет — уведомления идут лично сотрудникам, привязавшим MAX.'}
          </div>
        </div>
      </div>
      <div className="card__body channels">
        <AsyncState isLoading={channels.isLoading} error={channels.error} onRetry={() => void channels.refetch()}>
          {(channels.data?.length ?? 0) > 0 && (
            <div className="channels__list">
              {channels.data?.map((channel) => {
                const result = testResults[channel.id];
                return (
                  <div key={channel.id} className="channels__item">
                    <div className="channels__item-head">
                      <div>
                        <div className="cell-primary">{CHANNEL_META[channel.type].label}</div>
                        {channel.target && <div className="cell-muted">{channel.target}</div>}
                      </div>
                      <Pill
                        tone={channel.is_active ? 'success' : 'neutral'}
                        label={channel.is_active ? 'Включён' : 'Отключён'}
                      />
                    </div>
                    <div className="channels__actions">
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        disabled={testChannel.isPending}
                        onClick={() => runTest(channel.id)}
                      >
                        Проверить
                      </button>
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        disabled={setActive.isPending}
                        onClick={() => setActive.mutate({ channelId: channel.id, active: !channel.is_active })}
                      >
                        {channel.is_active ? 'Отключить' : 'Включить'}
                      </button>
                      <button
                        type="button"
                        className="btn btn--danger-ghost btn--small"
                        disabled={remove.isPending}
                        onClick={() => {
                          if (window.confirm('Удалить канал уведомлений?')) remove.mutate(channel.id);
                        }}
                      >
                        Удалить
                      </button>
                    </div>
                    {result && (
                      <div className={result.delivered ? 'form-success' : 'form-error'}>
                        {result.delivered
                          ? 'Тестовое сообщение отправлено — проверьте, что оно пришло.'
                          : `Не удалось отправить: ${result.error}`}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </AsyncState>

        <form className="channels__form" onSubmit={handleAdd}>
          <div className="form-section-title">Добавить канал</div>
          <div className="form-grid">
            <div>
              <label className="field-label" htmlFor="channel-type">
                Куда отправлять
              </label>
              <select
                id="channel-type"
                className="field"
                value={type}
                onChange={(event) => {
                  setType(event.target.value as ChannelType);
                  setTarget('');
                }}
              >
                {availableTypes.map((option) => (
                  <option key={option} value={option}>
                    {CHANNEL_META[option].label}
                  </option>
                ))}
              </select>
            </div>
            {meta.targetLabel && (
              <div>
                <label className="field-label" htmlFor="channel-target">
                  {meta.targetLabel}
                </label>
                <input
                  id="channel-target"
                  className="field"
                  placeholder={meta.placeholder}
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                />
                {targetError && <div className="form-hint form-hint--error">{targetError}</div>}
              </div>
            )}
            {type === 'WEBHOOK' && (
              <div>
                <label className="field-label" htmlFor="channel-secret">
                  Секрет для подписи
                </label>
                <input
                  id="channel-secret"
                  className="field"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Необязательно"
                  value={secret}
                  onChange={(event) => setSecret(event.target.value)}
                />
              </div>
            )}
            <div className="form-hint form-grid__wide">{meta.description}</div>
          </div>
          {create.isError && <div className="form-error">{apiErrorMessage(create.error)}</div>}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={!canAdd || create.isPending}>
              {create.isPending ? 'Добавляем…' : 'Добавить канал'}
            </button>
          </div>
        </form>

        {ownMember && (
          <div className="channels__own">
            <div className="form-section-title">Личные уведомления в MAX</div>
            <LinkMaxAccount member={ownMember} />
          </div>
        )}
      </div>
    </div>
  );
}
