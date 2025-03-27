-- Create product table
CREATE TABLE product (
    name text NOT NULL,
    schema jsonb NOT NULL,
    "approvalRequired" boolean NOT NULL,
    created timestamptz DEFAULT now(),
    lastupdated timestamptz DEFAULT now(),
    PRIMARY KEY ("name")
);

-- Create email templates table
CREATE TABLE emailtemplates (
    id uuid DEFAULT public.uuid_generate_v7() NOT NULL,
    product text NOT NULL,  -- product name reference
    name text NOT NULL,
    template jsonb,
    subject text,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("product") REFERENCES product("name"),
    UNIQUE ("product", "name")
);

-- Create customer table
CREATE TABLE customer (
    id uuid DEFAULT public.uuid_generate_v7() NOT NULL,
    product text NOT NULL,  -- product name reference
    tenantname text,
    orgname text,
    setupintent text,   -- payment method setup intent
    email text,
    source text,  -- source of signup request
    "approvedBy" uuid,
    schema jsonb,   -- product schema at tenant creation
    data jsonb,     -- data filled in tenant schema
    created timestamptz DEFAULT now() NOT NULL,
    lastupdated timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("product") REFERENCES product("name"),
    UNIQUE ("product", "email"),
    UNIQUE ("product", "tenantname")
);

-- Create plans table
CREATE TABLE plans (
    product text NOT NULL,  -- product name reference
    plancode text NOT NULL,  -- unique plan code
    description text NOT NULL,
    details jsonb NOT NULL,
    status integer NOT NULL,  -- status of plan active, inactive or legacy
    marketingtype integer DEFAULT 0 NOT NULL,  -- property to rank the feature most popular
    sortorder integer NOT NULL,  -- property to order the plan
    created timestamptz DEFAULT now() NOT NULL,
    lastupdated timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY ("product", "plancode"),
    FOREIGN KEY ("product") REFERENCES product("name")
);

-- Create features table
CREATE TABLE features (
    product text NOT NULL,  -- product name reference
    featurecode text NOT NULL,  -- Unique feature billable metric code
    description text DEFAULT ''::text NOT NULL,
    details jsonb DEFAULT '[]'::jsonb NOT NULL,
    status integer DEFAULT '-1'::integer NOT NULL,  -- status of feature active, inactive or legacy
    sortorder integer NOT NULL,  -- property to order the feature
    marketingtype integer DEFAULT 0 NOT NULL,  -- property to rank the feature most popular
    created timestamptz DEFAULT now() NOT NULL,
    lastupdated timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY ("product", "featurecode"),
    FOREIGN KEY ("product") REFERENCES product("name")
);

-- Create planfeatures table
CREATE TABLE planfeatures (
    product text NOT NULL,  -- prodcut name reference
    plancode text NOT NULL,  -- plan plancode reference
    featurecode text NOT NULL,  -- feature featurecode reference
    cansubscribe boolean DEFAULT false NOT NULL,  -- can subscribe this feature on this plan
    isincluded boolean DEFAULT false NOT NULL,  -- is feature included in this plan
    softlimits jsonb DEFAULT '{}'::jsonb NOT NULL,  -- transactions usage limit of feature
    created timestamptz DEFAULT now() NOT NULL,
    lastupdated timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY ("product", "plancode", "featurecode"),
    FOREIGN KEY ("product", "plancode") REFERENCES plans("product", "plancode"),
    FOREIGN KEY ("product", "featurecode") REFERENCES features("product", "featurecode")
);


-- Create failed invoices table
CREATE TABLE failedinvoices (
    invoiceid uuid NOT NULL,
    customerid uuid NOT NULL,
    subscriptionid uuid NOT NULL,
    paymentstatus text,
    reason character varying,
    created timestamp without time zone DEFAULT now() NOT NULL,
    lastupdated timestamp without time zone DEFAULT now() NOT NULL,
    PRIMARY KEY ("invoiceid")
);

-- Create operatorstatus table
CREATE TABLE operatorstatus (
    customerid uuid NOT NULL,
    status integer DEFAULT '-2'::integer,  -- provisioning status
    errors text DEFAULT '{"errors": "not_applicable"}'::text,  -- errors in provisioning
    "provisionedDateTime" timestamptz,
    created timestamptz DEFAULT now(),
    lastupdated timestamptz DEFAULT now(),
    PRIMARY KEY ("customerid"),
    FOREIGN KEY ("customerid") REFERENCES customer("id")
);

-- Create subscription table
CREATE TABLE subscription (
    id uuid DEFAULT public.uuid_generate_v7() NOT NULL,
    name text,  -- subscription name
    customerid uuid NOT NULL,
    product text NOT NULL,  -- product name reference
    plancode text NOT NULL,
    created timestamptz DEFAULT now() NOT NULL,
    lastupdated timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("customerid") REFERENCES customer("id"),
    FOREIGN KEY ("product", "plancode") REFERENCES plans("product", "plancode")
);

