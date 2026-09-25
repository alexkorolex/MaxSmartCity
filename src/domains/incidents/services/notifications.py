"""Who hears about an incident: residents (in-app notifications) and organizations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.domains.collaboration.enums import AssignmentStatus
from src.domains.collaboration.models import Assignment
from src.domains.geo.models import Address, House, HouseManagement
from src.domains.geo.services import active_house_manager_id
from src.domains.identity.models import Resident
from src.domains.incidents.models import (
    Incident,
    IncidentAffectedHouse,
)
from src.domains.incidents.services.base import IncidentCoreBase
from src.domains.notifications.dispatcher import OrganizationMessage, enqueue_organization_notification
from src.domains.notifications.enums import NotificationType
from src.domains.notifications.models import Notification
from src.domains.reports.enums import ReportStatus
from src.domains.reports.models import Report
from src.max_bot.links import max_profile_url
from src.settings import admin_panel_url


class IncidentNotificationsMixin(IncidentCoreBase):
    """Notifications to the residents and organizations of an incident."""

    async def _move_linked_reports(
        self, incident: Incident, source: ReportStatus, target: ReportStatus, reason: str | None
    ) -> None:
        for report in await self._linked_reports(incident):
            if report.status is source:
                self._transition_report(report, target, reason or f"Incident {incident.status.value}")

    async def _notify_residents(
        self, incident: Incident, notification_type: NotificationType, title: str, body: str
    ) -> None:
        for report in await self._linked_reports(incident):
            if report.resident_id is None:
                continue
            self.session.add(
                Notification(
                    resident_id=report.resident_id,
                    type=notification_type,
                    title=title,
                    body=body,
                    incident_id=incident.id,
                    report_id=report.id,
                )
            )

    async def _notify_organizations(self, incident: Incident, event_type: str, title: str, body: str) -> None:
        """Everyone working on the incident: its (non-cancelled) assignees plus the
        managing organization of every affected house."""
        assigned = select(Assignment.organization_id).where(
            Assignment.incident_id == incident.id,
            Assignment.status.not_in({AssignmentStatus.REJECTED, AssignmentStatus.CANCELLED}),
        )
        managing = (
            select(HouseManagement.organization_id)
            .join(IncidentAffectedHouse, IncidentAffectedHouse.house_id == HouseManagement.house_id)
            .where(IncidentAffectedHouse.incident_id == incident.id, HouseManagement.is_active.is_(True))
        )
        organization_ids = set((await self.session.scalars(assigned.union(managing))).all())
        for organization_id in sorted(organization_ids):
            enqueue_organization_notification(
                self.session,
                OrganizationMessage(
                    organization_id=organization_id,
                    event_type=event_type,
                    title=title,
                    body=body,
                    incident_id=incident.id,
                ),
            )

    async def _notify_house_manager(self, report: Report, incident: Incident, *, new_incident: bool) -> None:
        """Route a resident's request to the УК/ТСЖ managing the house it concerns."""
        if report.house_id is None:
            return
        organization_id = await active_house_manager_id(self.session, report.house_id)
        if organization_id is None:
            return
        address = await self.session.scalar(
            select(Address.formatted)
            .join(House, House.address_id == Address.id)
            .where(House.id == report.house_id)
        )
        title = "Новая заявка жителя" if new_incident else "Новое обращение по открытой заявке"
        requester = await self._requester(report)
        lines = [f"Адрес: {address}" if address else None, f"Заявка: {incident.title}"]
        if report.text:
            lines.append(f"Текст: {report.text}")
        if requester is not None:
            lines.append(f"Заявитель: {requester['name'] or 'имя не указано'}")
            if requester["max_profile_url"]:
                lines.append(f"Профиль MAX: {requester['max_profile_url']}")
            elif requester["max_user_id"]:
                lines.append(f"MAX ID: {requester['max_user_id']} (публичного профиля нет)")
        panel = admin_panel_url()
        if panel:
            lines.append(f"Открыть в панели: {panel}/incidents/{incident.id}")
        enqueue_organization_notification(
            self.session,
            OrganizationMessage(
                organization_id=organization_id,
                event_type="RESIDENT_REPORT_RECEIVED",
                title=title,
                body="\n".join(line for line in lines if line),
                incident_id=incident.id,
                report_id=report.id,
                house_id=report.house_id,
                requester=requester,
            ),
        )

    async def _requester(self, report: Report) -> dict[str, Any] | None:
        """Who filed the report, as far as MAX told us - for the organization to reach them."""
        if report.resident_id is None:
            return None
        resident = await self.session.get(Resident, report.resident_id)
        if resident is None:
            return None
        return {
            "name": resident.display_name,
            "max_user_id": resident.max_user_id,
            "max_username": resident.username,
            "max_profile_url": max_profile_url(resident.username),
        }
