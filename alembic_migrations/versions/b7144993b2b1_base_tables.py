"""base tables

Revision ID: b7144993b2b1
Revises:
Create Date: 2024-12-17 13:48:34.741517

"""

from collections.abc import Callable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "b7144993b2b1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(**kwargs: str | Callable) -> None:
    """
    Upgrade function
    """
    op.create_table(
        "product",
        sa.Column("id", type_=UUID, primary_key=True, server_default=sa.text("uuid_generate_v1mc()")),
        sa.Column("name", type_=sa.UnicodeText(), nullable=False),
        sa.Column("schema", type_=JSONB),
        sa.Column("created", type_=sa.TIMESTAMP),
        sa.Column("updated", type_=sa.TIMESTAMP),
        sa.Column("approvalRequired", type_=sa.Boolean(), nullable=False, default=False),
        if_not_exists=True,
    )

    op.create_table(
        "tenant",
        sa.Column("id", type_=UUID, primary_key=True, server_default=sa.text("uuid_generate_v1mc()")),
        sa.Column("name", type_=sa.UnicodeText(), nullable=False),
        sa.Column("product", sa.ForeignKey("product.id"), type_=UUID, nullable=False),
        sa.Column("status", type_=sa.UnicodeText()),
        sa.Column("errors", type_=sa.UnicodeText()),
        sa.Column("provisioneddatetime", type_=sa.DateTime()),
        sa.Column("source", type_=sa.UnicodeText()),
        sa.Column("approvedby", type_=UUID),
        sa.Column("created", type_=sa.TIMESTAMP, server_default=sa.text("now()")),
        sa.Column("schema", type_=JSONB),
        sa.UniqueConstraint("name", "product", name="tenant_name_product_unique_idx"),
        if_not_exists=True,
    )

    op.create_table(
        "email_templates",
        sa.Column("id", type_=UUID, primary_key=True, server_default=sa.text("uuid_generate_v1mc()")),
        sa.Column("name", type_=sa.UnicodeText(), nullable=False),
        sa.Column("product", sa.ForeignKey("product.id"), type_=UUID, nullable=False),
        sa.Column("template", type_=sa.UnicodeText()),
        sa.Column("subject", type_=sa.UnicodeText()),
        sa.UniqueConstraint("name", "product", name="email_templates_name_product_unique_idx"),
        if_not_exists=True,
    )


def downgrade(**kwargs: str | Callable) -> None:
    """
    Downgrade function
    """
    op.drop_table("email_template")
    op.drop_table("tenant")
    op.drop_table("product")