-- Create userevent table
CREATE TABLE userevent (
    id uuid NOT NULL, -- keycloak user id
    email text NOT NULL,
    customerid uuid NOT NULL,  -- reference to customer id
    status boolean DEFAULT true NOT NULL,
    created timestamptz DEFAULT now() NOT NULL,
    lastupdated timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY ("id", "customerid"),
    FOREIGN KEY ("customerid") REFERENCES customer("id")
);


-- Insert product data
INSERT INTO product (name, schema, "approvalRequired") VALUES
('veritable', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"phoneNumber","type":"number","label":"Phone Number","subtype":"number","required":false,"className":"form-control","placeholder":"e.g. 1234567890","mapTo":"phone"},{"name":"address","type":"text","label":"Address","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. 1234 Main St","mapTo":"address"},{"name":"city","type":"text","label":"City","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Berkeley","mapTo":"city"},{"name":"state","type":"text","label":"State","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. California","mapTo":"state"},{"name":"country","type":"text","label":"Country","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. US","mapTo":"country"},{"name":"zipCode","type":"text","label":"Zip Code","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. 90001","mapTo":"zipcode"},{"name":"couponCode","type":"text","label":"Coupon Code","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. VER15","mapTo":"couponCode"},{"name":"inviteYourTeam","type":"text","label":"Invite Your Team!","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. jane.smith@company.com, bob.jones@company.com"},{"name":"comment","rows":3,"type":"textarea","label":"Comment","subtype":"textarea","required":false,"className":"form-control","placeholder":"Any specific questions or details you''d like us to know?"},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, false),
('dexit', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"inviteYourTeam","type":"text","label":"Invite Your Team!","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. jane.smith@company.com, bob.jones@company.com"},{"name":"comment","rows":3,"type":"textarea","label":"Comment","subtype":"textarea","required":false,"className":"form-control","placeholder":"Any specific questions or details you''d like us to know?"},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, true),
('jeeves', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"companyNameProvidersOrPayersOnly","type":"text","label":"Company Name (Providers or Payers only)","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"companyNameProvidersOrPayersOnly"},{"name":"whichEhrDoesYourCompanyUse","type":"text","label":"Which EHR does your company use?","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Epic","mapTo":"whichEhrDoesYourCompanyUse"},{"name":"companyShortNameATypicalShortNameThatMightBeUsedForYourOrganization","type":"text","label":"Company Short Name (a typical short name that might be used for your organization)","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. SJHS for St. John''s Health System"},{"name":"haveYouEverAttendedAJeevesDemo","type":"select","label":"Have you ever attended a Jeeves demo?","values":[{"label":"Yes","value":"Yes","selected":true},{"label":"No","value":"No","selected":false}],"multiple":false,"required":true,"className":"form-control"},{"name":"comments","rows":3,"type":"textarea","label":"Comments","subtype":"textarea","required":false,"className":"form-control","placeholder":"Any contextual details here would be helpful. How do you know of 314e and/or Jeeves? Have you spoken with anyone at 314e before? When are you looking to buy by? etc."},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, true),
('hdp', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"comments","rows":3,"type":"textarea","label":"Comments","subtype":"textarea","required":false,"className":"form-control","placeholder":"Any contextual details here would be helpful. How do you know of 314e and/or Hdp? Have you spoken with anyone at 314e before? When are you looking to buy by? etc."},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, true),
('practifly', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, true),
('penknife', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"phoneNumber","type":"number","label":"Phone Number","subtype":"number","required":true,"className":"form-control","placeholder":"e.g. 1234567890","mapTo":"phoneNumber"},{"name":"companyDomain","type":"text","label":"Company Domain","subtype":"text","required":true,"className":"form-control","maxlength":25,"placeholder":"Eg. 314ecorp.com","mapTo":"companyDomain"},{"name":"tenantType","type":"select","label":"Tenant Type","values":[{"label":"Staffing","value":"Staffing","selected":true},{"label":"Internal Hiring","value":"InternalHiring","selected":false}],"multiple":false,"required":true,"className":"form-control","mapTo":"tenantType"},{"name":"emailProvider","type":"select","label":"Email Provider","values":[{"label":"Google","value":"Google","selected":true},{"label":"Microsoft","value":"Microsoft","selected":false}],"multiple":false,"required":true,"className":"form-control","mapTo":"emailProvider"},{"name":"comments","rows":3,"type":"textarea","label":"Comments","subtype":"textarea","required":false,"className":"form-control","placeholder":"Any contextual details here would be helpful. How do you know of 314e and/or Penknife? Have you spoken with anyone at 314e before? When are you looking to buy by? etc."},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, true),
('zsegment', '[{"name":"firstName","type":"text","label":"First Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. John","mapTo":"firstName"},{"name":"lastName","type":"text","label":"Last Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. Doe","mapTo":"lastName"},{"name":"workEmail","type":"text","label":"Work Email","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. john.doe@company.com","mapTo":"email"},{"name":"organizationName","type":"text","label":"Organization Name","subtype":"text","required":false,"className":"form-control","placeholder":"e.g. ZZZ Medical Center","mapTo":"organization"},{"name":"tenantName","type":"text","label":"Tenant Name","subtype":"text","required":true,"className":"form-control","placeholder":"e.g. test1","mapTo":"tenant"},{"name":"planName","type":"select","label":"PlanName","values":[{"label":"Free","value":"Free","selected":true},{"label":"Pro","value":"Pro","selected":false},{"label":"Entrerprise","value":"Entrerprise","selected":false}],"multiple":false,"required":true,"className":"form-control","placeholder":"Plan Name","mapTo":"planName"},{"name":"comments","rows":3,"type":"textarea","label":"Comments","subtype":"textarea","required":false,"className":"form-control","placeholder":"Any contextual details here would be helpful. How do you know of 314e and/or Zsegment? Have you spoken with anyone at 314e before? When are you looking to buy by? etc."},{"name":"termsAndConditions","type":"checkbox-group","label":"Terms and Conditions","other":false,"inline":false,"toggle":false,"values":[{"label":"I agree to 314e''s Terms of Use","value":"agree","selected":false}],"required":true}]'::jsonb, true);

