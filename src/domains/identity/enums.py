from enum import StrEnum


class BotStatus(StrEnum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"


class OrganizationType(StrEnum):
    ADMINISTRATION = "ADMINISTRATION"
    POWER_GRID = "POWER_GRID"
    WATER_UTILITY = "WATER_UTILITY"
    EMERGENCY = "EMERGENCY"
