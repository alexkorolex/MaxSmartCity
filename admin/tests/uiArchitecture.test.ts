import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const adminRoot = new URL('../', import.meta.url);

function read(relativePath: string): string {
  return readFileSync(new URL(relativePath, adminRoot), 'utf8');
}

test('global stylesheet delegates styles to FSD layers', () => {
  const stylesheet = read('app/styles/index.css');

  assert.match(stylesheet, /tokens\.css/);
  assert.match(stylesheet, /base\.css/);
  assert.match(stylesheet, /shared\/ui\/styles\/index\.css/);
  assert.ok(stylesheet.split('\n').length <= 6);
});

test('responsive table cells provide mobile labels', () => {
  const tablePages = [
    'pages/houses/ui/HousesPage.tsx',
    'pages/incidents/ui/IncidentsPage.tsx',
    'pages/news/ui/NewsPage.tsx',
    'pages/organization-detail/ui/OrganizationDetailPage.tsx',
    'pages/organizations/ui/OrganizationsPage.tsx',
    'pages/resident-detail/ui/ResidentDetailPage.tsx',
    'pages/residents/ui/ResidentsPage.tsx',
    'pages/staff/ui/StaffPage.tsx',
  ];

  for (const page of tablePages) {
    const source = read(page);
    const cells = source.match(/<td(?:\s[^>]*)?>/g) ?? [];
    assert.ok(cells.length > 0, `${page} should contain table cells`);
    assert.ok(cells.every((cell) => cell.includes('data-label=')), `${page} has an unlabeled mobile cell`);
  }
});

test('page and feature UI avoids inline style objects', () => {
  const sources = [
    'pages/news/ui/NewsPage.tsx',
    'pages/report-detail/ui/ReportDetailPage.tsx',
    'pages/incident-detail/ui/IncidentDetailPage.tsx',
    'features/staff-login/ui/StaffLoginForm.tsx',
    'features/register-organization/ui/RegisterOrganizationForm.tsx',
    'features/add-organization-employee/ui/AddOrganizationEmployeeForm.tsx',
    'pages/organization-detail/ui/OrganizationDetailPage.tsx',
    'features/take-house/ui/TakeHouseForm.tsx',
    'pages/houses/ui/HousesPage.tsx',
  ];

  for (const sourcePath of sources) {
    assert.doesNotMatch(read(sourcePath), /style=\{\{/);
  }
});
