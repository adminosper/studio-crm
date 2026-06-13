from __future__ import annotations

"""Mock PostHog event catalog for the lead-scoring prototype.

In real PostHog setups, product usage is often tracked through more generic
events such as button clicks, page views, or CTA interactions. Converting that
raw stream into reviewer-friendly business events like `demo_requested` or
`pricing_page_viewed` may require additional processing on event names and
properties. That derivation step is intentionally ignored in this prototype,
so this module exposes a small pre-derived allowlist directly.
"""

MOCK_POSTHOG_EVENT_NAMES = (
    "pricing_page_viewed",
    "demo_requested",
    "case_study_downloaded",
    "contact_sales_clicked",
    "product_tour_started",
)


def list_mock_posthog_event_names() -> tuple[str, ...]:
    """Return the mocked PostHog event names supported by the V1 rule contract."""
    return MOCK_POSTHOG_EVENT_NAMES
