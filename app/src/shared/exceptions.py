from __future__ import annotations


class TenantNotFoundError(Exception):
    """Raised when a tenant-scoped operation references a missing tenant."""


class LeadNotFoundError(Exception):
    """Raised when a tenant-scoped lead cannot be found."""


class ScoringRuleNotFoundError(Exception):
    """Raised when a tenant-scoped scoring rule cannot be found."""


class RuleConfigValidationError(Exception):
    """Raised when a rule config fails semantic validation."""

    def __init__(
        self,
        *,
        message: str,
        field_path: str,
        allowed_values: list[object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field_path = field_path
        self.allowed_values = allowed_values
