-- Update PriceDx plan codes
UPDATE plans SET plancode = 'sp_m_v1' WHERE plancode = 'starter-plan' AND product = 'pricedx';
UPDATE plans SET plancode = 'ep_m_v1' WHERE plancode = 'enterprise-plan' AND product = 'pricedx';
