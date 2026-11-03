"""lab_orders: technician assignment and order history (technician workbench)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "labo_0003"
down_revision: str | None = "labo_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("lab_orders", sa.Column("technician_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_lab_orders_technician_id_users", "lab_orders", "users", ["technician_id"], ["id"]
    )
    op.create_index("ix_lab_orders_technician_id", "lab_orders", ["technician_id"])

    op.create_table(
        "lab_order_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["lab_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_order_events_clinic_id", "lab_order_events", ["clinic_id"])
    op.create_index("ix_lab_order_events_order_id", "lab_order_events", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_lab_order_events_order_id", table_name="lab_order_events")
    op.drop_index("ix_lab_order_events_clinic_id", table_name="lab_order_events")
    op.drop_table("lab_order_events")
    op.drop_index("ix_lab_orders_technician_id", table_name="lab_orders")
    op.drop_constraint("fk_lab_orders_technician_id_users", "lab_orders", type_="foreignkey")
    op.drop_column("lab_orders", "technician_id")
