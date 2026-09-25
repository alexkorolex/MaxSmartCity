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
    'pages/select-house/ui/SelectHousePage.tsx',
  ];

  for (const sourcePath of sources) {
    assert.doesNotMatch(read(sourcePath), /style=\{\{/);
  }
});
