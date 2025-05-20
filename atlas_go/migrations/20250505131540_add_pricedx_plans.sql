-- Create PriceDx plans
INSERT INTO plans (product, plancode, description, details, status, marketingtype, sortorder) VALUES
('pricedx', 'starter-plan', 'Starter', '["Limited features", "1 user included", "Additional users at $10/month each"]'::jsonb, 1, 0, 1),
('pricedx', 'enterprise-plan', 'Enterprise', '["Full feature access", "Unlimited users", "Custom agreements", "Invoicing and check payments", "Enhanced flexibility"]'::jsonb, 1, 0, 3);
