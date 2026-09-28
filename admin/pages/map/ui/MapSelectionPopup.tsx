import { Link } from 'react-router-dom';

import { useHouseInfo } from '@/entities/geo';
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, type IncidentStatus } from '@/entities/incident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { Pill } from '@/shared/ui';
import { MapPopup } from '@/shared/ui/map';

import type { MapSelection } from './MapDataLayers';
import './MapSelectionPopup.css';

function Counter({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function HouseDetails({ houseId, address }: { houseId: string; address?: string }) {
  const info = useHouseInfo(houseId);
  const house = info.data?.house;
  const manager = info.data?.platform_manager?.name ?? info.data?.managing_organizations[0]?.name;
  return (
    <>
      <div className="font-semibold">{house?.formatted ?? address ?? 'Загружаем адрес…'}</div>
      {manager && <div className="mt-1 text-muted-foreground">{manager}</div>}
    </>
  );
}

export function MapSelectionPopup({ selection, onClose }: { selection: MapSelection; onClose: () => void }) {
  return (
    <MapPopup
      longitude={selection.longitude}
      latitude={selection.latitude}
      onClose={onClose}
      className="map-selection-popup w-72 max-w-72 text-sm"
    >
      <div className="pr-5">
        {selection.kind === 'incident' && (
          <>
            <HouseDetails houseId={selection.properties.house_id} address={selection.properties.address} />
            <ul className="m-0 mt-3 flex list-none flex-col gap-2 p-0">
              {selection.properties.incidents.map((incident) => (
                <li key={incident.incident_id} className="rounded-md bg-muted p-2">
                  <Link className="font-medium hover:underline" to={ROUTES.incident(incident.incident_id)}>
                    {incident.title}
                  </Link>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Pill
                      tone={INCIDENT_STATUS_TONES[incident.status as IncidentStatus] ?? 'neutral'}
                      label={INCIDENT_STATUS_LABELS[incident.status as IncidentStatus] ?? incident.status}
                    />
                    <span>{incident.category}</span>
                    {incident.last_report_at && <span>{formatDateTime(incident.last_report_at)}</span>}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
        {selection.kind === 'house' && (
          <>
            <HouseDetails houseId={selection.properties.house_id} address={selection.properties.address} />
            <div className="mt-3 flex flex-col gap-1">
              <Counter label="Активные инциденты" value={selection.properties.active_incidents} />
              <Counter label="Активные заявки" value={selection.properties.active_reports} />
            </div>
          </>
        )}
        {selection.kind === 'district' && (
          <>
            <div className="font-semibold">{selection.properties.name}</div>
            {selection.properties.type !== 'CITY' && (
              <div className="text-muted-foreground">{selection.properties.city}</div>
            )}
            <div className="mt-3 flex flex-col gap-1">
              <Counter label="Домов" value={selection.properties.house_count} />
              <Counter label="Активные инциденты" value={selection.properties.active_incidents} />
              <Counter label="Активные заявки" value={selection.properties.active_reports} />
            </div>
          </>
        )}
      </div>
    </MapPopup>
  );
}
