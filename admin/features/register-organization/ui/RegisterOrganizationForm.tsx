import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { useAssignHouseManagement, type House, type HouseInfo, type HouseManagingOrganization } from '@/entities/geo';
import {
  EMPTY_STAFF_ACCOUNT,
  HOUSING_ORGANIZATION_TYPES,
  isStaffAccountComplete,
  isValidInn,
  isValidOgrn,
  ORGANIZATION_TYPE_LABELS,
  StaffAccountFields,
  useOrganizations,
  useRegisterOrganization,
  type HousingOrganizationType,
  type OrganizationRegistrationResult,
  type StaffAccountPayload,
} from '@/entities/organization';
import { apiErrorMessage } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';

import { findRegistered, type RequisitesPrefill } from '../lib/prefill';
import { HouseManagerLookup } from './HouseManagerLookup';

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

const DEFAULT_BASIS = 'Сведения открытых реестров (ГИС ЖКХ) об управлении домом';

interface RegisterOrganizationFormProps {
  /** `registration` carries whether the first employee was e-mailed their credentials. */
  onRegistered: (organizationId: string, registration: OrganizationRegistrationResult) => void;
  onCancel: () => void;
}

/**
 * Admin registers a management company (УК) or HOA (ТСЖ) together with its first
 * employee in one step - per Постановление №1616 a УК must hold a license, and only a
 * licensed УК can be on the Перечень of fallback managers. Starting from a house it
 * manages, the form is prefilled from what the platform already knows about that house,
 * and the house can be attached to the new organization right away.
 */
