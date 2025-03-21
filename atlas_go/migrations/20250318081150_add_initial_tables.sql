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
('Veritable', '{"$defs": {"CustomCustomerBillingConfiguration": {"properties": {"invoice_grace_period": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": null, "title": "Invoice Grace Period"}, "payment_provider": {"default": "stripe", "title": "Payment Provider", "type": "string"}, "payment_provider_code": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "Payment Provider Code"}, "provider_customer_id": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "Provider Customer Id"}, "sync": {"default": true, "title": "Sync", "type": "boolean"}, "sync_with_provider": {"default": true, "title": "Sync With Provider", "type": "boolean"}, "document_locale": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "title": "Document Locale"}, "provider_payment_methods": {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": null, "title": "Provider Payment Methods"}}, "title": "CustomCustomerBillingConfiguration", "type": "object"}}, "properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"className": "form-control", "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. ZZZ Medical Center", "subtype": "text", "title": "Organization", "type": "string"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}, "billing_configuration": {"$ref": "#/$defs/CustomCustomerBillingConfiguration", "className": "form-control", "default": {"invoice_grace_period": null, "payment_provider": "stripe", "payment_provider_code": null, "provider_customer_id": null, "sync": true, "sync_with_provider": true, "document_locale": null, "provider_payment_methods": null}, "label": "Billing Configuration", "mapTo": "billing_configuration", "name": "billingConfiguration", "order": 6, "subtype": "text"}, "external_id": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "External ID", "mapTo": "external_id", "name": "externalId", "order": 7, "placeholder": "e.g. e38c5f99-580b-4bfd-a926-a82402eb8d6a", "subtype": "text", "title": "External Id"}, "phone": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Phone Number", "mapTo": "phone", "name": "phoneNumber", "order": 8, "placeholder": "e.g. 1234567890", "subtype": "number", "title": "Phone"}, "address_line1": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Address", "mapTo": "address_line1", "name": "address", "order": 9, "placeholder": "e.g. 1234 Main St", "subtype": "text", "title": "Address Line1"}, "city": {"className": "form-control", "label": "City", "mapTo": "city", "name": "city", "order": 10, "placeholder": "e.g. Berkeley", "subtype": "text", "title": "City", "type": "string"}, "state": {"className": "form-control", "label": "State", "mapTo": "state", "name": "state", "order": 11, "placeholder": "e.g. California", "subtype": "text", "title": "State", "type": "string"}, "country": {"className": "form-control", "label": "Country", "mapTo": "country", "name": "country", "order": 12, "placeholder": "e.g. US", "subtype": "text", "title": "Country", "type": "string"}, "zipcode": {"className": "form-control", "label": "Zip Code", "mapTo": "zipcode", "name": "zipCode", "order": 13, "placeholder": "e.g. 90001", "subtype": "text", "title": "Zipcode", "type": "string"}, "coupon_code": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Coupon Code", "mapTo": "coupon_code", "name": "couponCode", "order": 14, "placeholder": "e.g. VER15", "subtype": "text", "title": "Coupon Code"}, "emailSent": {"className": "form-control", "default": false, "inline": false, "label": "Email Sent", "mapTo": "emailSent", "name": "emailSent", "order": 15, "other": false, "title": "Emailsent", "toggle": false, "type": "checkbox-group"}}, "required": ["firstName", "lastName", "email", "organization", "tenant", "city", "state", "country", "zipcode"], "title": "VeritableSchema", "type": "object"}'::jsonb, false),
('Dexit', '{"properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. Z Medical Center", "subtype": "text", "title": "Organization"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}}, "required": ["firstName", "lastName", "email", "tenant"], "title": "DexitSchema", "type": "object"}'::jsonb, true),
('Jeeves', '{"properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. ZZZ Medical", "subtype": "text", "title": "Organization"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}, "emailSent": {"className": "form-control", "default": false, "inline": false, "label": "Email Sent", "mapTo": "emailSent", "name": "emailSent", "order": 6, "other": false, "title": "Emailsent", "toggle": false, "type": "checkbox-group"}, "companyNameProvidersOrPayersOnly": {"className": "form-control", "label": "Company Name", "mapTo": "companyNameProvidersOrPayersOnly", "name": "companyNameProvidersOrPayersOnly", "order": 7, "placeholder": "e.g. AETNA", "subtype": "text", "title": "Companynameprovidersorpayersonly", "type": "string"}, "whichEhrDoesYourCompanyUse": {"className": "form-control", "label": "Which EHR does your company use?", "mapTo": "whichEhrDoesYourCompanyUse", "name": "whichEhrDoesYourCompanyUse", "order": 8, "placeholder": "e.g. Epic", "subtype": "text", "title": "Whichehrdoesyourcompanyuse", "type": "string"}, "is_deployment": {"className": "form-control", "default": false, "inline": false, "label": "Is Deployment", "mapTo": "is_deployment", "name": "isDeployment", "order": 9, "other": false, "title": "Is Deployment", "toggle": false, "type": "checkbox-group"}}, "required": ["firstName", "lastName", "email", "tenant", "companyNameProvidersOrPayersOnly", "whichEhrDoesYourCompanyUse"], "title": "JeevesSchema", "type": "object"}'::jsonb, true),
('Hdp', '{"properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. ZZZ Medical Center", "subtype": "text", "title": "Organization"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}, "emailSent": {"className": "form-control", "default": false, "inline": false, "label": "Email Sent", "mapTo": "emailSent", "name": "emailSent", "order": 6, "other": false, "title": "Emailsent", "toggle": false, "type": "checkbox-group"}}, "required": ["firstName", "lastName", "email", "tenant"], "title": "HDPSchema", "type": "object"}'::jsonb, true),
('Practifly', '{"properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. ZZZ Medical", "subtype": "text", "title": "Organization"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}, "emailSent": {"className": "form-control", "default": false, "inline": false, "label": "Email Sent", "mapTo": "emailSent", "name": "emailSent", "order": 6, "other": false, "title": "Emailsent", "toggle": false, "type": "checkbox-group"}}, "required": ["firstName", "lastName", "email", "tenant"], "title": "PractiflySchema", "type": "object"}'::jsonb, true),
('Penknife', '{"$defs": {"EmailProvider": {"enum": ["Google", "Microsoft"], "title": "EmailProvider", "type": "string"}, "TenantType": {"enum": ["Staffing", "InternalHiring"], "title": "TenantType", "type": "string"}}, "properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"className": "form-control", "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. ZZZ Medical Center", "subtype": "text", "title": "Organization", "type": "string"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}, "phoneNumber": {"className": "form-control", "label": "Phone Number", "mapTo": "phoneNumber", "name": "phoneNumber", "order": 5, "subtype": "number", "title": "Phonenumber", "type": "string"}, "companyDomain": {"className": "form-control", "label": "Company Domain", "mapTo": "companyDomain", "name": "companyDomain", "order": 6, "subtype": "text", "title": "Companydomain", "type": "string"}, "tenantType": {"$ref": "#/$defs/TenantType", "className": "form-control", "default": "Staffing", "label": "Tenant Type", "mapTo": "tenantType", "name": "tenantType", "order": 7, "subtype": "select"}, "emailProvider": {"$ref": "#/$defs/EmailProvider", "className": "form-control", "default": "Google", "label": "Email Provider", "mapTo": "emailProvider", "name": "emailProvider", "order": 8, "subtype": "select"}}, "required": ["firstName", "lastName", "email", "organization", "tenant", "phoneNumber", "companyDomain"], "title": "PenknifeSchema", "type": "object"}'::jsonb, true),
('Zsegment', '{"properties": {"firstName": {"className": "form-control", "label": "First Name", "mapTo": "firstName", "name": "firstName", "order": 1, "placeholder": "e.g. John", "subtype": "text", "title": "Firstname", "type": "string"}, "lastName": {"className": "form-control", "label": "Last Name", "mapTo": "lastName", "name": "lastName", "order": 2, "placeholder": "e.g. Doe", "subtype": "text", "title": "Lastname", "type": "string"}, "email": {"className": "form-control", "format": "email", "label": "Work Email", "mapTo": "email", "name": "workEmail", "order": 3, "placeholder": "e.g. john.doe@example.com", "subtype": "text", "title": "Email", "type": "string"}, "organization": {"anyOf": [{"type": "string"}, {"type": "null"}], "className": "form-control", "default": null, "label": "Organization Name", "mapTo": "organization", "name": "organizationName", "order": 4, "placeholder": "e.g. ZZZ Medical Center", "subtype": "text", "title": "Organization"}, "tenant": {"className": "form-control", "label": "Tenant Name", "mapTo": "tenant", "name": "tenantName", "order": 5, "pattern": "^[a-z][a-z0-9]{2,14}$", "placeholder": "e.g. test1", "subtype": "text", "title": "Tenant", "type": "string"}, "emailSent": {"className": "form-control", "default": false, "inline": false, "label": "Email Sent", "mapTo": "emailSent", "name": "emailSent", "order": 6, "other": false, "title": "Emailsent", "toggle": false, "type": "checkbox-group"}, "PlanName": {"className": "form-control", "default": "Free", "label": "Plan Name", "mapTo": "PlanName", "name": "planName", "order": 7, "placeholder": "e.g. Pro", "subtype": "text", "title": "Planname", "type": "string"}}, "required": ["firstName", "lastName", "email", "tenant"], "title": "ZsegmentSchema", "type": "object"}'::jsonb, true);

