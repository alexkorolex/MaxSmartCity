"""Requisites checks for housing organizations registering themselves (Постановление
№1616): a management company is a licensed legal entity, an HOA (ТСЖ) is resident
self-management with no license - and only a licensed management company can be on the
government's Перечень of fallback managers."""

from src.domains.identity.enums import OrganizationType

HOUSING_ORGANIZATION_TYPES = frozenset({OrganizationType.MANAGEMENT_COMPANY, OrganizationType.HOA})

_INN10_WEIGHTS = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_FIRST_WEIGHTS = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_SECOND_WEIGHTS = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


class OrganizationRequisitesError(ValueError):
    pass


def _checksum(digits: str, weights: tuple[int, ...]) -> int:
    return sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=False)) % 11 % 10


def is_valid_inn(inn: str) -> bool:
    """10 digits for a legal entity, 12 for a sole proprietor - both with FNS check digits."""
    if not inn.isdigit():
        return False
    if len(inn) == 10:
        return _checksum(inn, _INN10_WEIGHTS) == int(inn[9])
    if len(inn) == 12:
        return _checksum(inn, _INN12_FIRST_WEIGHTS) == int(inn[10]) and _checksum(
            inn, _INN12_SECOND_WEIGHTS
        ) == int(inn[11])
    return False


def is_valid_ogrn(ogrn: str) -> bool:
    """13 digits (ОГРН, mod 11) or 15 digits (ОГРНИП, mod 13); the last digit is the check."""
    if not ogrn.isdigit() or len(ogrn) not in (13, 15):
        return False
    body, check = int(ogrn[:-1]), int(ogrn[-1])
    divisor = 11 if len(ogrn) == 13 else 13
    return body % divisor % 10 == check


def validate_housing_requisites(
    *,
    organization_type: OrganizationType,
    inn: str,
    ogrn: str,
    license_number: str | None,
    in_reserve_registry: bool,
) -> None:
    if organization_type not in HOUSING_ORGANIZATION_TYPES:
        raise OrganizationRequisitesError(
            "Only a management company (MANAGEMENT_COMPANY) or an HOA (HOA) can self-register"
        )
    if not is_valid_inn(inn):
        raise OrganizationRequisitesError("INN is invalid")
    if not is_valid_ogrn(ogrn):
        raise OrganizationRequisitesError("OGRN is invalid")
    if organization_type is OrganizationType.MANAGEMENT_COMPANY:
        if not license_number or not license_number.strip():
            raise OrganizationRequisitesError(
                "A management company must provide its license to manage apartment buildings"
            )
    else:
        if license_number:
            raise OrganizationRequisitesError("An HOA is not a licensed entity; license_number must be empty")
        if in_reserve_registry:
            raise OrganizationRequisitesError(
                "Only a licensed management company can be included in the Перечень"
            )
