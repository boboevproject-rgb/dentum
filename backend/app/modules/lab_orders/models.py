"""SQLAlchemy models for lab work orders and their history."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class LabOrder(Base, TimestampMixin):
    """Work sent to an external laboratory for a specific patient."""

    __tablename__ = "lab_orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("clinics.id"), index=True, nullable=False)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    lab_contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id"), index=True, nullable=False
    )

    work_type: Mapped[str] = mapped_column(String(20), index=True)
    tooth_reference: Mapped[str | None] = mapped_column(String(50))
    impression_type: Mapped[str | None] = mapped_column(String(20))
    antagonist_info: Mapped[str | None] = mapped_column(String(500))
    shade: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), index=True, default="sent")

    sent_date: Mapped[date] = mapped_column(Date)
    expected_date: Mapped[date | None] = mapped_column(Date)
    received_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    # Dental technician who took the order into work (technician workbench).
    technician_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)


class LabOrderEvent(Base):
    """Append-only history of an order: status changes and comments.

    Both sides of the order write here — clinic staff from the lab orders
    list, the technician from the workbench — so each sees the other's
    changes and messages on the same timeline.
    """

    __tablename__ = "lab_order_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(ForeignKey("clinics.id"), index=True, nullable=False)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("lab_orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))  # status | comment | assigned
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
