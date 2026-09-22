CREATE UNIQUE INDEX uq_assignment_active_role
ON collaboration.assignment (incident_id, organization_id, role)
WHERE status IN ('PROPOSED','ACCEPTED','IN_PROGRESS','BLOCKED','MONITORING');

-- statement-breakpoint

INSERT INTO reports.problem_category (
    id,
    code,
    name,
    is_critical,
    enabled,
    created_at,
    updated_at
)
VALUES
    ('d1000000-0000-4000-8000-000000000001', 'power_outage', 'Нет электричества', TRUE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000002', 'water_outage', 'Нет воды', TRUE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000003', 'gas_problem', 'Проблема с газом', TRUE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000004', 'flooding', 'Затопление или протечка', TRUE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000005', 'elevator_failure', 'Не работает лифт', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000006', 'waste', 'Мусор', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000007', 'heating', 'Нет отопления', TRUE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000008', 'other', 'Другое', FALSE, TRUE, now(), now())
ON CONFLICT (code) DO NOTHING;
