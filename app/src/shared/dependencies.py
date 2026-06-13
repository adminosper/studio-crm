from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from psycopg import Connection

from src.database.connection import get_db_connection
from src.repositories.lead_event_repository import LeadEventRepository
from src.repositories.lead_repository import LeadRepository
from src.repositories.lead_scoring_rule_repository import LeadScoringRuleRepository
from src.repositories.tenant_repository import TenantRepository
from src.services.lead_scoring_rules.contracts.service import ScoringRuleContractService
from src.services.lead_scoring_rules.service import LeadScoringRuleService
from src.services.lead_scoring_rules.validations.behavior import BehaviorScoringRuleValidator
from src.services.lead_scoring_rules.validations.fit import FitScoringRuleValidator
from src.services.lead_scoring_rules.validations.service import LeadScoringRuleValidationService
from src.services.lead_service import LeadService
from src.services.tenant_service import TenantService


def get_tenant_repository(connection: Annotated[Connection, Depends(get_db_connection)]) -> TenantRepository:
    """Build the tenant repository for the current request connection."""
    return TenantRepository(connection)


def get_lead_repository(connection: Annotated[Connection, Depends(get_db_connection)]) -> LeadRepository:
    """Build the lead repository for the current request connection."""
    return LeadRepository(connection)


def get_lead_scoring_rule_repository(
    connection: Annotated[Connection, Depends(get_db_connection)],
) -> LeadScoringRuleRepository:
    """Build the scoring rule repository for the current request connection."""
    return LeadScoringRuleRepository(connection)


def get_lead_event_repository(
    connection: Annotated[Connection, Depends(get_db_connection)],
) -> LeadEventRepository:
    """Build the lead event repository for the current request connection."""
    return LeadEventRepository(connection)


def get_fit_scoring_rule_validator() -> FitScoringRuleValidator:
    """Build the fit-rule validator."""
    return FitScoringRuleValidator()


def get_behavior_scoring_rule_validator() -> BehaviorScoringRuleValidator:
    """Build the behavior-rule validator."""
    return BehaviorScoringRuleValidator()


def get_lead_scoring_rule_validation_service(
    fit_validator: Annotated[FitScoringRuleValidator, Depends(get_fit_scoring_rule_validator)],
    behavior_validator: Annotated[BehaviorScoringRuleValidator, Depends(get_behavior_scoring_rule_validator)],
) -> LeadScoringRuleValidationService:
    """Build the scoring-rule validation service."""
    return LeadScoringRuleValidationService(
        fit_validator=fit_validator,
        behavior_validator=behavior_validator,
    )


def get_scoring_rule_contract_service() -> ScoringRuleContractService:
    """Build the contract discovery service for scoring rules."""
    return ScoringRuleContractService()


def get_tenant_service(
    tenant_repository: Annotated[TenantRepository, Depends(get_tenant_repository)],
) -> TenantService:
    """Build the tenant service with its repository dependencies."""
    return TenantService(tenant_repository=tenant_repository)


def get_lead_service(
    tenant_repository: Annotated[TenantRepository, Depends(get_tenant_repository)],
    lead_repository: Annotated[LeadRepository, Depends(get_lead_repository)],
) -> LeadService:
    """Build the lead service with its repository dependencies."""
    return LeadService(
        tenant_repository=tenant_repository,
        lead_repository=lead_repository,
    )


def get_lead_scoring_rule_service(
    tenant_repository: Annotated[TenantRepository, Depends(get_tenant_repository)],
    lead_scoring_rule_repository: Annotated[
        LeadScoringRuleRepository,
        Depends(get_lead_scoring_rule_repository),
    ],
    validation_service: Annotated[
        LeadScoringRuleValidationService,
        Depends(get_lead_scoring_rule_validation_service),
    ],
) -> LeadScoringRuleService:
    """Build the scoring rule service with its repository dependencies."""
    return LeadScoringRuleService(
        tenant_repository=tenant_repository,
        lead_scoring_rule_repository=lead_scoring_rule_repository,
        validation_service=validation_service,
    )
