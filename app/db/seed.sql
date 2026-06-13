INSERT INTO tenants (name, mql_score_threshold, sql_score_threshold)
VALUES
    ('Acme SaaS', 40, 70),
    ('Beta Fintech', 50, 80)
ON CONFLICT (name) DO UPDATE
SET
    mql_score_threshold = EXCLUDED.mql_score_threshold,
    sql_score_threshold = EXCLUDED.sql_score_threshold;

INSERT INTO leads (
    tenant_id,
    name,
    email,
    company,
    industry,
    company_size,
    geography,
    phone,
    title,
    source,
    status,
    stage,
    score,
    score_last_updated_at,
    is_stage_manually_overridden
)
SELECT
    tenants.id,
    seeded_leads.name,
    seeded_leads.email,
    seeded_leads.company,
    seeded_leads.industry,
    seeded_leads.company_size,
    seeded_leads.geography,
    seeded_leads.phone,
    seeded_leads.title,
    seeded_leads.source,
    seeded_leads.status,
    seeded_leads.stage,
    seeded_leads.score,
    seeded_leads.score_last_updated_at,
    seeded_leads.is_stage_manually_overridden
FROM (
    VALUES
        ('Acme SaaS', 'Alice Carter', 'alice@northwind.ai', 'Northwind', 'SaaS', 320, 'US', '+1-555-0101', 'Founder', 'manual', 'active', 'pre_mql', 0, NULL::timestamptz, FALSE),
        ('Acme SaaS', 'Ben Stone', 'ben@clearbitlabs.ai', 'Clearbit Labs', 'SaaS', 90, 'US', '+1-555-0102', 'Growth Lead', 'website', 'active', 'mql', 55, NOW(), FALSE),
        ('Acme SaaS', 'Cara Mills', 'cara@quietops.ai', 'QuietOps', 'SaaS', 35, 'UK', '+44-20-7000-0103', 'Operations Manager', 'linkedin', 'disqualified', 'pre_mql', 10, NOW(), FALSE),
        ('Acme SaaS', 'Derek Hall', 'derek@scaleforge.ai', 'ScaleForge', 'FinTech', 500, 'US', '+1-555-0104', 'Founder', 'website', 'active', 'sql', 88, NOW(), TRUE),
        ('Beta Fintech', 'Eva Long', 'eva@ledgerloop.io', 'LedgerLoop', 'FinTech', 240, 'US', '+1-555-0201', 'Founder', 'manual', 'active', 'pre_mql', 0, NULL::timestamptz, FALSE),
        ('Beta Fintech', 'Farah Noor', 'farah@riskgrid.io', 'RiskGrid', 'Cybersecurity', 150, 'UAE', '+971-4-555-0202', 'VP Sales', 'website', 'active', 'pre_mql', 20, NOW(), FALSE),
        ('Beta Fintech', 'Gabe Ross', 'gabe@capitalmesh.io', 'CapitalMesh', 'FinTech', 800, 'US', '+1-555-0203', 'CEO', 'website', 'active', 'mql', 60, NOW(), FALSE),
        ('Beta Fintech', 'Hana Kim', 'hana@mintlayer.io', 'MintLayer', 'FinTech', 50, 'Singapore', '+65-6555-0204', 'Product Manager', 'linkedin', 'converted', 'sql', 95, NOW(), FALSE)
) AS seeded_leads (
    tenant_name,
    name,
    email,
    company,
    industry,
    company_size,
    geography,
    phone,
    title,
    source,
    status,
    stage,
    score,
    score_last_updated_at,
    is_stage_manually_overridden
)
JOIN tenants ON tenants.name = seeded_leads.tenant_name
ON CONFLICT (tenant_id, email) DO UPDATE
SET
    name = EXCLUDED.name,
    company = EXCLUDED.company,
    industry = EXCLUDED.industry,
    company_size = EXCLUDED.company_size,
    geography = EXCLUDED.geography,
    phone = EXCLUDED.phone,
    title = EXCLUDED.title,
    source = EXCLUDED.source,
    status = EXCLUDED.status,
    stage = EXCLUDED.stage,
    score = EXCLUDED.score,
    score_last_updated_at = EXCLUDED.score_last_updated_at,
    is_stage_manually_overridden = EXCLUDED.is_stage_manually_overridden,
    updated_at = NOW();

