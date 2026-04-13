"""Add ontology_property table

Revision ID: 0001
Revises:
Create Date: 2026-04-13

Stores OWL object properties (with domain/range) extracted during ontology
import.  The table may already exist on installations where the application
was started after the schema change was introduced (SQLModel's create_all
creates it automatically for brand-new databases).  The upgrade therefore
checks for existence before creating, making it safe to run in both cases.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ontology_property" not in inspector.get_table_names():
        op.create_table(
            "ontology_property",
            sa.Column("property_id", sa.Integer(), nullable=False),
            sa.Column("ontology_id", sa.Integer(), nullable=False),
            sa.Column("curie", sa.String(), nullable=False),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("domain_curie", sa.String(), nullable=True),
            sa.Column("range_curie", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["ontology_id"], ["ontology.ontology_id"]),
            sa.PrimaryKeyConstraint("property_id"),
            sa.UniqueConstraint("ontology_id", "curie"),
        )
        op.create_index(
            "ix_ontology_property_ontology_id",
            "ontology_property",
            ["ontology_id"],
        )
        op.create_index(
            "ix_ontology_property_curie",
            "ontology_property",
            ["curie"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ontology_property" in inspector.get_table_names():
        op.drop_index("ix_ontology_property_curie", table_name="ontology_property")
        op.drop_index(
            "ix_ontology_property_ontology_id", table_name="ontology_property"
        )
        op.drop_table("ontology_property")
