-- Insurance Discovery and MBI Lookup ship as features included in ubp_m_v1, not purchasable add-ons.
-- Both metrics are zero-suppressed in Lago: no existing bill changes, no customer migration needed.
-- Included != feature-on -- ID/MBI access stays gated by the per-tenant flag.
-- Codes are unprefixed (a_ marks an add-on metric, e.g. a_payments); Lago metrics renamed to match.

-- Billable-metric features: status=1 active, no marketing bullets.
INSERT INTO features (featurecode, description, details, status, sortorder, marketingtype, product) VALUES
('insurance_discovery', 'Uncover active coverage with just basic patient demographics, to surface hidden or forgotten insurance for your patients.', '[]'::jsonb, 1, 3, 0, 'veritable'),
('mbi_lookup', 'Retrieves a patient''s Medicare Beneficiary Identifier using basic patient details, and verify Medicare eligibility without chasing down the number manually.', '[]'::jsonb, 1, 4, 0, 'veritable');

-- Empty softlimits -- ID/MBI usage does not draw down the 250-tx allowance on `default`.
-- get_plan_add_ons.sql requires isincluded=FALSE AND cansubscribe=TRUE, so these bypass
-- prefetch_addons() and get_addon_price(), surfacing via get_plans.sql includedFeatures instead.
INSERT INTO planfeatures (product, plancode, featurecode, cansubscribe, isincluded, softlimits) VALUES
('veritable', 'ubp_m_v1', 'insurance_discovery', false, true, '{}'::jsonb),
('veritable', 'ubp_m_v1', 'mbi_lookup', false, true, '{}'::jsonb);