INSERT INTO lead_scoring_rules (
    tenant_id,
    rule_name,
    rule_type,
    score_delta,
    is_active,
    rule_config
)
SELECT
    tenants.id,
    seeded_rules.rule_name,
    seeded_rules.rule_type,
    seeded_rules.score_delta,
    seeded_rules.is_active,
    seeded_rules.rule_config::jsonb
FROM (
    VALUES
        ('Acme SaaS', 'SaaS ICP', 'fit', 20, TRUE, '{"version":1,"field":"industry","operator":"in","value":["SaaS","FinTech"]}'),
        ('Acme SaaS', 'Mid Market Company Size', 'fit', 15, TRUE, '{"version":1,"field":"company_size","operator":"gte","value":200}'),
        ('Acme SaaS', 'Pricing Page Intent', 'behavior', 20, TRUE, '{"version":1,"event_name":"pricing_page_viewed","aggregate_operator":"count_gte","value":2,"lookback_days":30,"property_filters":{}}'),
        ('Acme SaaS', 'Demo Request Intent', 'behavior', 30, TRUE, '{"version":1,"event_name":"demo_requested","aggregate_operator":"count_gte","value":1,"lookback_days":30,"property_filters":{}}'),
        ('Beta Fintech', 'Fintech ICP', 'fit', 25, TRUE, '{"version":1,"field":"industry","operator":"equals","value":"FinTech"}'),
        ('Beta Fintech', 'Founder Persona', 'fit', 10, TRUE, '{"version":1,"field":"title","operator":"contains","value":"Founder"}'),
        ('Beta Fintech', 'Pricing Page Intent', 'behavior', 15, TRUE, '{"version":1,"event_name":"pricing_page_viewed","aggregate_operator":"count_gte","value":3,"lookback_days":30,"property_filters":{}}'),
        ('Beta Fintech', 'Case Study Download Intent', 'behavior', 25, TRUE, '{"version":1,"event_name":"case_study_downloaded","aggregate_operator":"count_gte","value":1,"lookback_days":14,"property_filters":{}}')
) AS seeded_rules (
    tenant_name,
    rule_name,
    rule_type,
    score_delta,
    is_active,
    rule_config
)
JOIN tenants ON tenants.name = seeded_rules.tenant_name
WHERE NOT EXISTS (
    SELECT 1
    FROM lead_scoring_rules existing_rules
    WHERE existing_rules.tenant_id = tenants.id
      AND existing_rules.rule_name = seeded_rules.rule_name
);

INSERT INTO lead_events (
    tenant_id,
    lead_id,
    event_name,
    event_properties,
    occurred_at
)
SELECT
    tenants.id,
    leads.id,
    seeded_events.event_name,
    seeded_events.event_properties::jsonb,
    seeded_events.occurred_at
FROM (
    VALUES
        ('Acme SaaS', 'alice@northwind.ai', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '10 days'),
        ('Acme SaaS', 'alice@northwind.ai', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '2 days'),
        ('Acme SaaS', 'ben@clearbitlabs.ai', 'demo_requested', '{"channel":"website"}', NOW() - INTERVAL '3 days'),
        ('Acme SaaS', 'derek@scaleforge.ai', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '7 days'),
        ('Acme SaaS', 'derek@scaleforge.ai', 'demo_requested', '{"channel":"website"}', NOW() - INTERVAL '1 day'),
        ('Beta Fintech', 'eva@ledgerloop.io', 'case_study_downloaded', '{"asset":"fraud-detection"}', NOW() - INTERVAL '5 days'),
        ('Beta Fintech', 'gabe@capitalmesh.io', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '8 days'),
        ('Beta Fintech', 'gabe@capitalmesh.io', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '4 days'),
        ('Beta Fintech', 'gabe@capitalmesh.io', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '1 day')
) AS seeded_events (
    tenant_name,
    lead_email,
    event_name,
    event_properties,
    occurred_at
)
JOIN tenants ON tenants.name = seeded_events.tenant_name
JOIN leads ON leads.tenant_id = tenants.id AND leads.email = seeded_events.lead_email
WHERE NOT EXISTS (
    SELECT 1
    FROM lead_events existing_events
    WHERE existing_events.tenant_id = tenants.id
      AND existing_events.lead_id = leads.id
      AND existing_events.event_name = seeded_events.event_name
      AND existing_events.occurred_at = seeded_events.occurred_at
);
