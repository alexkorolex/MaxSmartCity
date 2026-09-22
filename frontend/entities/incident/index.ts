export { canConfirmOrDispute, INCIDENT_STATUS_LABELS } from './lib/statusLabels';
export {
  incidentDisputesQueryKey,
  incidentQueryKey,
  myHouseIncidentsQueryKey,
  useConfirmResolution,
  useDisputeResolution,
  useIncident,
  useIncidentDisputes,
  useMyHouseIncidents,
} from './model/queries';
export type { Incident, IncidentPriority, IncidentStatus, ResolutionDispute } from './model/types';
