from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from psycopg import Connection

from src.models.scoring_compute import ScoringComputeLeadResultResponse
from src.models.scoring_compute import ScoringComputeResponse
from src.integrations.posthog.service import PosthogService
from src.repositories.lead_repository import LeadRepository
from src.repositories.lead_scoring_rule_repository import LeadScoringRuleRepository
from src.repositories.tenant_repository import TenantRepository
from src.shared.exceptions import TenantNotFoundError
from src.services.lead_scoring_engine.behavior_scorer import LeadBehaviorScorer
from src.services.lead_scoring_engine.fit_scorer import LeadFitScorer
from src.services.lead_scoring_engine.qualification import LeadQualificationService
from src.services.lead_scoring_engine.types import LeadScoringComputationResult
from src.services.lead_scoring_rules.validations.service import LeadScoringRuleValidationService


class LeadScoringComputeService:
    """Compute and persist tenant lead scores and stages in one transaction."""

    def __init__(
        self,
        connection: Connection,
        tenant_repository: TenantRepository,
        lead_repository: LeadRepository,
        lead_scoring_rule_repository: LeadScoringRuleRepository,
        validation_service: LeadScoringRuleValidationService,
        posthog_service: PosthogService,
        fit_scorer: LeadFitScorer,
        behavior_scorer: LeadBehaviorScorer,
        qualification_service: LeadQualificationService,
    ) -> None:
        self._connection = connection
        self._tenant_repository = tenant_repository
        self._lead_repository = lead_repository
        self._lead_scoring_rule_repository = lead_scoring_rule_repository
        self._validation_service = validation_service
        self._posthog_service = posthog_service
        self._fit_scorer = fit_scorer
        self._behavior_scorer = behavior_scorer
        self._qualification_service = qualification_service

    def compute_tenant_scores(self, tenant_id: UUID) -> ScoringComputeResponse:
        """Compute and persist scoring results for every lead belonging to one tenant."""
        computed_at = datetime.now(UTC)

        with self._connection.transaction():
            tenant = self._tenant_repository.fetch_by_id(tenant_id)
            if tenant is None:
                raise TenantNotFoundError

            leads = self._lead_repository.fetch_by_tenant_id(tenant_id)
            scoring_rules = self._load_normalized_active_rules(tenant_id)
            fit_rules = [rule for rule in scoring_rules if rule["rule_type"] == "fit"]
            behavior_rules = [rule for rule in scoring_rules if rule["rule_type"] == "behavior"]
            max_possible_score = self._compute_max_possible_score(scoring_rules)
            lead_events_by_lead_id = self._posthog_service.load_tenant_events_grouped_by_lead(
                tenant_id=tenant_id,
                lookback_days=self._resolve_outer_behavior_lookback_days(behavior_rules),
                as_of=computed_at,
            )

            results: list[LeadScoringComputationResult] = []
            processed_lead_count = 0
            skipped_lead_count = 0
            stage_transition_count = 0

            for lead in leads:
                result = self._compute_one_lead(
                    lead=lead,
                    tenant=tenant,
                    fit_rules=fit_rules,
                    behavior_rules=behavior_rules,
                    lead_events_by_lead_id=lead_events_by_lead_id,
                    max_possible_score=max_possible_score,
                    computed_at=computed_at,
                )
                results.append(result)

                if result.is_skipped:
                    skipped_lead_count += 1
                    continue

                processed_lead_count += 1
                if result.previous_stage != result.new_stage:
                    stage_transition_count += 1

                self._lead_repository.update_scoring_state(
                    tenant_id=tenant_id,
                    lead_id=result.lead_id,
                    score=result.final_score,
                    stage=result.new_stage,
                    score_last_updated_at=computed_at,
                )

        return ScoringComputeResponse(
            tenant_id=tenant_id,
            processed_lead_count=processed_lead_count,
            skipped_lead_count=skipped_lead_count,
            stage_transition_count=stage_transition_count,
            max_possible_score=max_possible_score,
            results=[
                ScoringComputeLeadResultResponse(
                    lead_id=result.lead_id,
                    status=result.status,
                    previous_score=result.previous_score,
                    raw_score=result.raw_score,
                    final_score=result.final_score,
                    previous_stage=result.previous_stage,
                    new_stage=result.new_stage,
                    is_stage_manually_overridden=result.is_stage_manually_overridden,
                    matched_rule_names=list(result.matched_rule_names),
                )
                for result in results
            ],
        )

    def _load_normalized_active_rules(self, tenant_id: UUID) -> list[dict]:
        normalized_rules: list[dict] = []
        for rule in self._lead_scoring_rule_repository.fetch_active_by_tenant_id(tenant_id):
            normalized_rule = dict(rule)
            normalized_rule["rule_config"] = self._validation_service.normalize_persisted_rule_config(
                rule_type=normalized_rule["rule_type"],
                rule_config=normalized_rule["rule_config"],
            )
            normalized_rules.append(normalized_rule)
        return normalized_rules

    def _resolve_outer_behavior_lookback_days(self, behavior_rules: list[dict]) -> int:
        if not behavior_rules:
            return 0
        return max(rule["rule_config"]["lookback_days"] for rule in behavior_rules)

    def _compute_max_possible_score(self, rules: list[dict]) -> int:
        return sum(max(rule["score_delta"], 0) for rule in rules)

    def _compute_one_lead(
        self,
        *,
        lead: dict,
        tenant: dict,
        fit_rules: list[dict],
        behavior_rules: list[dict],
        lead_events_by_lead_id: dict,
        max_possible_score: int,
        computed_at: datetime,
    ) -> LeadScoringComputationResult:
        if lead["status"] != "active":
            return LeadScoringComputationResult(
                lead_id=lead["id"],
                status=lead["status"],
                previous_score=lead["score"],
                raw_score=lead["score"],
                final_score=lead["score"],
                previous_stage=lead["stage"],
                new_stage=lead["stage"],
                is_stage_manually_overridden=lead["is_stage_manually_overridden"],
                is_skipped=True,
                matched_rule_names=(),
            )

        fit_breakdown = self._fit_scorer.score_lead(lead=lead, rules=fit_rules)
        behavior_breakdown = self._behavior_scorer.score_lead(
            events=lead_events_by_lead_id.get(lead["id"], []),
            rules=behavior_rules,
            as_of=computed_at,
        )

        raw_score = fit_breakdown.score_delta + behavior_breakdown.score_delta
        final_score = self._normalize_score(raw_score=raw_score, max_possible_score=max_possible_score)
        new_stage = lead["stage"]
        if not lead["is_stage_manually_overridden"]:
            new_stage = self._qualification_service.derive_stage(
                score=final_score,
                mql_score_threshold=tenant["mql_score_threshold"],
                sql_score_threshold=tenant["sql_score_threshold"],
            )

        matched_rule_names = tuple(
            matched_rule.rule_name
            for matched_rule in fit_breakdown.matched_rules + behavior_breakdown.matched_rules
        )

        return LeadScoringComputationResult(
            lead_id=lead["id"],
            status=lead["status"],
            previous_score=lead["score"],
            raw_score=raw_score,
            final_score=final_score,
            previous_stage=lead["stage"],
            new_stage=new_stage,
            is_stage_manually_overridden=lead["is_stage_manually_overridden"],
            is_skipped=False,
            matched_rule_names=matched_rule_names,
        )

    def _normalize_score(self, *, raw_score: int, max_possible_score: int) -> int:
        if max_possible_score > 100 and max_possible_score > 0:
            normalized_score = round((raw_score / max_possible_score) * 100)
            return max(0, min(100, normalized_score))
        return max(0, min(100, raw_score))
