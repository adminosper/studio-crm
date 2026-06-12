from __future__ import annotations


class TenantNotFoundError(Exception):
    """Raised when a tenant-scoped operation references a missing tenant."""


class LeadNotFoundError(Exception):
    """Raised when a tenant-scoped lead cannot be found."""


class ScoringRuleNotFoundError(Exception):
    """Raised when a tenant-scoped scoring rule cannot be found."""
