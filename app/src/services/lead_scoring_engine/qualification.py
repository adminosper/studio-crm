from __future__ import annotations


class LeadQualificationService:
    """Map a computed score to one qualification stage."""

    def derive_stage(
        self,
        *,
        score: int,
        mql_score_threshold: int,
        sql_score_threshold: int,
    ) -> str:
        """Return the qualification stage implied by one final normalized score."""
        if score >= sql_score_threshold:
            return "sql"
        if score >= mql_score_threshold:
            return "mql"
        return "pre_mql"
