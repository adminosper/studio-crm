CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    mql_score_threshold INTEGER NOT NULL CHECK (mql_score_threshold >= 0),
    sql_score_threshold INTEGER NOT NULL CHECK (sql_score_threshold >= mql_score_threshold),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL,
    industry TEXT NOT NULL,
    company_size INTEGER NOT NULL CHECK (company_size >= 0),
    geography TEXT NOT NULL,
    phone TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'disqualified', 'converted')),
    stage TEXT NOT NULL CHECK (stage IN ('pre_mql', 'mql', 'sql')),
    score INTEGER NOT NULL DEFAULT 0,
    score_last_updated_at TIMESTAMPTZ,
    is_stage_manually_overridden BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT leads_email_per_tenant_unique UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS leads_tenant_id_idx ON leads (tenant_id);

CREATE TABLE IF NOT EXISTS lead_scoring_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('fit', 'behavior')),
    score_delta INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    rule_config JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lead_scoring_rules_tenant_id_idx ON lead_scoring_rules (tenant_id);

CREATE TABLE IF NOT EXISTS lead_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads (id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    event_properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lead_events_tenant_id_idx ON lead_events (tenant_id);
CREATE INDEX IF NOT EXISTS lead_events_lead_id_idx ON lead_events (lead_id);
CREATE INDEX IF NOT EXISTS lead_events_event_name_idx ON lead_events (event_name);
