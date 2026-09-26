"""Coverage for the admin-panel API surface: organization-scoped visibility across staff
rosters, residents, reports, incidents, assignments/work items, incident comments, and the
staff-aware ``GET /news/`` behavior. Reuses the staff/resident token + seeding helpers from
``tests/integration/test_resident_api.py`` rather than duplicating them."""

from datetime import UTC, datetime
from uuid import uuid4

from litestar.testing import TestClient

from tests.integration.test_resident_api import (  # noqa: F401
    _insert_category,
    _insert_house,
    _insert_incident,
    _insert_report,
    _insert_report_link,
    _resident_token,
    _staff_token,
    rsa_keypair,
    run_sql,
    security_env,
)


def _insert_organization(
    database_url: str, *, name: str = "Org", city: str | None = None, org_type: str = "WATER_UTILITY"
) -> str:
    organization_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO identity.organization(id, code, name, type, city, created_at, updated_at) "
        "VALUES (:id, :code, :name, :type, :city, now(), now())",
        id=organization_id,
        code=uuid4().hex,
        name=name,
        type=org_type,
        city=city,
    )
    return organization_id


def _insert_role(database_url: str, *, code: str | None = None, name: str = "Role") -> str:
    role_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO identity.role(id, code, name) VALUES (:id, :code, :name)",
        id=role_id,
        code=code or uuid4().hex,
        name=name,
    )
    return role_id


def _insert_operator_user(
    database_url: str,
    *,
    keycloak_subject: str,
    login: str | None = None,
    display_name: str = "Operator",
    email: str | None = None,
) -> str:
    operator_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO identity.operator_user"
        "(id, login, display_name, email, keycloak_subject, created_at, updated_at) "
        "VALUES (:id, :login, :display_name, :email, :keycloak_subject, now(), now())",
        id=operator_id,
        login=login or uuid4().hex,
        display_name=display_name,
        email=email,
        keycloak_subject=keycloak_subject,
    )
    return operator_id


def _insert_organization_member(
    database_url: str,
    *,
    organization_id: str,
    user_id: str,
    role_id: str,
    is_active: bool = True,
) -> str:
    member_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO identity.organization_member"
        "(id, organization_id, user_id, role_id, is_active, created_at, updated_at) "
        "VALUES (:id, :organization_id, :user_id, :role_id, :is_active, now(), now())",
        id=member_id,
        organization_id=organization_id,
        user_id=user_id,
        role_id=role_id,
        is_active=is_active,
    )
    return member_id


def _insert_assignment(
    database_url: str, *, incident_id: str, organization_id: str, role: str = "OWNER"
) -> str:
    assignment_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO collaboration.assignment"
        "(id, incident_id, organization_id, role, created_at, updated_at) "
        "VALUES (:id, :incident_id, :organization_id, :role, now(), now())",
        id=assignment_id,
        incident_id=incident_id,
        organization_id=organization_id,
        role=role,
    )
    return assignment_id


def _insert_work_item(database_url: str, *, incident_id: str, organization_id: str, created_by: str) -> str:
    work_item_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO collaboration.work_item"
        "(id, incident_id, organization_id, title, created_by, created_at, updated_at) "
        "VALUES (:id, :incident_id, :organization_id, 'Test work item', :created_by, now(), now())",
        id=work_item_id,
        incident_id=incident_id,
        organization_id=organization_id,
        created_by=created_by,
    )
    return work_item_id


def _insert_incident_comment(
    database_url: str, *, incident_id: str, author_user_id: str, text: str = "Comment"
) -> str:
    comment_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO collaboration.incident_comment"
        "(id, incident_id, author_user_id, text, created_at, updated_at) "
        "VALUES (:id, :incident_id, :author_user_id, :text, now(), now())",
        id=comment_id,
        incident_id=incident_id,
        author_user_id=author_user_id,
        text=text,
    )
    return comment_id


def _org_a_staff_setup(
    database_url: str, private_pem: str, *, city: str | None = None
) -> tuple[str, str, str]:
    """Seed one organization with one active ``housing_worker`` staff member.
    Returns ``(organization_id, operator_user_id, token)``."""
    organization_id = _insert_organization(database_url, name="Org A", city=city)
    role_id = _insert_role(database_url)
    subject = str(uuid4())
    operator_id = _insert_operator_user(database_url, keycloak_subject=subject, display_name="Org A Worker")
    _insert_organization_member(
        database_url, organization_id=organization_id, user_id=operator_id, role_id=role_id
    )
    token = _staff_token(private_pem, subject=subject, roles=["housing_worker"])
    return organization_id, operator_id, token


