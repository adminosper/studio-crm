# Lead Scoring Rule Contracts

This document defines the contract for creating and storing lead scoring rules in the Lead Scoring and Qualification slice.

The purpose of this document is to remove ambiguity before we build the scoring engine. The scoring engine should not interpret arbitrary JSON. It should operate on a small, explicit, versioned rule catalog.

---

## 1. Why This Document Exists

The current `lead_scoring_rules.rule_config` field is stored as `JSONB`, but that does **not** mean tenants can submit free-form JSON.

For this feature, we want:

- fixed rule shapes
- deterministic validation
- explicit semantics for time windows
- a clear path for backward compatibility

So the correct mental model is:

- `JSONB` is only the storage format
- the real contract is a **typed rule model**
- rule evaluation is driven by `(rule_type, config_version)`

---

## 2. Core Concepts

### 2.1 Rule Type

There are only two rule types in this slice:

- `fit`
- `behavior`

Each rule type has its own fixed config model.

### 2.2 Rule Contract

A rule contract is the exact allowed shape of `rule_config` for a given `rule_type`.

Example:

- `fit` rules must use the fit config model
- `behavior` rules must use the behavior config model

Any unknown field, missing required field, or unsupported operator should be rejected at API validation time.

### 2.3 Config Version

Every `rule_config` should be treated as versioned.

Recommended direction:

```json
{
  "version": 1,
  "...": "other fields depend on rule type"
}
```

We are not changing the schema right this second, but before the scoring engine milestone we should tighten the API model so that rule configs are explicitly versioned.

That gives us a stable compatibility story when we extend the contract later.

---

## 3. Rule Creation Must Come From A Predefined Catalog

Tenants should not invent their own scoring rule structure.

Instead, rule creation must follow a predefined catalog:

- predefined rule types
- predefined allowed fields
- predefined allowed operators
- predefined optional fields
- predefined evaluation semantics

This does **not** mean we need hardcoded named presets only.

It means:

- users can configure rules
- but only within a bounded, validated grammar

So the system supports **configurable rules**, not **arbitrary rule design**.

---

## 4. Fit Rule Contract

## 4.1 Recommended V1 Fit Rule Shape

```json
{
  "version": 1,
  "field": "industry",
  "operator": "in",
  "value": ["SaaS", "FinTech"]
}
```

## 4.2 Required Fields

- `version`
- `field`
- `operator`
- `value`

## 4.3 Allowed Fields

- `industry`
- `company_size`
- `geography`
- `title`
- `source`

## 4.4 Allowed Operator Matrix

The important constraint is not just "valid operator names". It is also "which operators are valid for which fields".

### String-like fields

Fields:

- `industry`
- `geography`
- `source`

Allowed operators:

- `equals`
- `not_equals`
- `in`
- `not_in`

### Title field

Field:

- `title`

Allowed operators:

- `equals`
- `not_equals`
- `in`
- `not_in`
- `contains`

### Numeric field

Field:

- `company_size`

Allowed operators:

- `equals`
- `not_equals`
- `gte`
- `lte`

## 4.5 Validation Rules

- `field` must belong to the allowed catalog
- `operator` must be valid for that specific field
- `value` type must match the chosen field/operator pair
- unknown extra keys must be rejected

Examples:

- `company_size + contains` => invalid
- `industry + gte` => invalid
- `company_size + in ["100", "200"]` => invalid in V1

---

## 5. Behavior Rule Contract

## 5.1 Recommended V1 Behavior Rule Shape

```json
{
  "version": 1,
  "event_name": "pricing_page_viewed",
  "aggregate_operator": "count_gte",
  "value": 2,
  "lookback_days": 30,
  "property_filters": {
    "page": "pricing"
  }
}
```

## 5.2 Required Fields

- `version`
- `event_name`
- `aggregate_operator`
- `value`
- `lookback_days`

## 5.3 Optional Fields

- `property_filters`

## 5.4 Why `lookback_days` Should Be Required In V1

This is the most important decision for behavior rules.

If `lookback_days` is omitted, the engine has to guess whether the rule means:

- use all historical events forever
- use some default time window
- use only recent events

That ambiguity is bad for both validation and business semantics.

So the recommended V1 rule is:

- `lookback_days` is **required**
- omission is **invalid**

Why this is better:

- no hidden default behavior
- no accidental qualification from very old events
- deterministic rule meaning
- reviewers can reason about the score easily

