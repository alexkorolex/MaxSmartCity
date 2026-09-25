import assert from 'node:assert/strict';
import test from 'node:test';

import {
  findRegistered,
  prefillFromManager,
  shortOrganizationName,
} from '../features/register-organization/lib/prefill.ts';

test('registry legal names become short, readable names', () => {
  assert.equal(shortOrganizationName('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ДОМ-ПЛЮС"'), 'ООО «ДОМ-ПЛЮС»');
  assert.equal(
    shortOrganizationName('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "УПРАВЛЯЮЩАЯ КОМПАНИЯ "ДОМОВЛАДЕНИЕ"'),
    'ООО «УПРАВЛЯЮЩАЯ КОМПАНИЯ ДОМОВЛАДЕНИЕ»',
  );
  assert.equal(shortOrganizationName('ТСЖ "ТУХАЧЕВСКИЙ"'), 'ТСЖ «ТУХАЧЕВСКИЙ»');
  assert.equal(shortOrganizationName('ООО ДОМ-ПЛЮС'), 'ООО «ДОМ-ПЛЮС»');
  assert.equal(shortOrganizationName('Управдом'), 'Управдом');
});

test('prefill picks HOA by management method or name and builds a code from OGRN', () => {
  const company = prefillFromManager(
    { name: 'ООО ДОМ-ПЛЮС', inn: '3250056308', ogrn: '1043244013625' },
    { city: 'Брянск', managementMethod: 'УО' },
  );
  assert.deepEqual(company, {
    name: 'ООО «ДОМ-ПЛЮС»',
    type: 'MANAGEMENT_COMPANY',
    inn: '3250056308',
    ogrn: '1043244013625',
    city: 'Брянск',
    code: 'uk-1043244013625',
  });
  const hoa = prefillFromManager(
    { name: 'ТОВАРИЩЕСТВО СОБСТВЕННИКОВ ЖИЛЬЯ "ТУХАЧЕВСКИЙ"', inn: null, ogrn: '1093254014897' },
    { city: 'Брянск', managementMethod: null },
  );
  assert.equal(hoa.type, 'HOA');
  assert.equal(hoa.inn, '');
  assert.equal(hoa.code, 'tszh-1093254014897');
});

test('an organization already on the platform is found by INN or OGRN', () => {
  const registered = [{ id: '1', inn: '3250056308', ogrn: null }, { id: '2', inn: null, ogrn: '1093254014897' }];
  assert.equal(findRegistered(registered, { inn: '3250056308', ogrn: '' })?.id, '1');
  assert.equal(findRegistered(registered, { inn: '', ogrn: '1093254014897' })?.id, '2');
  assert.equal(findRegistered(registered, { inn: '', ogrn: '' }), undefined);
});