def _full_incident_chain(
    database_url: str, *, organization_id: str, resident_id: str | None = None, house_id: str | None = None
) -> tuple[str, str, str]:
    """Seed a category/incident/report/link/assignment all connected, so the org is
    "responsible for" the incident. Returns ``(incident_id, report_id, assignment_id)``."""
    category_id = _insert_category(database_url)
    incident_id = _insert_incident(database_url, category_id=category_id, status="TRIAGE")
    report_id = _insert_report(database_url, resident_id=resident_id, house_id=house_id)
    _insert_report_link(database_url, incident_id=incident_id, report_id=report_id)
    assignment_id = _insert_assignment(database_url, incident_id=incident_id, organization_id=organization_id)
    return incident_id, report_id, assignment_id


# --- Admin: unrestricted visibility --------------------------------------------------


def test_admin_sees_all_organization_scoped_resources(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])

    org_a, operator_a, _token_a = _org_a_staff_setup(database_url, private_pem, city="Брянск")
    org_b, operator_b, _token_b = _org_a_staff_setup(database_url, private_pem, city="Бахчисарай")

    resident_id, _resident_token_value = _resident_token(api_client)
    incident_a, report_a, _assignment_a = _full_incident_chain(
        database_url, organization_id=org_a, resident_id=resident_id
    )
    incident_b, report_b, _assignment_b = _full_incident_chain(
        database_url, organization_id=org_b, resident_id=resident_id
    )
    comment_a = _insert_incident_comment(database_url, incident_id=incident_a, author_user_id=operator_a)
    comment_b = _insert_incident_comment(database_url, incident_id=incident_b, author_user_id=operator_b)

    headers = {"Authorization": f"Bearer {admin_token}"}

    # Direct-id fetches, not the list endpoint: the list is paginated (default limit 50)
    # and the shared dev/test database accumulates organizations across every previous
    # test run, so a freshly created org is not guaranteed to land on the first page.
    assert api_client.get(f"/identity/organizations/{org_a}", headers=headers).status_code == 200
    assert api_client.get(f"/identity/organizations/{org_b}", headers=headers).status_code == 200

    # Same reasoning: operator-users sorts ascending by login and incidents sorts
    # ascending by id, neither of which puts freshly created rows anywhere near a
    # 50-row first page once the shared database has accumulated more than that.
    assert api_client.get(f"/identity/operator-users/{operator_a}", headers=headers).status_code == 200
    assert api_client.get(f"/identity/operator-users/{operator_b}", headers=headers).status_code == 200
    assert api_client.get(f"/incidents/{incident_a}", headers=headers).status_code == 200
    assert api_client.get(f"/incidents/{incident_b}", headers=headers).status_code == 200

    # Residents/reports/comments sort newest-first, so a plain list check is safe.
    residents = api_client.get("/identity/residents/", headers=headers)
    assert residents.status_code == 200
    assert resident_id in {item["id"] for item in residents.json()}

    reports = api_client.get("/reports/", headers=headers)
    assert reports.status_code == 200
    report_ids = {item["id"] for item in reports.json()}
    assert {report_a, report_b} <= report_ids

    comments = api_client.get("/collaboration/incident-comments/", headers=headers)
    assert comments.status_code == 200
    comment_ids = {item["id"] for item in comments.json()}
    assert {comment_a, comment_b} <= comment_ids


# --- Non-admin staff: confined to their own organization ------------------------------