export function RegisterOrganizationForm({ onRegistered, onCancel }: RegisterOrganizationFormProps) {
  const [requisites, setRequisites] = useState<RequisitesState>(EMPTY_REQUISITES);
  const [employee, setEmployee] = useState<StaffAccountPayload>(EMPTY_STAFF_ACCOUNT);
  const [touched, setTouched] = useState(false);
  const [house, setHouse] = useState<House | null>(null);
  const [houseInfo, setHouseInfo] = useState<HouseInfo | undefined>();
  const [applied, setApplied] = useState<{ key: string; candidate: HouseManagingOrganization } | null>(null);
  const [attachHouse, setAttachHouse] = useState(true);
  const [basis, setBasis] = useState(DEFAULT_BASIS);
  const [registered, setRegistered] = useState<OrganizationRegistrationResult | null>(null);
  const register = useRegisterOrganization();
  const assign = useAssignHouseManagement();
  const organizations = useOrganizations();
  const alreadyRegistered = findRegistered(organizations.data ?? [], requisites);
  const platformManager = houseInfo?.platform_manager ?? null;

  const isManagementCompany = requisites.type === 'MANAGEMENT_COMPANY';
  const innError = requisites.inn && !isValidInn(requisites.inn) ? 'ИНН не прошёл проверку контрольной суммы' : '';
  const ogrnError = requisites.ogrn && !isValidOgrn(requisites.ogrn) ? 'ОГРН не прошёл проверку контрольной суммы' : '';
  const canSubmit =
    Boolean(requisites.name.trim()) &&
    Boolean(requisites.code.trim()) &&
    isValidInn(requisites.inn) &&
    isValidOgrn(requisites.ogrn) &&
    (!isManagementCompany || Boolean(requisites.licenseNumber.trim())) &&
    isStaffAccountComplete(employee) &&
    !alreadyRegistered &&
    (!house || !attachHouse || Boolean(basis.trim()));

  function update<K extends keyof RequisitesState>(key: K, value: RequisitesState[K]) {
    setTouched(true);
    setRequisites((current) => ({ ...current, [key]: value }));
  }

  function changeHouse(next: House | null) {
    setHouse(next);
    setApplied(null);
    // Taking a house from another platform organization is a deliberate step, not a default.
    setAttachHouse(Boolean(next) && !next?.managed_by_organization_id);
  }

  function applyPrefill(prefill: RequisitesPrefill, key: string, candidate: HouseManagingOrganization) {
    setApplied({ key, candidate });
    setRequisites((current) => ({
      ...current,
      ...prefill,
      // A registry never publishes the license - keep what the admin typed.
      licenseNumber: prefill.type === 'HOA' ? '' : current.licenseNumber,
      inReserveRegistry: prefill.type === 'HOA' ? false : current.inReserveRegistry,
    }));
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
      {
        onSuccess: (result) => {
          if (!house || !attachHouse) {
            onRegistered(result.organization_id, result);
            return;
          }
          assign.mutate(
            { house_id: house.house_id, organization_id: result.organization_id, basis: basis.trim() },
            {
              onSuccess: () => onRegistered(result.organization_id, result),
              // The organization exists either way - say what's missing, don't lose it.
              onError: () => setRegistered(result),
            },
          );
        },
      },
    );
  }

  if (registered) {
    return (
      <div className="register-organization">
        <div className="form-error">
          Организация зарегистрирована, но дом не удалось привязать: {apiErrorMessage(assign.error)}. Привяжите его
          на странице «Дома».
        </div>
        <div className="form-actions">
          <button type="button" className="btn" onClick={() => onRegistered(registered.organization_id, registered)}>
            Перейти к организации
          </button>
        </div>
      </div>
    );
  }

  return (
    <form className="register-organization" onSubmit={handleSubmit}>
      <div className="form-section-title">Дом, который обслуживает организация</div>
      <div className="form-hint">
        Необязательно, но экономит время: по адресу подтянем название, ИНН/ОГРН и контакты из открытых источников.
      </div>
      <HouseManagerLookup
        house={house}
        onHouseChange={changeHouse}
        appliedKey={applied?.key ?? null}
        autoApply={!touched}
        onApply={applyPrefill}
        onInfo={setHouseInfo}
      />
      {platformManager && (
        <div className="form-error">
          Дом уже обслуживает на платформе {platformManager.name}.{' '}
          <Link to={ROUTES.organization(platformManager.organization_id)}>Открыть карточку</Link>
        </div>
      )}
      {house && (
        <div className="form-grid">
          <label className="checkbox-field form-grid__wide">
            <input type="checkbox" checked={attachHouse} onChange={(event) => setAttachHouse(event.target.checked)} />
            {platformManager
              ? 'Передать дом новой организации (прежнее управление на платформе завершится)'
              : 'Сразу привязать дом к организации — сотрудник увидит его жителей и заявки'}
          </label>
          {attachHouse && (
            <div className="form-grid__wide">
              <label className="field-label" htmlFor="org-house-basis">
                Основание управления
              </label>
              <input
                id="org-house-basis"
                className="field"
                value={basis}
                onChange={(event) => setBasis(event.target.value)}
              />
            </div>
          )}
        </div>
      )}

      <div className="form-section-title">Организация</div>
      {alreadyRegistered && (
        <div className="form-error">
          {alreadyRegistered.name} с такими ИНН/ОГРН уже зарегистрирована.{' '}
          <Link to={ROUTES.organization(alreadyRegistered.id)}>Открыть карточку</Link> — там можно добавить
          сотрудников.
        </div>
      )}
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
          {!innError && applied && !applied.candidate.inn && !requisites.inn && (
            <div className="form-hint">В открытых источниках ИНН не найден — укажите вручную</div>
          )}
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
      {applied?.candidate.email && !employee.email && (
        <div className="form-hint">
          Контактный e-mail организации из открытых источников: {applied.candidate.email}
        </div>
      )}

      {register.isError && <div className="form-error">{apiErrorMessage(register.error)}</div>}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!canSubmit || register.isPending || assign.isPending}>
          {register.isPending || assign.isPending ? 'Регистрируем…' : 'Зарегистрировать'}
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={onCancel}
          disabled={register.isPending || assign.isPending}
        >
          Отмена
        </button>
      </div>
    </form>
  );
}
