import { useState, type FormEvent } from 'react';

import {
  AUTHORITY_KIND_LABELS,
  AUTHORITY_KINDS,
  EMPTY_STAFF_ACCOUNT,
  isStaffAccountComplete,
  isValidInn,
  isValidOgrn,
  StaffAccountFields,
  useRegisterAuthority,
  type AuthorityKind,
  type OrganizationRegistrationResult,
  type StaffAccountPayload,
} from '@/entities/organization';
import { flattenTerritoryTree, TERRITORY_TYPE_LABELS, useTerritories } from '@/entities/territory';
import { apiErrorMessage } from '@/shared/lib';

import './RegisterAuthorityForm.css';

interface RegisterAuthorityFormProps {
  onRegistered: (organizationId: string, registration: OrganizationRegistrationResult) => void;
  onCancel: () => void;
}

export function RegisterAuthorityForm({ onRegistered, onCancel }: RegisterAuthorityFormProps) {
  const territories = useTerritories();
  const register = useRegisterAuthority();
  const [name, setName] = useState('');
  const [kind, setKind] = useState<AuthorityKind>('DISTRICT_ADMINISTRATION');
  const [territoryId, setTerritoryId] = useState('');
  const [inn, setInn] = useState('');
  const [ogrn, setOgrn] = useState('');
  const [employee, setEmployee] = useState<StaffAccountPayload>(EMPTY_STAFF_ACCOUNT);

  const innInvalid = inn.trim() !== '' && !isValidInn(inn.trim());
  const ogrnInvalid = ogrn.trim() !== '' && !isValidOgrn(ogrn.trim());
  const canSubmit =
    name.trim() && territoryId && !innInvalid && !ogrnInvalid && isStaffAccountComplete(employee) && !register.isPending;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    register.mutate(
      {
        name: name.trim(),
        authority_kind: kind,
        territory_id: territoryId,
        inn: inn.trim() || null,
        ogrn: ogrn.trim() || null,
        employee: { ...employee, email: employee.email?.trim() || null },
      },
      { onSuccess: (result) => onRegistered(result.organization_id, result) },
    );
  }

  const items = flattenTerritoryTree(territories.data ?? []);

  return (
    <form className="authority-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div className="form-grid__wide">
          <label className="field-label" htmlFor="authority-name">
            Название
          </label>
          <input
            id="authority-name"
            className="field"
            placeholder="Администрация Бежицкого района города Брянска"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="authority-kind">
            Вид органа
          </label>
          <select
            id="authority-kind"
            className="field"
            value={kind}
            onChange={(event) => setKind(event.target.value as AuthorityKind)}
          >
            {AUTHORITY_KINDS.map((value) => (
              <option key={value} value={value}>
                {AUTHORITY_KIND_LABELS[value]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="authority-territory">
            Территория
          </label>
          <select
            id="authority-territory"
            className="field"
            value={territoryId}
            onChange={(event) => setTerritoryId(event.target.value)}
          >
            <option value="">Выберите территорию</option>
            {items.map(({ node, depth }) => (
              <option key={node.id} value={node.id}>
                {`${'  '.repeat(depth)}${node.name} — ${TERRITORY_TYPE_LABELS[node.type].toLowerCase()}`}
              </option>
            ))}
          </select>
          <div className="form-hint">Новости и статистика органа — по этой территории со всеми её делениями</div>
        </div>
        <div>
          <label className="field-label" htmlFor="authority-inn">
            ИНН <span className="cell-muted">(необязательно)</span>
          </label>
          <input
            id="authority-inn"
            className="field"
            inputMode="numeric"
            value={inn}
            onChange={(event) => setInn(event.target.value.replace(/\D/g, ''))}
            aria-invalid={innInvalid || undefined}
          />
          {innInvalid && <div className="form-hint form-hint--error">Проверьте ИНН</div>}
        </div>
        <div>
          <label className="field-label" htmlFor="authority-ogrn">
            ОГРН <span className="cell-muted">(необязательно)</span>
          </label>
          <input
            id="authority-ogrn"
            className="field"
            inputMode="numeric"
            value={ogrn}
            onChange={(event) => setOgrn(event.target.value.replace(/\D/g, ''))}
            aria-invalid={ogrnInvalid || undefined}
          />
          {ogrnInvalid && <div className="form-hint form-hint--error">Проверьте ОГРН</div>}
        </div>
      </div>
      <div className="form-section-title">Первый сотрудник</div>
      <StaffAccountFields idPrefix="authority-employee" value={employee} onChange={setEmployee} />
      {register.isError && <div className="form-error">{apiErrorMessage(register.error)}</div>}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!canSubmit}>
          {register.isPending ? 'Регистрируем…' : 'Зарегистрировать орган власти'}
        </button>
        <button type="button" className="btn btn--ghost" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  );
}