def test_organization_staff_sees_only_their_own_organization_and_404s_on_other_org_resources(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair

    org_a, operator_a, token_a = _org_a_staff_setup(database_url, private_pem, city="Брянск")
    org_b, operator_b, _token_b = _org_a_staff_setup(database_url, private_pem, city="Бахчисарай")

    resident_a, _ = _resident_token(api_client, display_name="Resident A")
    resident_b, _ = _resident_token(api_client, display_name="Resident B")

    incident_a, report_a, _assignment_a = _full_incident_chain(
        database_url, organization_id=org_a, resident_id=resident_a
    )
    incident_b, report_b, _assignment_b = _full_incident_chain(
        database_url, organization_id=org_b, resident_id=resident_b
    )
    comment_a = _insert_incident_comment(database_url, incident_id=incident_a, author_user_id=operator_a)
    comment_b = _insert_incident_comment(database_url, incident_id=incident_b, author_user_id=operator_b)

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # --- Lists: org A's own data appears, org B's does not -----------------------
    operators = api_client.get("/identity/operator-users/", headers=headers_a)
    assert operators.status_code == 200
    operator_ids = {item["id"] for item in operators.json()}
    assert operator_a in operator_ids
    assert operator_b not in operator_ids

    residents = api_client.get("/identity/residents/", headers=headers_a)
    assert residents.status_code == 200
    resident_ids = {item["id"] for item in residents.json()}
    assert resident_a in resident_ids
    assert resident_b not in resident_ids

    reports = api_client.get("/reports/", headers=headers_a)
    assert reports.status_code == 200
    report_ids = {item["id"] for item in reports.json()}
    assert report_a in report_ids
    assert report_b not in report_ids

    incidents = api_client.get("/incidents/", headers=headers_a)
    assert incidents.status_code == 200
    incident_ids = {item["id"] for item in incidents.json()}
    assert incident_a in incident_ids
    assert incident_b not in incident_ids

    comments = api_client.get("/collaboration/incident-comments/", headers=headers_a)
    assert comments.status_code == 200
    comment_ids = {item["id"] for item in comments.json()}
    assert comment_a in comment_ids
    assert comment_b not in comment_ids

    # --- Direct-id fetches of another organization's resources 404, not 403 ------
    assert api_client.get(f"/identity/operator-users/{operator_b}", headers=headers_a).status_code == 404
    assert api_client.get(f"/identity/residents/{resident_b}", headers=headers_a).status_code == 404

    # organization_id filter: passing another org's id is a 403 (probing by id)
    forbidden_org_filter = api_client.get(
        "/identity/operator-users/", params={"organization_id": org_b}, headers=headers_a
    )
    assert forbidden_org_filter.status_code == 403


def test_assignments_and_work_items_scoped_to_organization(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    org_a, operator_a, token_a = _org_a_staff_setup(database_url, private_pem)
    org_b, operator_b, _token_b = _org_a_staff_setup(database_url, private_pem)

    category_id = _insert_category(database_url)
    incident_a = _insert_incident(database_url, category_id=category_id, status="TRIAGE")
    incident_b = _insert_incident(database_url, category_id=category_id, status="TRIAGE")
    assignment_a = _insert_assignment(database_url, incident_id=incident_a, organization_id=org_a)
    assignment_b = _insert_assignment(database_url, incident_id=incident_b, organization_id=org_b)
    work_item_a = _insert_work_item(
        database_url, incident_id=incident_a, organization_id=org_a, created_by=operator_a
    )
    work_item_b = _insert_work_item(
        database_url, incident_id=incident_b, organization_id=org_b, created_by=operator_b
    )

    headers_a = {"Authorization": f"Bearer {token_a}"}

    assignments = api_client.get("/collaboration/assignments/", headers=headers_a)
    assert assignments.status_code == 200
    assignment_ids = {item["id"] for item in assignments.json()}
    assert assignment_a in assignment_ids
    assert assignment_b not in assignment_ids

    work_items = api_client.get("/collaboration/work-items/", headers=headers_a)
    assert work_items.status_code == 200
    work_item_ids = {item["id"] for item in work_items.json()}
    assert work_item_a in work_item_ids
    assert work_item_b not in work_item_ids


def test_incident_comment_create_scoped_to_assigned_organization(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    org_a, _operator_a, token_a = _org_a_staff_setup(database_url, private_pem)
    _org_b, _operator_b, _token_b = _org_a_staff_setup(database_url, private_pem)

    category_id = _insert_category(database_url)
    incident_assigned = _insert_incident(database_url, category_id=category_id, status="TRIAGE")
    incident_unassigned = _insert_incident(database_url, category_id=category_id, status="TRIAGE")
    _insert_assignment(database_url, incident_id=incident_assigned, organization_id=org_a)

    headers_a = {"Authorization": f"Bearer {token_a}"}

    allowed = api_client.post(
        "/collaboration/incident-comments/",
        json={"incident_id": incident_assigned, "text": "На месте, разбираемся"},
        headers=headers_a,
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["text"] == "На месте, разбираемся"
    assert allowed.json()["visibility"] == "INTERNAL"
    assert "author_display_name" in allowed.json()

    forbidden = api_client.post(
        "/collaboration/incident-comments/",
        json={"incident_id": incident_unassigned, "text": "Should not work"},
        headers=headers_a,
    )
    assert forbidden.status_code == 403


# --- City filtering ---------------------------------------------------------------


def test_city_filters_operator_users_and_residents(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    org_bryansk, operator_bryansk, _ = _org_a_staff_setup(database_url, private_pem, city="Брянск")
    org_crimea, operator_crimea, _ = _org_a_staff_setup(database_url, private_pem, city="Бахчисарай")

    house_bryansk = _insert_house(database_url, city="Брянск")
    house_crimea = _insert_house(database_url, city="Бахчисарай")

    resident_bryansk, _ = _resident_token(api_client, display_name="Bryansk Resident")
    resident_crimea, _ = _resident_token(api_client, display_name="Crimea Resident")
    run_sql(
        database_url,
        "UPDATE identity.resident SET house_id = :house_id WHERE id = :resident_id",
        house_id=house_bryansk,
        resident_id=resident_bryansk,
    )
    run_sql(
        database_url,
        "UPDATE identity.resident SET house_id = :house_id WHERE id = :resident_id",
        house_id=house_crimea,
        resident_id=resident_crimea,
    )

    operators_filtered = api_client.get(
        "/identity/operator-users/", params={"city": "Брянск"}, headers=headers
    )
    assert operators_filtered.status_code == 200
    filtered_ids = {item["id"] for item in operators_filtered.json()}
    assert operator_bryansk in filtered_ids
    assert operator_crimea not in filtered_ids

    residents_filtered = api_client.get("/identity/residents/", params={"city": "Брянск"}, headers=headers)
    assert residents_filtered.status_code == 200
    resident_ids_filtered = {item["id"] for item in residents_filtered.json()}
    assert resident_bryansk in resident_ids_filtered
    assert resident_crimea not in resident_ids_filtered

    _ = org_bryansk, org_crimea


def test_city_filters_reports(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])
    headers = {"Authorization": f"Bearer {admin_token}"}

    house_bryansk = _insert_house(database_url, city="Брянск")
    house_crimea = _insert_house(database_url, city="Бахчисарай")
    report_bryansk = _insert_report(database_url, resident_id=None, house_id=house_bryansk)
    report_crimea = _insert_report(database_url, resident_id=None, house_id=house_crimea)

    filtered = api_client.get("/reports/", params={"city": "Брянск"}, headers=headers)
    assert filtered.status_code == 200
    filtered_ids = {item["id"] for item in filtered.json()}
    assert report_bryansk in filtered_ids
    assert report_crimea not in filtered_ids


# --- Single report: owning resident / org-scoped staff / everyone else ---------------


def test_report_detail_and_attachments_scoped_by_owner_or_organization(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])

    org_a, _operator_a, token_a = _org_a_staff_setup(database_url, private_pem)
    _org_b, _operator_b, token_b = _org_a_staff_setup(database_url, private_pem)

    owner_id, owner_token = _resident_token(api_client, display_name="Owner")
    _other_id, other_token = _resident_token(api_client, display_name="Other")

    _incident_id, report_id, _assignment_id = _full_incident_chain(
        database_url, organization_id=org_a, resident_id=owner_id
    )

    # No token at all: the detail endpoint requires authentication now, full stop.
    assert api_client.get(f"/reports/{report_id}").status_code == 401

    # Owning resident: sees both the report and its (empty) attachment list.
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    assert api_client.get(f"/reports/{report_id}", headers=owner_headers).status_code == 200
    assert api_client.get(f"/reports/{report_id}/attachments", headers=owner_headers).status_code == 200

    # A different resident gets 404, not 403 - the report's existence isn't revealed.
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert api_client.get(f"/reports/{report_id}", headers=other_headers).status_code == 404
    assert api_client.get(f"/reports/{report_id}/attachments", headers=other_headers).status_code == 404

    # Staff at the assigned organization (org_a) can see it; staff at an unrelated
    # organization (org_b) cannot, even though both are legitimate district_admins.
    scoped_headers = {"Authorization": f"Bearer {token_a}"}
    assert api_client.get(f"/reports/{report_id}", headers=scoped_headers).status_code == 200
    assert api_client.get(f"/reports/{report_id}/attachments", headers=scoped_headers).status_code == 200

    unrelated_headers = {"Authorization": f"Bearer {token_b}"}
    assert api_client.get(f"/reports/{report_id}", headers=unrelated_headers).status_code == 404
    assert api_client.get(f"/reports/{report_id}/attachments", headers=unrelated_headers).status_code == 404

    # Admin sees any report regardless of organization.
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    assert api_client.get(f"/reports/{report_id}", headers=admin_headers).status_code == 200
    assert api_client.get(f"/reports/{report_id}/attachments", headers=admin_headers).status_code == 200


# --- News: resident / admin / non-admin staff visibility ------------------------------


def test_news_visibility_for_resident_admin_and_non_admin_staff(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])
    _org, _operator, worker_token = _org_a_staff_setup(database_url, private_pem)
    _resident_id, resident_token = _resident_token(api_client)

    # Admin creates a published post and its own draft.
    published = api_client.post(
        "/news/",
        json={"title": "Published", "body": "Body"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert published.status_code == 201, published.text
    published_id = published.json()["id"]
    api_client.patch(
        f"/news/{published_id}",
        json={"is_published": True, "published_at": datetime.now(UTC).isoformat()},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    admin_draft = api_client.post(
        "/news/",
        json={"title": "Admin draft", "body": "Body"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_draft.status_code == 201
    admin_draft_id = admin_draft.json()["id"]

    # The district_admin/housing_worker creates their own draft.
    worker_draft = api_client.post(
        "/news/",
        json={"title": "Worker draft", "body": "Body"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert worker_draft.status_code == 201
    worker_draft_id = worker_draft.json()["id"]

    # Resident: published only.
    resident_list = api_client.get("/news/", headers={"Authorization": f"Bearer {resident_token}"})
    resident_ids = {item["id"] for item in resident_list.json()}
    assert published_id in resident_ids
    assert admin_draft_id not in resident_ids
    assert worker_draft_id not in resident_ids

    # Admin: everything.
    admin_list = api_client.get("/news/", headers={"Authorization": f"Bearer {admin_token}"})
    admin_ids = {item["id"] for item in admin_list.json()}
    assert {published_id, admin_draft_id, worker_draft_id} <= admin_ids

    # Non-admin staff: published + their own draft, not someone else's draft.
    worker_list = api_client.get("/news/", headers={"Authorization": f"Bearer {worker_token}"})
    worker_ids = {item["id"] for item in worker_list.json()}
    assert published_id in worker_ids
    assert worker_draft_id in worker_ids
    assert admin_draft_id not in worker_ids


def test_news_update_and_delete_scoped_to_author(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    """A district_admin/housing_worker may edit or delete only their own posts - never
    another author's, including the admin's - even though `require_staff()` alone would
    let any staff role through."""
    private_pem, _ = rsa_keypair
    admin_token = _staff_token(private_pem, subject=str(uuid4()), roles=["admin"])
    _org, _operator, worker_token = _org_a_staff_setup(database_url, private_pem)

    admin_post = api_client.post(
        "/news/",
        json={"title": "Admin post", "body": "Body"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_post.status_code == 201
    admin_post_id = admin_post.json()["id"]

    worker_post = api_client.post(
        "/news/",
        json={"title": "Worker post", "body": "Body"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert worker_post.status_code == 201
    worker_post_id = worker_post.json()["id"]

    # Worker cannot edit or delete the admin's post.
    forbidden_update = api_client.patch(
        f"/news/{admin_post_id}",
        json={"title": "Hijacked"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert forbidden_update.status_code == 403

    forbidden_delete = api_client.delete(
        f"/news/{admin_post_id}", headers={"Authorization": f"Bearer {worker_token}"}
    )
    assert forbidden_delete.status_code == 403

    # Worker can edit and delete their own post.
    own_update = api_client.patch(
        f"/news/{worker_post_id}",
        json={"title": "Updated by author"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert own_update.status_code == 200, own_update.text
    assert own_update.json()["title"] == "Updated by author"

    # Admin can edit and delete anyone's post.
    admin_edit_of_worker_post = api_client.patch(
        f"/news/{worker_post_id}",
        json={"title": "Edited by admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_edit_of_worker_post.status_code == 200

    admin_delete_of_worker_post = api_client.delete(
        f"/news/{worker_post_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_delete_of_worker_post.status_code == 204


# --- Staff with no active organization membership: empty, not an error ----------------


def test_staff_without_active_membership_gets_empty_lists(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    unassigned_token = _staff_token(private_pem, subject=str(uuid4()), roles=["housing_worker"])
    headers = {"Authorization": f"Bearer {unassigned_token}"}

    # Seed some organization-scoped data elsewhere so an empty result is a real assertion,
    # not a vacuous one.
    org_a, operator_a, _token_a = _org_a_staff_setup(database_url, private_pem)
    incident_a, _report_a, _assignment_a = _full_incident_chain(database_url, organization_id=org_a)
    _insert_incident_comment(database_url, incident_id=incident_a, author_user_id=operator_a)

    assert api_client.get("/identity/operator-users/", headers=headers).json() == []
    assert api_client.get("/identity/residents/", headers=headers).json() == []
    assert api_client.get("/reports/", headers=headers).json() == []
    assert api_client.get("/incidents/", headers=headers).json() == []
    assert api_client.get("/collaboration/assignments/", headers=headers).json() == []
    assert api_client.get("/collaboration/work-items/", headers=headers).json() == []
    assert api_client.get("/collaboration/incident-comments/", headers=headers).json() == []

    forbidden_comment = api_client.post(
        "/collaboration/incident-comments/",
        json={"incident_id": incident_a, "text": "Should not work"},
        headers=headers,
    )
    assert forbidden_comment.status_code == 403


def _staff_of(database_url: str, private_pem: str, organization_id: str, role: str) -> str:
    subject = str(uuid4())
    operator_id = _insert_operator_user(database_url, keycloak_subject=subject, display_name=f"{role} worker")
    _insert_organization_member(
        database_url,
        organization_id=organization_id,
        user_id=operator_id,
        role_id=_insert_role(database_url),
    )
    return _staff_token(private_pem, subject=subject, roles=[role])


def _resident_of(api_client: TestClient, database_url: str, house_id: str | None) -> str:
    resident_id, token = _resident_token(api_client)
    run_sql(
        database_url,
        "UPDATE identity.resident SET house_id = :house WHERE id = :id",
        house=house_id,
        id=resident_id,
    )
    return token


def _managed_house(database_url: str, organization_id: str, *, city: str, active: bool = True) -> str:
    house_id = _insert_house(database_url, city=city, formatted=f"{city}, {uuid4().hex[:6]}")
    run_sql(
        database_url,
        "INSERT INTO geo.house_management(id, house_id, organization_id, is_active, created_at, updated_at) "
        "VALUES (:id, :house, :organization, :active, now(), now())",
        id=str(uuid4()),
        house=house_id,
        organization=organization_id,
        active=active,
    )
    return house_id


def _insert_territory(database_url: str, name: str, parent_id: str | None = None) -> str:
    territory_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO geo.administrative_area(id, parent_id, name, type, created_at, updated_at) "
        "VALUES (:id, :parent, :name, :type, now(), now())",
        id=territory_id,
        parent=parent_id,
        name=name,
        type="DISTRICT" if parent_id else "CITY",
    )
    return territory_id


def _place(database_url: str, house_id: str, territory_id: str) -> None:
    run_sql(
        database_url,
        "UPDATE geo.house SET administrative_area_id = :territory WHERE id = :house",
        territory=territory_id,
        house=house_id,
    )


def _insert_authority(database_url: str, name: str, kind: str, territory_id: str) -> str:
    organization_id = str(uuid4())
    run_sql(
        database_url,
        "INSERT INTO identity.organization"
        "(id, code, name, type, authority_kind, territory_id, created_at, updated_at) "
        "VALUES (:id, :code, :name, 'ADMINISTRATION', :kind, :territory, now(), now())",
        id=organization_id,
        code=uuid4().hex,
        name=name,
        kind=kind,
        territory=territory_id,
    )
    return organization_id


def test_news_reaches_only_the_residents_of_the_publishers_houses(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    city = f"Город-{uuid4().hex[:6]}"
    city_territory = _insert_territory(database_url, city)
    district_a = _insert_territory(database_url, "Район А", city_territory)
    district_b = _insert_territory(database_url, "Район Б", city_territory)
    uk_a = _insert_organization(database_url, name="УК А", city=city, org_type="MANAGEMENT_COMPANY")
    uk_b = _insert_organization(database_url, name="УК Б", city=city, org_type="MANAGEMENT_COMPANY")
    city_hall = _insert_authority(database_url, "Администрация города", "CITY_ADMINISTRATION", city_territory)
    district_hall = _insert_authority(
        database_url, "Администрация района А", "DISTRICT_ADMINISTRATION", district_a
    )
    house_a = _managed_house(database_url, uk_a, city=city)
    house_b = _managed_house(database_url, uk_b, city=city)
    house_former = _managed_house(database_url, uk_a, city=city, active=False)
    house_elsewhere = _insert_house(database_url, city="Другой город")
    _place(database_url, house_a, district_a)
    _place(database_url, house_b, district_b)
    _place(database_url, house_former, city_territory)

    def publish(token: str, title: str) -> str:
        headers = {"Authorization": f"Bearer {token}"}
        created = api_client.post("/news/", json={"title": title, "body": "Body"}, headers=headers)
        assert created.status_code == 201, created.text
        published = api_client.patch(
            f"/news/{created.json()['id']}",
            json={"is_published": True, "published_at": datetime.now(UTC).isoformat()},
            headers=headers,
        )
        assert published.status_code == 200, published.text
        return title

    titles = {"Для всех", "От УК А", "От УК Б", "От города", "От района А"}
    publish(_staff_token(private_pem, subject=str(uuid4()), roles=["admin"]), "Для всех")
    worker_a = _staff_of(database_url, private_pem, uk_a, "housing_worker")
    publish(worker_a, "От УК А")
    publish(_staff_of(database_url, private_pem, uk_b, "housing_worker"), "От УК Б")
    publish(_staff_of(database_url, private_pem, city_hall, "district_admin"), "От города")
    district_worker = _staff_of(database_url, private_pem, district_hall, "district_admin")
    publish(district_worker, "От района А")

    def feed(token: str) -> set[str]:
        response = api_client.get(
            "/news/", params={"limit": 100}, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, response.text
        return {item["title"] for item in response.json()} & titles

    assert feed(_resident_of(api_client, database_url, house_a)) == {
        "Для всех",
        "От УК А",
        "От города",
        "От района А",
    }
    assert feed(_resident_of(api_client, database_url, house_b)) == {"Для всех", "От УК Б", "От города"}
    assert feed(_resident_of(api_client, database_url, house_former)) == {"Для всех", "От города"}
    assert feed(_resident_of(api_client, database_url, house_elsewhere)) == {"Для всех"}
    assert feed(_resident_of(api_client, database_url, None)) == {"Для всех"}
    assert feed(worker_a) == {"Для всех", "От УК А"}
    assert feed(district_worker) == {"Для всех", "От района А"}


def test_news_audience_cannot_be_chosen_by_the_client(
    api_client: TestClient,
    database_url: str,
    rsa_keypair: tuple[str, str],  # noqa: F811
) -> None:
    private_pem, _ = rsa_keypair
    uk = _insert_organization(database_url, name="УК", org_type="MANAGEMENT_COMPANY")
    other = _insert_organization(database_url, name="Чужая УК", org_type="MANAGEMENT_COMPANY")
    worker = _staff_of(database_url, private_pem, uk, "housing_worker")

    forged = api_client.post(
        "/news/",
        json={"title": "T", "body": "B", "organization_id": other},
        headers={"Authorization": f"Bearer {worker}"},
    )
    assert forged.status_code == 400
    created = api_client.post(
        "/news/", json={"title": "T", "body": "B"}, headers={"Authorization": f"Bearer {worker}"}
    )
    assert created.json()["organization_id"] == uk
