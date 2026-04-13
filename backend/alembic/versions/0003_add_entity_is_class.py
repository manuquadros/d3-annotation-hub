"""Add is_class column to entity table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entity",
        sa.Column("is_class", sa.Boolean(), nullable=False, server_default="0"),
    )
    # Backfill: all currently confirmed entities were loaded from OWL and are classes.
    # Unconfirmed entities are annotator-proposed individuals.
    op.execute("UPDATE entity SET is_class = 1 WHERE confirmed = 1")
    op.create_index("ix_entity_is_class", "entity", ["is_class"])


def downgrade() -> None:
    op.drop_index("ix_entity_is_class", table_name="entity")
    op.drop_column("entity", "is_class")
