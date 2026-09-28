import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const frontendRoot = new URL('../', import.meta.url);

function read(relativePath: string): string {
  return readFileSync(new URL(relativePath, frontendRoot), 'utf8');
}

test('global stylesheet delegates visual responsibility to FSD layers', () => {
  const stylesheet = read('app/styles/index.css');

  assert.match(stylesheet, /tokens\.css/);
  assert.match(stylesheet, /base\.css/);
  assert.match(stylesheet, /max-ui\.css/);
  assert.match(stylesheet, /shared\/ui\/styles\/index\.css/);
  assert.ok(stylesheet.split('\n').length <= 5);
});

test('the main lint command validates colocated CSS files', () => {
  const packageJson = JSON.parse(read('package.json')) as { scripts: Record<string, string> };

  assert.match(packageJson.scripts.lint, /lint:css/);
  assert.match(packageJson.scripts['lint:css'], /stylelint/);
  assert.match(read('stylelint.config.js'), /stylelint-config-standard/);
});

test('new interactive screens avoid inline presentation styles', () => {
  const sources = [
    'features/report-chat/ui/ReportChat.tsx',
    'features/select-house/ui/HouseSelector.tsx',
    'features/submit-report/ui/ReportForm.tsx',
    'pages/incident-card/ui/IncidentCardPage.tsx',
    'pages/incident-resolution/ui/IncidentResolutionPage.tsx',
    'pages/notifications/ui/NotificationsPage.tsx',
    'pages/report-card/ui/ReportCardPage.tsx',
    'pages/report-chat/ui/ReportChatPage.tsx',
    'pages/select-house/ui/SelectHousePage.tsx',
  ];

  for (const sourcePath of sources) {
    assert.doesNotMatch(read(sourcePath), /style=\{\{/);
  }
});

test('report chat owns the viewport instead of rendering as a content card', () => {
  const page = read('pages/report-chat/ui/ReportChatPage.tsx');
  const pageStyles = read('pages/report-chat/ui/ReportChatPage.css');
  const chat = read('features/report-chat/ui/ReportChat.tsx');

  assert.match(page, /className="report-chat-page"/);
  assert.doesNotMatch(page, /PageLayout/);
  assert.match(pageStyles, /height:\s*100dvh/);
  assert.doesNotMatch(chat, /surface-card report-chat/);
});

test('dark theme remaps MAX UI surfaces and contextual back navigation', () => {
  const maxUi = read('app/styles/max-ui.css');
  const pageLayout = read('shared/ui/page-layout/PageLayout.tsx');

  assert.match(maxUi, /--background-card:\s*var\(--surface-raised\)/);
  assert.match(maxUi, /\[data-theme="dark"\] \.app-page/);
  assert.match(pageLayout, /backLabel/);
  assert.match(pageLayout, /page-heading__back-label/);
});

test('house selection content keeps a consistent full-width mobile rhythm', () => {
  const pageStyles = read('pages/select-house/ui/SelectHousePage.css');
  const houseStyles = read('entities/geo/ui/HouseInfoCard.css');
  const sectionStyles = read('shared/ui/styles/sections.css');

  assert.match(pageStyles, /\.house-selection-page\s*>\s*\*\s*{[^}]*width:\s*100%/s);
  assert.match(houseStyles, /\.house-info\s*>\s*\*\s*{[^}]*width:\s*100%/s);
  assert.match(sectionStyles, /\.app-section\s*{[^}]*width:\s*100%/s);
});