### Explicit Non-Decision

In V1, `lookback_days = null` should **not** mean "lifetime".

If we need lifetime semantics later, we should model it explicitly rather than overloading `null`.

Recommended future pattern:

```json
{
  "version": 2,
  "window_type": "lifetime",
  "event_name": "demo_requested",
  "aggregate_operator": "count_gte",
  "value": 1,
  "property_filters": {}
}
```

That is much clearer than using a missing or null lookback.

## 5.5 Allowed Aggregate Operators

- `count_gte`
- `count_eq`

That means:

- count of matching events in the window is `>= value`
- count of matching events in the window is `== value`

## 5.6 Which Attributes Can Be Optional

Yes, some behavior-rule attributes can be optional, but only when omission has a clear semantic meaning.

In V1:

- `property_filters` is optional
  - omitted or `{}` means "match by event name only"

The following should **not** be optional in V1:

- `event_name`
- `aggregate_operator`
- `value`
- `lookback_days`

Reason:

- omitting any of these changes the meaning of the rule too much
- validation becomes ambiguous
- the engine would need hidden assumptions

---

## 6. How To Ensure Each Rule Type Uses A Fixed Model

We should enforce this at three levels.

## 6.1 API Model Level

Use typed request models per rule type.

Conceptually:

- `FitRuleConfigV1`
- `BehaviorRuleConfigV1`

Then the outer request chooses the inner config model based on `rule_type`.

This is the most important protection because it stops bad configs before they reach the database.

## 6.2 Service Layer Level

The service should normalize the config before persistence.

Meaning:

- reject unknown keys
- apply explicit defaults only where documented
- persist a canonical JSON structure

Example:

- if `property_filters` is omitted, store it as `{}` explicitly

That avoids multiple equivalent representations for the same rule.

## 6.3 Database Level

The database should remain a safety net, not the primary validator.

At minimum:

- `rule_type` stays constrained to `fit | behavior`
- `rule_config` must be valid JSONB

Optional later hardening:

- DB `CHECK` constraints for version presence
- DB `CHECK` constraints for required keys per rule type

For this assignment slice, strong API validation is enough. We do not need to overbuild DB-side JSON validation right now.

---

## 7. Backward Compatibility Strategy

This is the answer to: "What happens when we add new fields later?"

The rule is:

- do not reinterpret old configs silently
- evolve contracts by version

## 7.1 Contract Evolution Policy

### Safe additive change

If a new field is:

- optional
- has a deterministic default
- does not change the meaning of existing stored rows

then we may keep the same config version.

Example:

- adding optional `property_filters` with default `{}` to a behavior rule model

### Breaking semantic change

If a new field:

- becomes required
- changes how existing fields are interpreted
- changes time-window semantics
- changes operator meaning

then we should introduce a new config version.

Example:

- introducing `window_type`
- changing `value` meaning from "count threshold" to something else

## 7.2 Engine Behavior Across Versions

The scoring engine should dispatch by:

- `rule_type`
- `rule_config.version`

Examples:

- `fit + version 1` => evaluate with fit rule evaluator V1
- `behavior + version 1` => evaluate with behavior rule evaluator V1
- `behavior + version 2` => evaluate with behavior rule evaluator V2

That keeps old rules stable even when the product evolves.

## 7.3 Migration Policy

When we introduce a new version:

- old rules remain valid
- new rule creation uses the latest version
- optional migration scripts can rewrite older rows later if desired

This is safer than rewriting old rules implicitly at read time.

---

## 8. Recommended V1 Decisions

For this implementation slice, the cleanest decisions are:

1. `rule_config` is not free-form JSON. It follows a fixed typed contract.
2. `behavior.lookback_days` is required in V1.
3. `behavior.property_filters` is optional and defaults to `{}`.
4. fit-rule operator validity depends on the chosen field.
5. unknown config keys are rejected.
6. future incompatible changes must use config versioning.

---

## 9. Impact On Upcoming Milestone 3

Before or during milestone 3, we should tighten the current implementation to match this document.

Recommended changes:

1. Make `BehaviorRuleConfig.lookback_days` required.
2. Narrow fit-rule operator support by field instead of allowing one flat operator set for every field.
3. Introduce explicit config versioning in `rule_config`.
4. Keep canonical persistence for optional objects such as `property_filters`.

Until we do that, the current API is functional, but the contract is still looser than the desired engine design.