-- Insert plans data
INSERT INTO plans (plancode, details, status, marketingtype, sortorder, description, product) VALUES
('lp_m_v2', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 1, 2, 'Upto 250 transactions\n$8 for every additional 50 transactions', 'veritable'),
('ee_m_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 2, 0, 3, 'Upto 250 transactions\n$8 for every additional 50 transactions', 'veritable'),
('lp_m_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 2, 'Upto 250 transactions\n$10 for every additional 75 transactions', 'veritable'),
('lp_y_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 2, 'Upto 3000 transactions\n$10 for every additional 75 transactions', 'veritable'),
('lp_y_v2', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 2, 'Upto 3000 transactions\n$8 for every additional 50 transactions', 'veritable'),
('sp_y_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 1200 transactions\n$10 for every additional 50 transactions', 'veritable'),
('lp_y_v3', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 1, 2, 'Upto 3000 transactions\n$8 for every additional 50 transactions', 'veritable'),
('sp_y_v2', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 1200 transactions\n$10 for every additional 50 transactions', 'veritable'),
('sp_m_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 100 transactions\n$10 for every additional 50 transactions', 'veritable'),
('sp_y_v3', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 1200 transactions\n$10 for every additional 50 transactions', 'veritable'),
('ubp_m_v1', '["Verify real-time eligibility & benefits from 1000+ payers", "Track the status for professional and institutional claims", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 1, 2, 1, 'Includes 250 transactions; then pay as you use', 'veritable');

-- Insert features data
INSERT INTO features (featurecode, description, details, status, sortorder, marketingtype, product) VALUES
('a_payments', 'Easily collect payments from your patients directly within your veritable portal. Create an invoice or collect generic payments. The monthly subscription fee for this add-on is $30 and this will be charged with your next periodic plan renewal.\nOur current payment gateway integrations: Stripe, Authorize.net', '["Easily collect payments from patients using a secure payment link.", "Generate and send payment requests directly to patients for faster payment processing.", "Track the real-time status of payments, including completed, pending, and failed transactions.", "Access a comprehensive view of all past payment submissions and transactions.", "Receive monthly reports with insights into total payments collected, number of transactions, and more.", "Seamlessly integrate with your preferred payment gateway for secure transactions."]'::jsonb, 1, 2, 0, 'veritable'),
('default', '', '[]'::jsonb, 1, 1, 0, 'veritable')
;

-- Insert planfeatures data
INSERT INTO planfeatures (product, plancode, featurecode, cansubscribe, isincluded, softlimits) VALUES
('veritable', 'sp_m_v1', 'default', false, true, '{"count": 100}'::jsonb),
('veritable', 'lp_m_v1', 'default', false, true, '{"count": 250}'::jsonb),
('veritable', 'lp_y_v1', 'default', false, true, '{"count": 3000}'::jsonb),
('veritable', 'lp_y_v3', 'default', false, true, '{"count": 3000}'::jsonb),
('veritable', 'sp_y_v2', 'default', false, true, '{"count": 1200}'::jsonb),
('veritable', 'ee_m_v1', 'default', false, true, '{}'::jsonb),
('veritable', 'sp_y_v1', 'default', false, true, '{"count": 1200}'::jsonb),
('veritable', 'lp_m_v2', 'default', false, true, '{"count": 250}'::jsonb),
('veritable', 'lp_y_v2', 'default', false, true, '{"count": 3000}'::jsonb),
('veritable', 'sp_m_v1', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'lp_y_v3', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'sp_y_v2', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'lp_m_v2', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'lp_m_v1', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'lp_y_v1', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'lp_y_v2', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'sp_y_v1', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'sp_y_v3', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'sp_y_v3', 'default', false, true, '{"count": 1200}'::jsonb),
('veritable', 'ubp_m_v1', 'a_payments', true, false, '{}'::jsonb),
('veritable', 'ubp_m_v1', 'default', false, true, '{"count": 250}'::jsonb)
;

