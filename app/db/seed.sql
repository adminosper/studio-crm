-- Seed file with static UUIDs to guarantee repeatable documentation walkthrough tests
INSERT INTO tenants (id, name, mql_score_threshold, sql_score_threshold)
VALUES
    ('37e8d336-9d56-49e0-a918-6e555295cee9', 'Acme SaaS', 40, 70),
    ('6248d652-45f2-47af-a3d8-6565ae026387', 'Beta Fintech', 50, 80)
ON CONFLICT (name) DO UPDATE
SET
    id = EXCLUDED.id,
    mql_score_threshold = EXCLUDED.mql_score_threshold,
    sql_score_threshold = EXCLUDED.sql_score_threshold;

INSERT INTO leads (
    id,
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
VALUES
    -- Acme SaaS Leads
    ('4b49bb63-b93f-4381-be55-5e1bfb0b1cf7', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Alice Carter', 'alice@northwind.ai', 'Northwind', 'SaaS', 320, 'US', '+1-555-0101', 'Founder', 'manual', 'active', 'pre_mql', 0, NULL, FALSE),
    ('611952d8-385c-459b-ba20-cac3523dd991', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Ben Stone', 'ben@clearbitlabs.ai', 'Clearbit Labs', 'SaaS', 90, 'US', '+1-555-0102', 'Growth Lead', 'website', 'active', 'mql', 55, NOW(), FALSE),
    ('63d41dc5-8b71-4eae-b56c-168bcbfb322b', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Cara Mills', 'cara@quietops.ai', 'QuietOps', 'SaaS', 35, 'UK', '+44-20-7000-0103', 'Operations Manager', 'linkedin', 'disqualified', 'pre_mql', 10, NOW(), FALSE),
    ('53703ed8-dc7c-478c-b639-579885fb8200', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Derek Hall', 'derek@scaleforge.ai', 'ScaleForge', 'FinTech', 500, 'US', '+1-555-0104', 'Founder', 'website', 'active', 'sql', 88, NOW(), TRUE),
    
    -- Beta Fintech Leads
    ('ff6440f3-1b95-486d-ab64-4e13571bef59', '6248d652-45f2-47af-a3d8-6565ae026387', 'Eva Long', 'eva@ledgerloop.io', 'LedgerLoop', 'FinTech', 240, 'US', '+1-555-0201', 'Founder', 'manual', 'active', 'pre_mql', 0, NULL, FALSE),
    ('7c156217-6468-478a-9e36-f542ec8831fe', '6248d652-45f2-47af-a3d8-6565ae026387', 'Farah Noor', 'farah@riskgrid.io', 'RiskGrid', 'Cybersecurity', 150, 'UAE', '+971-4-555-0202', 'VP Sales', 'website', 'active', 'pre_mql', 20, NOW(), FALSE),
    ('c413cc88-9032-48c3-b955-21070eab7bbc', '6248d652-45f2-47af-a3d8-6565ae026387', 'Gabe Ross', 'gabe@capitalmesh.io', 'CapitalMesh', 'FinTech', 800, 'US', '+1-555-0203', 'CEO', 'website', 'active', 'mql', 60, NOW(), FALSE),
    ('a741615c-321f-4c50-a5ff-02232855b475', '6248d652-45f2-47af-a3d8-6565ae026387', 'Hana Kim', 'hana@mintlayer.io', 'MintLayer', 'FinTech', 50, 'Singapore', '+65-6555-0204', 'Product Manager', 'linkedin', 'converted', 'sql', 95, NOW(), FALSE)
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
    id,
    tenant_id,
    rule_name,
    rule_type,
    score_delta,
    is_active,
    rule_config
)
VALUES
    -- Acme SaaS Rules
    ('eb47e258-86db-4c4f-8f7d-f09430a59802', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Demo Request Intent', 'behavior', 30, TRUE, '{"value": 1, "version": 1, "event_name": "demo_requested", "lookback_days": 30, "property_filters": {}, "aggregate_operator": "count_gte"}'),
    ('ac9cb6b4-a84f-40d4-8e24-99860ce07e4a', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Pricing Page Intent', 'behavior', 20, TRUE, '{"value": 2, "version": 1, "event_name": "pricing_page_viewed", "lookback_days": 30, "property_filters": {}, "aggregate_operator": "count_gte"}'),
    ('58fc66a2-0687-4104-8dc1-0a6c3f27c310', '37e8d336-9d56-49e0-a918-6e555295cee9', 'Mid Market Company Size', 'fit', 15, TRUE, '{"field": "company_size", "value": 200, "version": 1, "operator": "gte"}'),
    ('44dc73ae-290b-4440-92be-a68d687353d4', '37e8d336-9d56-49e0-a918-6e555295cee9', 'SaaS ICP', 'fit', 20, TRUE, '{"field": "industry", "value": ["SaaS", "FinTech"], "version": 1, "operator": "in"}'),
    
    -- Beta Fintech Rules
    ('2b47e258-86db-4c4f-8f7d-f09430a59802', '6248d652-45f2-47af-a3d8-6565ae026387', 'Case Study Download Intent', 'behavior', 25, TRUE, '{"value": 1, "version": 1, "event_name": "case_study_downloaded", "lookback_days": 14, "property_filters": {}, "aggregate_operator": "count_gte"}'),
    ('2c9cb6b4-a84f-40d4-8e24-99860ce07e4a', '6248d652-45f2-47af-a3d8-6565ae026387', 'Pricing Page Intent', 'behavior', 15, TRUE, '{"value": 3, "version": 1, "event_name": "pricing_page_viewed", "lookback_days": 30, "property_filters": {}, "aggregate_operator": "count_gte"}'),
    ('28fc66a2-0687-4104-8dc1-0a6c3f27c310', '6248d652-45f2-47af-a3d8-6565ae026387', 'Founder Persona', 'fit', 10, TRUE, '{"field": "title", "value": "Founder", "version": 1, "operator": "contains"}'),
    ('24dc73ae-290b-4440-92be-a68d687353d4', '6248d652-45f2-47af-a3d8-6565ae026387', 'Fintech ICP', 'fit', 25, TRUE, '{"field": "industry", "value": "FinTech", "version": 1, "operator": "equals"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO lead_events (
    tenant_id,
    lead_id,
    event_name,
    event_properties,
    occurred_at
)
VALUES
    ('37e8d336-9d56-49e0-a918-6e555295cee9', '4b49bb63-b93f-4381-be55-5e1bfb0b1cf7', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '10 days'),
    ('37e8d336-9d56-49e0-a918-6e555295cee9', '4b49bb63-b93f-4381-be55-5e1bfb0b1cf7', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '2 days'),
    ('37e8d336-9d56-49e0-a918-6e555295cee9', '611952d8-385c-459b-ba20-cac3523dd991', 'demo_requested', '{"channel":"website"}', NOW() - INTERVAL '3 days'),
    ('37e8d336-9d56-49e0-a918-6e555295cee9', '53703ed8-dc7c-478c-b639-579885fb8200', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '7 days'),
    ('37e8d336-9d56-49e0-a918-6e555295cee9', '53703ed8-dc7c-478c-b639-579885fb8200', 'demo_requested', '{"channel":"website"}', NOW() - INTERVAL '1 day'),
    ('6248d652-45f2-47af-a3d8-6565ae026387', 'ff6440f3-1b95-486d-ab64-4e13571bef59', 'case_study_downloaded', '{"asset":"fraud-detection"}', NOW() - INTERVAL '5 days'),
    ('6248d652-45f2-47af-a3d8-6565ae026387', 'c413cc88-9032-48c3-b955-21070eab7bbc', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '8 days'),
    ('6248d652-45f2-47af-a3d8-6565ae026387', 'c413cc88-9032-48c3-b955-21070eab7bbc', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '4 days'),
    ('6248d652-45f2-47af-a3d8-6565ae026387', 'c413cc88-9032-48c3-b955-21070eab7bbc', 'pricing_page_viewed', '{"page":"pricing"}', NOW() - INTERVAL '1 day');
