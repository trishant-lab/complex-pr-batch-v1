"""add accounts tables

Revision ID: 26471c957a7c
Revises: b7144993b2b1
Create Date: 2024-12-17 16:01:11.843191

"""

import json
from collections.abc import Callable

import sqlalchemy as sa
from sqlalchemy import text
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

from app.models.enums import FeatureStatus, MarketingType, PlanStatus
from app.models.addOns.veritable import VeritableFeature

# revision identifiers, used by Alembic.
revision: str = "26471c957a7c"
down_revision = "b7144993b2b1"
branch_labels = None
depends_on = None

plan_details = [
    "Verify real-time eligibility and track claim status for professional and institutional claims from 1500+ payers",
    "Obtain detailed benefits and coverage information",
    "Perform batch verification of eligibility and benefits",
    "Easily access/manage previous inquiries for eligibility and claims status",
]

payment_feature_description = (
    "Easily collect payments from your patients directly within your Veritable portal. "
    "Create a payment request or collect generic payments. "
    "The monthly subscription fee for this add-on is $30 and this will be charged with your next periodic plan renewal."
    "\nOur current payment gateway integrations: Stripe, Authorize.net"
)

payment_feature_details = [
    "Easily collect payments from patients using a secure payment link.",
    "Generate and send payment requests directly to patients for faster payment processing.",
    "Track the real-time status of payments, including completed, pending, and failed transactions.",
    "Access a comprehensive view of all past payment submissions and transactions.",
    "Receive monthly reports with insights into total payments collected, number of transactions, and more.",
    "Seamlessly integrate with your preferred payment gateway for secure transactions.",
]


