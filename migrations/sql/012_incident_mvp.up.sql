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
    ('d1000000-0000-4000-8000-000000000001', 'water', 'Водоснабжение', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000002', 'electricity', 'Электроснабжение', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000003', 'building', 'Многоквартирный дом', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000004', 'road_and_yard', 'Дороги и дворы', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000005', 'waste', 'Отходы', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000006', 'emergency', 'Аварийная ситуация', TRUE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000007', 'city_infrastructure', 'Городская инфраструктура', FALSE, TRUE, now(), now()),
    ('d1000000-0000-4000-8000-000000000008', 'other', 'Другая проблема', FALSE, TRUE, now(), now())
ON CONFLICT (code) DO NOTHING;
