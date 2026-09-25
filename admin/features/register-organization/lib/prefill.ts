// Pure helpers turning what the platform already knows about a house (its management
// company from open sources, see GET /geo/houses/{id}/info) into registration form values.
// Kept free of `@/` imports so they can be unit-tested with plain node.

export type HousingType = 'MANAGEMENT_COMPANY' | 'HOA';

export interface ManagerCandidate {
  name: string;
  inn: string | null;
  ogrn: string | null;
}

export interface RequisitesPrefill {
  name: string;
  type: HousingType;
  inn: string;
  ogrn: string;
  city: string;
  code: string;
}

const LEGAL_FORMS: Array<[RegExp, string]> = [
  [/^ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ\s*/i, 'ООО'],
  [/^ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО\s*/i, 'ПАО'],
  [/^АКЦИОНЕРНОЕ ОБЩЕСТВО\s*/i, 'АО'],
  [/^ТОВАРИЩЕСТВО СОБСТВЕННИКОВ ЖИЛЬЯ\s*/i, 'ТСЖ'],
  [/^ТОВАРИЩЕСТВО СОБСТВЕННИКОВ НЕДВИЖИМОСТИ\s*/i, 'ТСН'],
  [/^ЖИЛИЩНО-СТРОИТЕЛЬНЫЙ КООПЕРАТИВ\s*/i, 'ЖСК'],
  [/^МУНИЦИПАЛЬНОЕ УНИТАРНОЕ ПРЕДПРИЯТИЕ\s*/i, 'МУП'],
  [/^(ООО|ПАО|АО|ЗАО|ОАО|ТСЖ|ТСН|ЖСК|МУП)\s+/i, ''],
];

/** «ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ДОМ-ПЛЮС"» -> «ООО «ДОМ-ПЛЮС»». Registry
 * names often carry unbalanced nested quotes, so all quotes are dropped and the rest is
 * wrapped once. */
export function shortOrganizationName(name: string): string {
  const trimmed = name.trim().replace(/\s+/g, ' ');
  for (const [pattern, short] of LEGAL_FORMS) {
    const match = pattern.exec(trimmed);
    if (!match) continue;
    const form = short || match[1].toUpperCase();
    const rest = trimmed.slice(match[0].length).replace(/["«»“”„']/g, '').trim();
    return rest ? `${form} «${rest}»` : trimmed;
  }
  return trimmed;
}

export function isHoa(name: string, managementMethod: string | null): boolean {
  return managementMethod === 'ТСЖ' || /^(ТСЖ|ТОВАРИЩЕСТВО СОБСТВЕННИКОВ)/i.test(name.trim());
}

export function prefillFromManager(
  candidate: ManagerCandidate,
  context: { city: string | null; managementMethod: string | null },
): RequisitesPrefill {
  const type: HousingType = isHoa(candidate.name, context.managementMethod) ? 'HOA' : 'MANAGEMENT_COMPANY';
  const id = candidate.ogrn ?? candidate.inn ?? '';
  return {
    name: shortOrganizationName(candidate.name),
    type,
    inn: candidate.inn ?? '',
    ogrn: candidate.ogrn ?? '',
    city: context.city ?? '',
    code: id ? `${type === 'HOA' ? 'tszh' : 'uk'}-${id}` : '',
  };
}

/** An organization already registered on the platform with the same INN or OGRN. */
export function findRegistered<T extends { inn: string | null; ogrn: string | null }>(
  organizations: T[],
  requisites: { inn: string; ogrn: string },
): T | undefined {
  return organizations.find(
    (organization) =>
      (requisites.inn && organization.inn === requisites.inn) ||
      (requisites.ogrn && organization.ogrn === requisites.ogrn),
  );
}
