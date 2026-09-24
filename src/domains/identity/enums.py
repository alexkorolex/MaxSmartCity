from enum import StrEnum


class BotStatus(StrEnum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"


class OrganizationType(StrEnum):
    ADMINISTRATION = "ADMINISTRATION"
    POWER_GRID = "POWER_GRID"
    WATER_UTILITY = "WATER_UTILITY"
    EMERGENCY = "EMERGENCY"
    MANAGEMENT_COMPANY = "MANAGEMENT_COMPANY"
    """Управляющая компания - a licensed commercial entity managing apartment buildings
    (Постановление №1616)."""
    HOA = "HOA"
    """ТСЖ (товарищество собственников жилья) - resident self-management, not a licensed
    commercial entity; ``Organization.license_number`` does not apply to this type."""


class OrganizationRegistrationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
