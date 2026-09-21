from enum import StrEnum


class ActorType(StrEnum):
    RESIDENT = "RESIDENT"
    OPERATOR = "OPERATOR"
    SERVICE = "SERVICE"
    SYSTEM = "SYSTEM"


class Priority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
