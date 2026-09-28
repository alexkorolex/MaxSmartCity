import { useEffect, useRef } from 'react';

import { HouseSearchField, useHouseInfo, type House, type HouseInfo, type HouseManagingOrganization } from '@/entities/geo';
import { formatCalendarDate, formatPhone } from '@/shared/lib';
import { Pill } from '@/shared/ui';

import { prefillFromManager, shortOrganizationName, type RequisitesPrefill } from '../lib/prefill';

function sourceHost(url: string | null, code: string): string {
  if (!url) return code;
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return code;
  }
}

function candidateKey(candidate: HouseManagingOrganization): string {
  return candidate.ogrn ?? candidate.inn ?? candidate.name;
}

interface HouseManagerLookupProps {
  house: House | null;
  onHouseChange: (house: House | null) => void;
  appliedKey: string | null;
  autoApply: boolean;
  onApply: (prefill: RequisitesPrefill, key: string, candidate: HouseManagingOrganization) => void;
  onInfo: (info: HouseInfo | undefined) => void;
}

export function HouseManagerLookup({ house, onHouseChange, appliedKey, autoApply, onApply, onInfo }: HouseManagerLookupProps) {
  const info = useHouseInfo(house?.house_id);
  const autoAppliedFor = useRef<string | null>(null);
  const candidates = info.data?.managing_organizations ?? [];

  function apply(candidate: HouseManagingOrganization) {
    if (!info.data) return;
    onApply(
      prefillFromManager(candidate, {
        city: info.data.house.city,
        managementMethod: info.data.management_method,
      }),
      candidateKey(candidate),
      candidate,
    );
  }

  useEffect(() => {
    onInfo(info.data);
    const first = info.data?.managing_organizations[0];
    if (!info.data || !first || !autoApply || autoAppliedFor.current === info.data.house.house_id) return;
    autoAppliedFor.current = info.data.house.house_id;
    apply(first);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [info.data, autoApply]);

  return (
    <div className="manager-lookup">
      <HouseSearchField value={house} onChange={onHouseChange} />

      {house && info.isLoading && <div className="form-hint">Ищем сведения об управляющей организации…</div>}

      {info.data && candidates.length === 0 && (
        <div className="form-hint">
          По этому дому нет сведений об управляющей организации в открытых источниках — заполните реквизиты вручную.
        </div>
      )}

      {candidates.length > 0 && (
        <div className="manager-lookup__candidates">
          <div className="form-hint">
            {candidates.length === 1
              ? 'Дом обслуживает по данным открытых источников:'
              : 'По данным открытых источников дом обслуживают несколько организаций — выберите нужную:'}
          </div>
          {candidates.map((candidate) => {
            const key = candidateKey(candidate);
            const isApplied = key === appliedKey;
            return (
              <div key={key} className={`manager-lookup__candidate${isApplied ? ' manager-lookup__candidate--applied' : ''}`}>
                <div className="manager-lookup__head">
                  <div>
                    <div className="manager-lookup__name">{shortOrganizationName(candidate.name)}</div>
                    <div className="manager-lookup__meta">
                      {[candidate.inn && `ИНН ${candidate.inn}`, candidate.ogrn && `ОГРН ${candidate.ogrn}`]
                        .filter(Boolean)
                        .join(' · ') || 'Реквизиты не опубликованы'}
                    </div>
                  </div>
                  {isApplied ? (
                    <Pill tone="success" label="Подставлено в форму" />
                  ) : (
                    <button type="button" className="btn btn--ghost btn--small" onClick={() => apply(candidate)}>
                      Подставить
                    </button>
                  )}
                </div>
                {(candidate.phones.length > 0 || candidate.email || candidate.website) && (
                  <div className="manager-lookup__contacts">
                    {candidate.phones.map((phone) => (
                      <a key={phone} href={`tel:${phone}`}>
                        {formatPhone(phone)}
                      </a>
                    ))}
                    {candidate.email && <a href={`mailto:${candidate.email}`}>{candidate.email}</a>}
                    {candidate.website && (
                      <a href={candidate.website} target="_blank" rel="noopener noreferrer">
                        {sourceHost(candidate.website, candidate.website)}
                      </a>
                    )}
                  </div>
                )}
                <div className="manager-lookup__sources">
                  Источники:{' '}
                  {candidate.sources
                    .map(
                      (source) =>
                        `${sourceHost(source.url, source.code)} (${formatCalendarDate(source.retrieved_at, { year: true })})`,
                    )
                    .join(', ')}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