def upgrade(**kwargs: str | Callable) -> None:
    """
    Upgrade function
    """
    op.add_column("tenant", sa.Column("setupintent", type_=sa.UnicodeText(), comment="payment method setup intent"))
    op.add_column("tenant", sa.Column("email", type_=sa.UnicodeText(), nullable=True))
    op.create_unique_constraint("tenant_product_email_unique_idx", "tenant", ["name", "product", "email"])

    # plans
    plans = op.create_table(
        "plans",
        sa.Column(
            "plancode",
            type_=sa.UnicodeText(),
            primary_key=True,
            comment="Unique plan code",
        ),
        sa.Column(
            "details",
            type_=sa.UnicodeText(),
            nullable=False,
            comment="details of plan",
        ),
        sa.Column(
            "status",
            type_=sa.Integer(),
            nullable=False,
            comment="status of plan",
        ),
        sa.Column(
            "marketingtype",
            type_=sa.Integer(),
            nullable=False,
            comment="property to rank the feature most popular",
        ),
        sa.Column(
            "sortorder",
            type_=sa.Integer(),
            nullable=False,
            comment="property to order the plan",
        ),
        sa.Column(
            "created",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="Creation time of this entry",
        ),
        sa.Column(
            "lastupdated",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="last updated of this entry",
        ),
        sa.Column(
            "description",
            type_=sa.UnicodeText(),
            nullable=False,
            comment="Description of plan",
        ),
        sa.Column(
            "product",
            sa.ForeignKey("product.id"),
            type_=UUID,
            nullable=False,
            comment="product id reference",
        ),
        sa.UniqueConstraint("plancode", name="plans_pkey"),
    )

    # features
    features = op.create_table(
        "features",
        sa.Column(
            "featurecode",
            type_=sa.UnicodeText(),
            primary_key=True,
            comment="Unique feature billable metric code",
        ),
        sa.Column(
            "description",
            type_=sa.UnicodeText(),
            nullable=False,
            comment="description of feature",
        ),
        sa.Column(
            "details",
            type_=sa.UnicodeText(),
            nullable=False,
            comment="details of feature",
        ),
        sa.Column(
            "status",
            type_=sa.Integer(),
            nullable=False,
            comment="status of feature active, inactive or legacy",
        ),
        sa.Column(
            "sortorder",
            type_=sa.Integer(),
            nullable=False,
            comment="property to order the feature",
        ),
        sa.Column(
            "marketingtype",
            type_=sa.Integer(),
            nullable=False,
            comment="property to rank the feature most popular",
        ),
        sa.Column(
            "created",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="creation time of feature",
        ),
        sa.Column(
            "lastupdated",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="last updated time of feature",
        ),
        sa.Column(
            "product",
            sa.ForeignKey("product.id"),
            type_=UUID,
            nullable=False,
            comment="product id reference",
        ),
        sa.UniqueConstraint("featurecode", name="features_pkey"),
    )

    # planfeatures
    planfeatures = op.create_table(
        "planfeatures",
        sa.Column(
            "plancode",
            sa.ForeignKey("plans.plancode"),
            type_=sa.UnicodeText(),
            nullable=False,
            comment="plancode from plans table",
        ),
        sa.Column(
            "featurecode",
            sa.ForeignKey("features.featurecode"),
            type_=sa.UnicodeText(),
            nullable=False,
            comment="featurecode from features table",
        ),
        sa.Column(
            "cansubscribe",
            type_=sa.Boolean(),
            nullable=False,
            default=False,
            comment="can subscribe this feature on this plan",
        ),
        sa.Column(
            "isincluded",
            type_=sa.Boolean(),
            nullable=False,
            default=False,
            comment="is feature included in this plan",
        ),
        sa.Column(
            "softlimits",
            type_=sa.UnicodeText(),
            nullable=False,
            default="{}",
            comment="transactions usage limit of feature",
        ),
        sa.Column(
            "created",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="creation time of this mapping",
        ),
        sa.Column(
            "lastupdated",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="last updated time of this mapping",
        ),
        sa.PrimaryKeyConstraint("plancode", "featurecode"),
    )

    # subscription
    op.create_table(
        "subscription",
        sa.Column(
            "id",
            type_=UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v1mc()"),
            comment="subscription id",
        ),
        sa.Column(
            "name",
            type_=sa.UnicodeText(),
            nullable=True,
            comment="subscription name",
        ),
        sa.Column(
            "customerid",
            type_=UUID,
            nullable=False,
            comment="customer id",
        ),
        sa.Column(
            "plancode",
            type_=sa.UnicodeText(),
            nullable=False,
            comment="Unique plan code",
        ),
        sa.Column(
            "created",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="Creation time of this entry",
        ),
        sa.Column(
            "lastupdated",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="last updated of this entry",
        ),
        sa.PrimaryKeyConstraint("id", name="subscription_pkey"),
    )

    # userevent
    op.create_table(
        "userevent",
        sa.Column(
            "id",
            type_=UUID,
            comment="Keycloak User Id",
        ),
        sa.Column(
            "email",
            type_=sa.UnicodeText(),
            nullable=False,
            comment="User email",
        ),
        sa.Column(
            "customerid",
            sa.ForeignKey("tenant.id"),
            type_=UUID,
            nullable=False,
            comment="User customer_id",
        ),
        sa.Column(
            "status",
            type_=sa.Boolean(),
            nullable=False,
            default=True,
            comment="User status",
        ),
        sa.Column(
            "created",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="Creation time of this entry",
        ),
        sa.Column(
            "lastupdated",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="last updated of this entry",
        ),
        sa.PrimaryKeyConstraint("id", "customerid", name="keycloak_customer_pk"),
    )

    # failedinvoices
    op.create_table(
        "failedinvoices",
        sa.Column(
            "invoiceid",
            type_=UUID,
            primary_key=True,
            comment="Unique id",
        ),
        sa.Column(
            "customerid",
            sa.ForeignKey("tenant.id"),
            type_=UUID,
            nullable=False,
            comment="customer id reference",
        ),
        sa.Column(
            "subscriptionid",
            sa.ForeignKey("subscription.id"),
            type_=UUID,
            nullable=False,
            comment="subscription id reference",
        ),
        sa.Column(
            "paymentstatus",
            type_=sa.UnicodeText(),
            comment="status of payment for the invoice",
        ),
        sa.Column(
            "created",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="Creation time of this entry",
        ),
        sa.Column(
            "lastupdated",
            type_=sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
            comment="last updated of this entry",
        ),
        sa.PrimaryKeyConstraint("invoiceid", name="failedinvoices_pkey"),
    )

    conn = op.get_bind()
    product_id = conn.execute(text("SELECT id FROM product WHERE name = 'veritable'")).fetchone()[0]
    plans_data = [
        {
            "plancode": "ee_m_v1",
            "details": json.dumps(plan_details),
            "status": PlanStatus.enterprise.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 3,
            "description": "Enterprise plan",
            "product": product_id,
        },
        {
            "plancode": "lp_m_v1",
            "details": json.dumps(plan_details),
            "status": PlanStatus.legacy.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 2,
            "description": "Upto 250 transactions\n$10 for every additional 75 transactions",
            "product": product_id,
        },
        {
            "plancode": "lp_m_v2",
            "details": json.dumps(plan_details),
            "status": PlanStatus.active.value,
            "marketingtype": MarketingType.popular.value,
            "sortorder": 2,
            "description": "Upto 250 transactions\n$8 for every additional 50 transactions",
            "product": product_id,
        },
        {
            "plancode": "lp_y_v1",
            "details": json.dumps(plan_details),
            "status": PlanStatus.legacy.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 2,
            "description": "Upto 3000 transactions\n$10 for every additional 75 transactions",
            "product": product_id,
        },
        {
            "plancode": "lp_y_v2",
            "details": json.dumps(plan_details),
            "status": PlanStatus.active.value,
            "marketingtype": MarketingType.popular.value,
            "sortorder": 2,
            "description": "Upto 3000 transactions\n$8 for every additional 50 transactions",
            "product": product_id,
        },
        {
            "plancode": "lp_y_v3",
            "details": json.dumps(plan_details),
            "status": PlanStatus.active.value,
            "marketingtype": MarketingType.popular.value,
            "sortorder": 2,
            "description": "Upto 3000 transactions\n$8 for every additional 50 transactions",
            "product": product_id,
        },
        {
            "plancode": "sp_m_v1",
            "details": json.dumps(plan_details),
            "status": PlanStatus.active.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 1,
            "description": "Upto 100 transactions\n$10 for every additional 50 transactions",
            "product": product_id,
        },
        {
            "plancode": "sp_y_v1",
            "details": json.dumps(plan_details),
            "status": PlanStatus.legacy.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 1,
            "description": "Upto 1200 transactions\n$10 for every additional 50 transactions",
            "product": product_id,
        },
        {
            "plancode": "sp_y_v3",
            "details": json.dumps(plan_details),
            "status": PlanStatus.active.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 1,
            "description": "Upto 1200 transactions\n$10 for every additional 50 transactions",
            "product": product_id,
        },
        {
            "plancode": "sp_y_v2",
            "details": json.dumps(plan_details),
            "status": PlanStatus.legacy.value,
            "marketingtype": MarketingType.normal.value,
            "sortorder": 1,
            "description": "Upto 1200 transactions\n$10 for every additional 50 transactions",
            "product": product_id,
        },
    ]

    op.bulk_insert(table=plans, rows=plans_data)

    features_data = [
        {
            "featurecode": VeritableFeature.default.value,
            "description": "",
            "details": "[]",
            "status": FeatureStatus.active.value,
            "sortorder": 1,
            "marketingtype": MarketingType.normal.value,
            "product": product_id,
        },
        {
            "featurecode": VeritableFeature.payments.value,
            "description": payment_feature_description,
            "details": json.dumps(payment_feature_details),
            "status": FeatureStatus.active.value,
            "sortorder": 2,
            "marketingtype": MarketingType.normal.value,
            "product": product_id,
        },
    ]

    op.bulk_insert(table=features, rows=features_data)

    planfeatures_data = [
        {
            "plancode": "sp_m_v1",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 100}),
        },
        {
            "plancode": "lp_m_v1",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 250}),
        },
        {
            "plancode": "lp_y_v1",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 3000}),
        },
        {
            "plancode": "lp_y_v3",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 3000}),
        },
        {
            "plancode": "sp_y_v2",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 1200}),
        },
        {
            "plancode": "ee_m_v1",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "sp_y_v1",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 1200}),
        },
        {
            "plancode": "lp_m_v2",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 250}),
        },
        {
            "plancode": "lp_y_v2",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 3000}),
        },
        {
            "plancode": "sp_m_v1",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "lp_y_v3",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "sp_y_v2",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "lp_m_v2",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "lp_m_v1",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "lp_y_v1",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "lp_y_v2",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "sp_y_v1",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "sp_y_v3",
            "featurecode": VeritableFeature.payments.value,
            "cansubscribe": True,
            "isincluded": False,
            "softlimits": json.dumps({}),
        },
        {
            "plancode": "sp_y_v3",
            "featurecode": VeritableFeature.default.value,
            "cansubscribe": False,
            "isincluded": True,
            "softlimits": json.dumps({"count": 1200}),
        },
    ]

    op.bulk_insert(table=planfeatures, rows=planfeatures_data)


def downgrade(**kwargs: str | Callable) -> None:
    """
    Downgrade function
    """
    op.drop_table("failedinvoices")
    op.drop_table("userevent")
    op.drop_table("subscription")
    op.drop_table("planfeatures")
    op.drop_table("features")
    op.drop_table("plans")
    op.drop_column("tenant", "email")
    op.drop_column("tenant", "setupintent")
