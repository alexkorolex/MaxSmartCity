import { useState, type FormEvent } from 'react';

import {
  EMPTY_STAFF_ACCOUNT,
  HOUSING_ORGANIZATION_TYPES,
  isStaffAccountComplete,
  isValidInn,
  isValidOgrn,
  ORGANIZATION_TYPE_LABELS,
  StaffAccountFields,
  useRegisterOrganization,
  type HousingOrganizationType,
  type StaffAccountPayload,
} from '@/entities/organization';
import { apiErrorMessage } from '@/shared/lib';

import './RegisterOrganizationForm.css';

interface RequisitesState {
  name: string;
  code: string;
  type: HousingOrganizationType;
  city: string;
  inn: string;
  ogrn: string;
  licenseNumber: string;
  inReserveRegistry: boolean;
}

const EMPTY_REQUISITES: RequisitesState = {
  name: '',
  code: '',
  type: 'MANAGEMENT_COMPANY',
  city: '',
  inn: '',
  ogrn: '',
  licenseNumber: '',
  inReserveRegistry: false,
};

interface RegisterOrganizationFormProps {
  onRegistered: (organizationId: string) => void;
  onCancel: () => void;
}

/**
 * Admin registers a management company (УК) or HOA (ТСЖ) together with its first
 * employee in one step - per Постановление №1616 a УК must hold a license, and only a
 * licensed УК can be on the Перечень of fallback managers.
 */
export function RegisterOrganizationForm({ onRegistered, onCancel }: RegisterOrganizationFormProps) {
  const [requisites, setRequisites] = useState<RequisitesState>(EMPTY_REQUISITES);
  const [employee, setEmployee] = useState<StaffAccountPayload>(EMPTY_STAFF_ACCOUNT);
  const register = useRegisterOrganization();

  const isManagementCompany = requisites.type === 'MANAGEMENT_COMPANY';
  const innError = requisites.inn && !isValidInn(requisites.inn) ? 'ИНН не прошёл проверку контрольной суммы' : '';
  const ogrnError = requisites.ogrn && !isValidOgrn(requisites.ogrn) ? 'ОГРН не прошёл проверку контрольной суммы' : '';
  const canSubmit =
    Boolean(requisites.name.trim()) &&
    Boolean(requisites.code.trim()) &&
    isValidInn(requisites.inn) &&
    isValidOgrn(requisites.ogrn) &&
    (!isManagementCompany || Boolean(requisites.licenseNumber.trim())) &&
    isStaffAccountComplete(employee);

  function update<K extends keyof RequisitesState>(key: K, value: RequisitesState[K]) {
    setRequisites((current) => ({ ...current, [key]: value }));
  }

  function changeType(type: HousingOrganizationType) {
    // An HOA is neither licensed nor eligible for the Перечень - drop what doesn't apply.
    setRequisites((current) =>
      type === 'HOA' ? { ...current, type, licenseNumber: '', inReserveRegistry: false } : { ...current, type },
    );
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    register.mutate(
      {
        name: requisites.name.trim(),
        code: requisites.code.trim(),
        type: requisites.type,
        city: requisites.city.trim() || null,
        inn: requisites.inn,
        ogrn: requisites.ogrn,
        license_number: isManagementCompany ? requisites.licenseNumber.trim() : null,
        in_reserve_registry: isManagementCompany && requisites.inReserveRegistry,
        employee: { ...employee, email: employee.email?.trim() || null },
      },
      { onSuccess: (result) => onRegistered(result.organization_id) },
    );
  }

  return (
    <form className="register-organization" onSubmit={handleSubmit}>
      <div className="form-section-title">Организация</div>
      <div className="form-grid">
        <div className="form-grid__wide">
          <label className="field-label" htmlFor="org-name">
            Название
          </label>
          <input
            id="org-name"
            className="field"
            placeholder="ООО «УК Уютный дом»"
            value={requisites.name}
            onChange={(event) => update('name', event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="org-type">
            Тип
          </label>
          <select
            id="org-type"
            className="field"
            value={requisites.type}
            onChange={(event) => changeType(event.target.value as HousingOrganizationType)}
          >
            {HOUSING_ORGANIZATION_TYPES.map((type) => (
              <option key={type} value={type}>
                {ORGANIZATION_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="org-code">
            Код
          </label>
          <input
            id="org-code"
            className="field"
            placeholder="uk-uyutny-dom"
            value={requisites.code}
            onChange={(event) => update('code', event.target.value)}
          />
          <div className="form-hint">Уникальный короткий идентификатор латиницей</div>
        </div>
        <div>
          <label className="field-label" htmlFor="org-inn">
            ИНН
          </label>
          <input
            id="org-inn"
            className="field"
            inputMode="numeric"
            maxLength={12}
            placeholder="10 или 12 цифр"
            value={requisites.inn}
            onChange={(event) => update('inn', event.target.value.replace(/\D/g, ''))}
          />
          {innError && <div className="form-hint form-hint--error">{innError}</div>}
        </div>
        <div>
          <label className="field-label" htmlFor="org-ogrn">
            ОГРН
          </label>
          <input
            id="org-ogrn"
            className="field"
            inputMode="numeric"
            maxLength={15}
            placeholder="13 или 15 цифр"
            value={requisites.ogrn}
            onChange={(event) => update('ogrn', event.target.value.replace(/\D/g, ''))}
          />
          {ogrnError && <div className="form-hint form-hint--error">{ogrnError}</div>}
        </div>
        <div>
          <label className="field-label" htmlFor="org-city">
            Город
          </label>
          <input
            id="org-city"
            className="field"
            placeholder="Брянск"
            value={requisites.city}
            onChange={(event) => update('city', event.target.value)}
          />
        </div>
        {isManagementCompany && (
          <div>
            <label className="field-label" htmlFor="org-license">
              Лицензия на управление МКД
            </label>
            <input
              id="org-license"
              className="field"
              placeholder="№ 032-000123"
              value={requisites.licenseNumber}
              onChange={(event) => update('licenseNumber', event.target.value)}
            />
          </div>
        )}
        {isManagementCompany && (
          <label className="checkbox-field form-grid__wide">
            <input
              type="checkbox"
              checked={requisites.inReserveRegistry}
              onChange={(event) => update('inReserveRegistry', event.target.checked)}
            />
            Включена в Перечень управляющих организаций (ГИС ЖКХ)
          </label>
        )}
      </div>

      <div className="form-section-title">Первый сотрудник</div>
      <StaffAccountFields idPrefix="org-employee" value={employee} onChange={setEmployee} />

      {register.isError && <div className="form-error">{apiErrorMessage(register.error)}</div>}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!canSubmit || register.isPending}>
          {register.isPending ? 'Регистрируем…' : 'Зарегистрировать'}
        </button>
        <button type="button" className="btn btn--ghost" onClick={onCancel} disabled={register.isPending}>
          Отмена
        </button>
      </div>
    </form>
  );
}