-- Insert plans data
INSERT INTO plans (plancode, details, status, marketingtype, sortorder, description, product) VALUES
('lp_m_v2', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 1, 2, 'Upto 250 transactions\n$8 for every additional 50 transactions', 'Veritable'),
('ee_m_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 2, 0, 3, 'Upto 250 transactions\n$8 for every additional 50 transactions', 'Veritable'),
('lp_m_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 2, 'Upto 250 transactions\n$10 for every additional 75 transactions', 'Veritable'),
('lp_y_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 2, 'Upto 3000 transactions\n$10 for every additional 75 transactions', 'Veritable'),
('lp_y_v2', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 2, 'Upto 3000 transactions\n$8 for every additional 50 transactions', 'Veritable'),
('sp_y_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 1200 transactions\n$10 for every additional 50 transactions', 'Veritable'),
('lp_y_v3', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 1, 2, 'Upto 3000 transactions\n$8 for every additional 50 transactions', 'Veritable'),
('sp_y_v2', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 1200 transactions\n$10 for every additional 50 transactions', 'Veritable'),
('sp_m_v1', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 100 transactions\n$10 for every additional 50 transactions', 'Veritable'),
('sp_y_v3', '["Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 0, 0, 1, 'Upto 1200 transactions\n$10 for every additional 50 transactions', 'Veritable'),
('ubp_m_v1', '["Verify real-time eligibility & benefits from 1000+ payers", "Track the status for professional and institutional claims", "Obtain detailed benefits and coverage information", "Perform batch verification of eligibility and benefits", "Easily access/manage previous inquiries for eligibility and claims status"]'::jsonb, 1, 2, 1, 'Includes 250 transactions; then pay as you use', 'Veritable');

-- Insert features data
INSERT INTO features (featurecode, description, details, status, sortorder, marketingtype, product) VALUES
('a_payments', 'Easily collect payments from your patients directly within your Veritable portal. Create an invoice or collect generic payments. The monthly subscription fee for this add-on is $30 and this will be charged with your next periodic plan renewal.\nOur current payment gateway integrations: Stripe, Authorize.net', '["Easily collect payments from patients using a secure payment link.", "Generate and send payment requests directly to patients for faster payment processing.", "Track the real-time status of payments, including completed, pending, and failed transactions.", "Access a comprehensive view of all past payment submissions and transactions.", "Receive monthly reports with insights into total payments collected, number of transactions, and more.", "Seamlessly integrate with your preferred payment gateway for secure transactions."]'::jsonb, 1, 2, 0, 'Veritable'),
('default', '', '[]'::jsonb, 1, 1, 0, 'Veritable')
;

-- Insert planfeatures data
INSERT INTO planfeatures (product, plancode, featurecode, cansubscribe, isincluded, softlimits) VALUES
('Veritable', 'sp_m_v1', 'default', false, true, '{"count": 100}'::jsonb),
('Veritable', 'lp_m_v1', 'default', false, true, '{"count": 250}'::jsonb),
('Veritable', 'lp_y_v1', 'default', false, true, '{"count": 3000}'::jsonb),
('Veritable', 'lp_y_v3', 'default', false, true, '{"count": 3000}'::jsonb),
('Veritable', 'sp_y_v2', 'default', false, true, '{"count": 1200}'::jsonb),
('Veritable', 'ee_m_v1', 'default', false, true, '{}'::jsonb),
('Veritable', 'sp_y_v1', 'default', false, true, '{"count": 1200}'::jsonb),
('Veritable', 'lp_m_v2', 'default', false, true, '{"count": 250}'::jsonb),
('Veritable', 'lp_y_v2', 'default', false, true, '{"count": 3000}'::jsonb),
('Veritable', 'sp_m_v1', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'lp_y_v3', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'sp_y_v2', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'lp_m_v2', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'lp_m_v1', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'lp_y_v1', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'lp_y_v2', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'sp_y_v1', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'sp_y_v3', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'sp_y_v3', 'default', false, true, '{"count": 1200}'::jsonb),
('Veritable', 'ubp_m_v1', 'a_payments', true, false, '{}'::jsonb),
('Veritable', 'ubp_m_v1', 'default', false, true, '{"count": 250}'::jsonb)
;

