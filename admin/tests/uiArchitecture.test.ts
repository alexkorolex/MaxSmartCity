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

test('the main lint command validates colocated CSS files', () => {
  const packageJson = JSON.parse(read('package.json')) as { scripts: Record<string, string> };
  const stylelintConfig = read('stylelint.config.js');

  assert.match(packageJson.scripts.lint, /lint:css/);
  assert.match(packageJson.scripts['lint:css'], /stylelint/);
  assert.match(stylelintConfig, /stylelint-config-standard/);
});

test('responsive table cells provide mobile labels', () => {
  const tablePages = [
    'pages/houses/ui/HousesPage.tsx',
    'pages/incident-detail/ui/IncidentDetailPage.tsx',
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

test('message inbox uses semantic links instead of clickable table rows', () => {
  const source = read('pages/messages/ui/MessagesPage.tsx');

  assert.match(source, /<Link/);
  assert.match(source, /className="message-inbox"/);
  assert.doesNotMatch(source, /<table/);
  assert.doesNotMatch(source, /tabIndex=/);
});

test('house address search exposes combobox state', () => {
  const source = read('entities/geo/ui/HouseSearchField.tsx');

  assert.match(source, /role="combobox"/);
  assert.match(source, /aria-expanded=/);
  assert.match(source, /aria-controls=/);
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
    'features/organization-channels/ui/OrganizationChannelsCard.tsx',
    'features/complete-incident/ui/CompleteIncidentCard.tsx',
    'features/report-chat/ui/ReportChatCard.tsx',
    'pages/messages/ui/MessagesPage.tsx',
    'pages/houses/ui/HousesPage.tsx',
  ];

  for (const sourcePath of sources) {
    assert.doesNotMatch(read(sourcePath), /style=\{\{/);
  }
});

test('report chat uses an edge-to-edge workspace instead of a nested card', () => {
  const page = read('pages/report-chat/ui/ReportChatPage.tsx');
  const pageStyles = read('pages/report-chat/ui/ReportChatPage.css');
  const chat = read('features/report-chat/ui/ReportChatCard.tsx');

  assert.doesNotMatch(page, /className="page-back"/);
  assert.match(pageStyles, /max-width:\s*none/);
  assert.doesNotMatch(chat, /className="card report-chat-card"/);
  assert.match(chat, /report-chat-card__back/);
});

test('detail pages use the shared breadcrumb navigation', () => {
  const sharedExports = read('shared/ui/index.ts');
  const detailPages = [
    'pages/incident-detail/ui/IncidentDetailPage.tsx',
    'pages/organization-detail/ui/OrganizationDetailPage.tsx',
    'pages/report-detail/ui/ReportDetailPage.tsx',
    'pages/resident-detail/ui/ResidentDetailPage.tsx',
  ];

  assert.match(sharedExports, /Breadcrumbs/);
  for (const page of detailPages) assert.match(read(page), /<Breadcrumbs/);
});

test('mobile status pills stay compact and dark card outlines stay subtle', () => {
  const feedback = read('shared/ui/styles/feedback.css');
  const tables = read('shared/ui/styles/tables.css');
  const surfaces = read('shared/ui/styles/surfaces.css');
  const mapPopup = read('pages/map/ui/MapSelectionPopup.css');

  assert.match(feedback, /\.pill\s*{[^}]*width:\s*fit-content/s);
  assert.match(tables, /\.data-table td\s*>\s*\.pill\s*{[^}]*justify-self:\s*start/s);
  assert.match(surfaces, /\[data-theme="dark"\][^{]*{[^}]*var\(--border-soft\)/s);
  assert.match(mapPopup, /\[data-theme="dark"\] \.map-selection-popup/);
});
