import { CellHeader, CellList, CellSimple, Flex, Typography } from '@maxhub/max-ui';

import { formatCalendarDate } from '@/shared/lib';
import { GlobeIcon, ListCard, MailIcon, PhoneIcon, StatusBadge } from '@/shared/ui';

import { formatPhone, websiteLabel } from '../lib/contacts';
import {
  managingOrganizationLabel,
  type HouseDataSource,
  type HouseInfo,
  type HouseManagingOrganization,
} from '../model/types';

import './HouseInfoCard.css';

function sourceLabel(source: HouseDataSource): string {
  const host = source.url ? websiteLabel(source.url) : source.code;
  return `${host} · ${formatCalendarDate(source.retrieved_at, { year: true })}`;
}

function Requisites({ inn, ogrn }: { inn: string | null; ogrn: string | null }) {
  const parts = [inn && `ИНН ${inn}`, ogrn && `ОГРН ${ogrn}`].filter(Boolean);
  if (parts.length === 0) return null;
  return (
    <Typography.Text variant="description" color="tertiary">
      {parts.join(' · ')}
    </Typography.Text>
  );
}

function ManagingOrganizationCard({
  organization,
  managementMethod,
}: {
  organization: HouseManagingOrganization;
  managementMethod: string | null;
}) {
  const isDemo = organization.sources.some((source) => source.data_kind === 'DEMO');
  const hasContacts = organization.phones.length > 0 || organization.email || organization.website;

  return (
    <>
      <Flex direction="column" gap="var(--space-2)" className="surface-card house-info__company">
        <Flex gap="var(--space-2)" wrap="wrap">
          <StatusBadge label={managingOrganizationLabel(organization, managementMethod)} tone="info" />
          {organization.is_platform_manager && <StatusBadge label="Принимает заявки в приложении" tone="success" />}
          {isDemo && <StatusBadge label="Демо-данные" tone="warning" />}
        </Flex>
        <Typography.Text variant="title" color="primary">
          {organization.name}
        </Typography.Text>
        <Requisites inn={organization.inn} ogrn={organization.ogrn} />
        {organization.period_from && (
          <Typography.Text variant="description" color="secondary">
            Управляет домом с {formatCalendarDate(organization.period_from, { year: true })}
          </Typography.Text>
        )}
      </Flex>

      <ListCard>
        <CellList mode="full-width" header={<CellHeader>Контакты</CellHeader>}>
          {organization.phones.map((phone) => (
            <CellSimple
              key={phone}
              asChild
              title={formatPhone(phone)}
              subtitle="Позвонить"
              subtitleMode="tertiary"
              before={<PhoneIcon width={20} height={20} />}
              separator
            >
              <a href={`tel:${phone}`} />
            </CellSimple>
          ))}
          {organization.email && (
            <CellSimple
              asChild
              title={organization.email}
              subtitle="Написать письмо"
              subtitleMode="tertiary"
              before={<MailIcon width={20} height={20} />}
              separator
            >
              <a href={`mailto:${organization.email}`} />
            </CellSimple>
          )}
          {organization.website && (
            <CellSimple
              asChild
              title={websiteLabel(organization.website)}
              subtitle="Сайт организации"
              subtitleMode="tertiary"
              before={<GlobeIcon width={20} height={20} />}
              showChevron
            >
              <a href={organization.website} target="_blank" rel="noopener noreferrer" />
            </CellSimple>
          )}
          {!hasContacts && (
            <CellSimple
              title="Контакты пока не опубликованы"
              subtitle="Мы покажем их, как только они появятся в открытых источниках"
              subtitleMode="tertiary"
            />
          )}
        </CellList>
      </ListCard>

      {organization.sources.length > 0 && (
        <Typography.Text variant="description" color="tertiary" className="house-info__source">
          По данным открытых источников:{' '}
          {organization.sources.map((source, index) => (
            <span key={`${source.code}-${source.retrieved_at}`}>
              {index > 0 && ', '}
              {source.url ? (
                <a href={source.url} target="_blank" rel="noopener noreferrer">
                  {sourceLabel(source)}
                </a>
              ) : (
                sourceLabel(source)
              )}
            </span>
          ))}
        </Typography.Text>
      )}
    </>
  );
}

/**
 * Who manages the resident's house and how to reach them: the management company from
 * open sources (with contacts and provenance), plus whether the УК/ТСЖ is connected to
 * Smart City and gets residents' requests directly.
 */
export function HouseInfoCard({ info }: { info: HouseInfo }) {
  const platformManager = info.platform_manager;
  const platformManagerListed = info.managing_organizations.some((organization) => organization.is_platform_manager);

  return (
    <Flex direction="column" gap="var(--space-3)" className="house-info">
      {info.managing_organizations.map((organization) => (
        <ManagingOrganizationCard
          key={`${organization.name}-${organization.ogrn ?? organization.inn ?? ''}`}
          organization={organization}
          managementMethod={info.management_method}
        />
      ))}

      {platformManager && !platformManagerListed && (
        <Flex direction="column" gap="var(--space-2)" className="surface-card house-info__company">
          <Flex gap="var(--space-2)" wrap="wrap">
            <StatusBadge label="Принимает заявки в приложении" tone="success" />
          </Flex>
          <Typography.Text variant="title" color="primary">
            {platformManager.name}
          </Typography.Text>
          <Requisites inn={platformManager.inn} ogrn={platformManager.ogrn} />
          <Typography.Text variant="description" color="secondary">
            Обслуживает дом в Smart City — ваши обращения по дому попадают к ней напрямую.
          </Typography.Text>
        </Flex>
      )}

      {!platformManager && info.managing_organizations.length === 0 && (
        <Flex direction="column" gap="var(--space-2)" className="surface-card house-info__company">
          <Typography.Text variant="body-strong" color="primary">
            Нет сведений об управляющей компании
          </Typography.Text>
          <Typography.Text variant="description" color="secondary">
            Мы пока не нашли этот дом в открытых реестрах. Обращения по нему всё равно можно отправлять — их
            рассмотрит городская служба.
          </Typography.Text>
        </Flex>
      )}
    </Flex>
  );
}
