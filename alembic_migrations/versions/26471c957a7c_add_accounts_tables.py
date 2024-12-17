"""add accounts tables

Revision ID: 26471c957a7c
Revises: b7144993b2b1
Create Date: 2024-12-17 16:01:11.843191

"""

from collections.abc import Callable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "26471c957a7c"
down_revision = "b7144993b2b1"
branch_labels = None
depends_on = None


def upgrade(**kwargs: str | Callable) -> None:
    """
    Upgrade function
    """
    op.add_column("tenant", sa.Column("setupintent", type_=sa.UnicodeText(), comment="payment method setup intent"))
    op.add_column("tenant", sa.Column("email", type_=sa.UnicodeText(), nullable=True))
    op.create_unique_constraint("tenant_product_email_unique_idx", "tenant", ["name", "product", "email"])

    # plans
    op.create_table(
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
        sa.UniqueConstraint("plancode", name="plans_pkey"),
    )

    # features
    op.create_table(
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
        sa.UniqueConstraint("featurecode", name="features_pkey"),
    )

    # planfeatures
    op.create_table(
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
    op.drop_constraint("tenant_product_email_unique_idx", "tenant", type_="unique")
