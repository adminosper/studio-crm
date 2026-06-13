from __future__ import annotations

from fastapi import HTTPException, status

from src.shared.exceptions import LeadNotFoundError
from src.shared.exceptions import RuleConfigValidationError
from src.shared.exceptions import ScoringRuleNotFoundError
from src.shared.exceptions import TenantNotFoundError


def raise_http_exception_for_service_error(error: Exception) -> None:
    """Translate domain exceptions into HTTP exceptions."""
    if isinstance(error, TenantNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found") from error
    if isinstance(error, LeadNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found") from error
    if isinstance(error, ScoringRuleNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scoring rule not found") from error
    if isinstance(error, RuleConfigValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "rule_config_validation_error",
                "field_path": error.field_path,
                "message": error.message,
                "allowed_values": error.allowed_values,
            },
        ) from error
    raise error
