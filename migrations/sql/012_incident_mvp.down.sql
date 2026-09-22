DELETE FROM reports.problem_category AS category
WHERE category.id IN (
    'd1000000-0000-4000-8000-000000000001',
    'd1000000-0000-4000-8000-000000000002',
    'd1000000-0000-4000-8000-000000000003',
    'd1000000-0000-4000-8000-000000000004',
    'd1000000-0000-4000-8000-000000000005',
    'd1000000-0000-4000-8000-000000000006',
    'd1000000-0000-4000-8000-000000000007',
    'd1000000-0000-4000-8000-000000000008'
)
AND NOT EXISTS (
    SELECT 1 FROM reports.report AS report WHERE report.category_id = category.id
)
AND NOT EXISTS (
    SELECT 1 FROM incidents.incident AS incident WHERE incident.category_id = category.id
);

-- statement-breakpoint

DROP INDEX collaboration.uq_assignment_active_role;
