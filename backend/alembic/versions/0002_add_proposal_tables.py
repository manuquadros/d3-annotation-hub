"""Add proposed_entity and proposed_property tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()

    if "proposed_entity" not in existing:
        op.create_table(
            "proposed_entity",
            sa.Column("proposal_id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, sa.ForeignKey("project.project_id"), nullable=False, index=True),
            sa.Column("label", sa.Text, nullable=False),
            sa.Column("curie", sa.Text, nullable=False),
            sa.Column("kind", sa.Text, nullable=False),
            sa.Column("proposed_by", sa.Text, nullable=True),
            sa.Column("status", sa.Text, nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("project_id", "curie", name="uq_proposed_entity_project_curie"),
        )

    if "proposed_property" not in existing:
        op.create_table(
            "proposed_property",
            sa.Column("proposal_id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, sa.ForeignKey("project.project_id"), nullable=False, index=True),
            sa.Column("label", sa.Text, nullable=False),
            sa.Column("curie", sa.Text, nullable=True),
            sa.Column("domain_curie", sa.Text, nullable=True),
            sa.Column("range_curie", sa.Text, nullable=True),
            sa.Column("proposed_by", sa.Text, nullable=True),
            sa.Column("status", sa.Text, nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()

    if "proposed_property" in existing:
        op.drop_table("proposed_property")
    if "proposed_entity" in existing:
        op.drop_table("proposed_entity")
