"""Business logic for lab work orders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from fastapi import status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.models import User
from app.core.events import event_bus
from app.core.events.types import EventType
from app.core.utils.dates import clinic_today_for
from app.modules.contacts.models import Contact
from app.modules.patients.models import Patient

from .models import LabOrder, LabOrderEvent
from .schemas import LabOrderCreate, LabOrderUpdate

# Technician workbench state machine: from-status -> statuses the
# technician may move the order to. ``received`` / ``cancelled`` are
# clinic decisions and only reachable through PATCH (lab_orders.write).
TECHNICIAN_TRANSITIONS: dict[str, frozenset[str]] = {
    "sent": frozenset({"in_progress"}),
    "in_progress": frozenset({"try_in", "ready"}),
    "try_in": frozenset({"in_progress", "ready"}),
    "ready": frozenset({"in_progress"}),
}

_last_event_stamp = datetime.min.replace(tzinfo=UTC)


def _event_stamp() -> datetime:
    """Strictly increasing timestamp for thread rows.

    ``server_default=now()`` is the *transaction* start, so a status move
    and the comment attached to it would tie and the thread would order
    them by random UUID. Stamp from the app clock and never repeat.
    """
    global _last_event_stamp
    now = datetime.now(UTC)
    if now <= _last_event_stamp:
        now = _last_event_stamp + timedelta(microseconds=1)
    _last_event_stamp = now
    return now


def _response_dict(
    order: LabOrder, patient_name: str, lab_name: str, technician_name: str | None
) -> dict:
    return {
        "id": order.id,
        "clinic_id": order.clinic_id,
        "patient_id": order.patient_id,
        "patient_name": patient_name,
        "lab_contact_id": order.lab_contact_id,
        "lab_contact_name": lab_name,
        "work_type": order.work_type,
        "tooth_reference": order.tooth_reference,
        "impression_type": order.impression_type,
        "antagonist_info": order.antagonist_info,
        "shade": order.shade,
        "status": order.status,
        "sent_date": order.sent_date,
        "expected_date": order.expected_date,
        "received_date": order.received_date,
        "notes": order.notes,
        "created_by": order.created_by,
        "technician_id": order.technician_id,
        "technician_name": technician_name,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


async def _user_names(db: AsyncSession, user_ids: set[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    users = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    return {user.id: user.full_name for user in users}


class LabOrderService:
    @staticmethod
    async def _assert_patient(db: AsyncSession, clinic_id: UUID, patient_id: UUID) -> None:
        stmt = select(Patient.id).where(Patient.id == patient_id, Patient.clinic_id == clinic_id)
        if (await db.execute(stmt)).scalar_one_or_none() is None:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                "patient_id does not match a patient in this clinic",
            )

    @staticmethod
    async def _assert_contact(db: AsyncSession, clinic_id: UUID, contact_id: UUID) -> None:
        stmt = select(Contact.id).where(Contact.id == contact_id, Contact.clinic_id == clinic_id)
        if (await db.execute(stmt)).scalar_one_or_none() is None:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                "lab_contact_id does not match a contact in this clinic",
            )

    @staticmethod
    async def _enrich(db: AsyncSession, clinic_id: UUID, orders: list[LabOrder]) -> list[dict]:
        if not orders:
            return []
        patient_ids = {order.patient_id for order in orders}
        contact_ids = {order.lab_contact_id for order in orders}
        patients = (
            (
                await db.execute(
                    select(Patient).where(
                        Patient.id.in_(patient_ids), Patient.clinic_id == clinic_id
                    )
                )
            )
            .scalars()
            .all()
        )
        contacts = (
            (
                await db.execute(
                    select(Contact).where(
                        Contact.id.in_(contact_ids), Contact.clinic_id == clinic_id
                    )
                )
            )
            .scalars()
            .all()
        )
        technicians = await _user_names(
            db, {order.technician_id for order in orders if order.technician_id}
        )
        patient_names = {patient.id: patient.full_name for patient in patients}
        contact_names = {contact.id: contact.name for contact in contacts}
        return [
            _response_dict(
                order,
                patient_names.get(order.patient_id, "—"),
                contact_names.get(order.lab_contact_id, "—"),
                technicians.get(order.technician_id) if order.technician_id else None,
            )
            for order in orders
        ]

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        clinic_id: UUID,
        patient_id: UUID | None = None,
        lab_contact_id: UUID | None = None,
        order_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        statuses: list[str] | None = None,
        technician_id: UUID | None = None,
    ) -> tuple[list[LabOrder], int]:
        stmt = select(LabOrder).where(LabOrder.clinic_id == clinic_id)
        if patient_id:
            stmt = stmt.where(LabOrder.patient_id == patient_id)
        if lab_contact_id:
            stmt = stmt.where(LabOrder.lab_contact_id == lab_contact_id)
        if order_status:
            stmt = stmt.where(LabOrder.status == order_status)
        if statuses:
            stmt = stmt.where(LabOrder.status.in_(statuses))
        if technician_id:
            stmt = stmt.where(LabOrder.technician_id == technician_id)
        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            (
                await db.execute(
                    stmt.order_by(LabOrder.sent_date.desc(), LabOrder.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    @staticmethod
    async def list_order_responses(
        db: AsyncSession,
        clinic_id: UUID,
        patient_id: UUID | None = None,
        lab_contact_id: UUID | None = None,
        order_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        statuses: list[str] | None = None,
        technician_id: UUID | None = None,
    ) -> tuple[list[dict], int]:
        orders, total = await LabOrderService.list_orders(
            db,
            clinic_id,
            patient_id,
            lab_contact_id,
            order_status,
            page,
            page_size,
            statuses,
            technician_id,
        )
        return await LabOrderService._enrich(db, clinic_id, orders), total

    @staticmethod
    async def get_order(db: AsyncSession, clinic_id: UUID, order_id: UUID) -> LabOrder:
        stmt = select(LabOrder).where(LabOrder.id == order_id, LabOrder.clinic_id == clinic_id)
        order = (await db.execute(stmt)).scalar_one_or_none()
        if order is None:
            raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Lab order not found")
        return order

    @staticmethod
    async def get_order_response(db: AsyncSession, clinic_id: UUID, order_id: UUID) -> dict:
        order = await LabOrderService.get_order(db, clinic_id, order_id)
        return (await LabOrderService._enrich(db, clinic_id, [order]))[0]

    @staticmethod
    def _record(
        db: AsyncSession,
        order: LabOrder,
        author_id: UUID | None,
        kind: str,
        *,
        from_status: str | None = None,
        to_status: str | None = None,
        body: str | None = None,
    ) -> None:
        db.add(
            LabOrderEvent(
                clinic_id=order.clinic_id,
                order_id=order.id,
                author_id=author_id,
                kind=kind,
                from_status=from_status,
                to_status=to_status,
                body=body,
                created_at=_event_stamp(),
            )
        )

    @staticmethod
    async def create_order(
        db: AsyncSession, clinic_id: UUID, payload: LabOrderCreate, created_by: UUID | None
    ) -> LabOrder:
        await LabOrderService._assert_patient(db, clinic_id, payload.patient_id)
        await LabOrderService._assert_contact(db, clinic_id, payload.lab_contact_id)
        order = LabOrder(
            clinic_id=clinic_id, created_by=created_by, status="sent", **payload.model_dump()
        )
        db.add(order)
        await db.flush()
        LabOrderService._record(db, order, created_by, "status", to_status="sent")
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def _apply_status(
        db: AsyncSession, order: LabOrder, new_status: str, actor_id: UUID | None
    ) -> None:
        """Set ``order.status`` and log + publish the transition (no commit)."""
        old_status = order.status
        if old_status == new_status:
            return
        order.status = new_status
        LabOrderService._record(
            db, order, actor_id, "status", from_status=old_status, to_status=new_status
        )
        await db.flush()
        # ADR 0019 — publish *inside* the transaction with the publisher's
        # session so transactional subscribers see the updated row and roll
        # back with it; the caller owns the commit.
        await event_bus.publish(
            EventType.LAB_ORDER_STATUS_CHANGED,
            {
                "clinic_id": str(order.clinic_id),
                "order_id": str(order.id),
                "patient_id": str(order.patient_id),
                "status": order.status,
                "work_type": order.work_type,
                "tooth_reference": order.tooth_reference,
            },
            db=db,
        )

    @staticmethod
    async def update_order(
        db: AsyncSession,
        clinic_id: UUID,
        order_id: UUID,
        payload: LabOrderUpdate,
        actor_id: UUID | None = None,
    ) -> LabOrder:
        order = await LabOrderService.get_order(db, clinic_id, order_id)
        if payload.lab_contact_id is not None:
            await LabOrderService._assert_contact(db, clinic_id, payload.lab_contact_id)
        data = payload.model_dump(exclude_unset=True)
        new_status = data.pop("status", None)
        # Stamp only on the transition *into* received — a repeated PATCH
        # with status=received must not overwrite the original receipt date.
        if new_status == "received" and "received_date" not in data and order.status != "received":
            data["received_date"] = await clinic_today_for(db, clinic_id)
        for field, value in data.items():
            setattr(order, field, value)
        if new_status is not None:
            await LabOrderService._apply_status(db, order, new_status, actor_id)
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def transition(
        db: AsyncSession,
        clinic_id: UUID,
        order_id: UUID,
        new_status: str,
        actor_id: UUID,
        comment: str | None = None,
    ) -> LabOrder:
        """Technician workbench move along :data:`TECHNICIAN_TRANSITIONS`.

        Taking a ``sent`` order into work assigns it to the acting
        technician when nobody holds it yet.
        """
        order = await LabOrderService.get_order(db, clinic_id, order_id)
        allowed = TECHNICIAN_TRANSITIONS.get(order.status, frozenset())
        if new_status not in allowed:
            raise HTTPException(
                http_status.HTTP_409_CONFLICT,
                f"Cannot move a lab order from '{order.status}' to '{new_status}'",
            )
        if order.technician_id is None:
            order.technician_id = actor_id
            LabOrderService._record(db, order, actor_id, "assigned")
        await LabOrderService._apply_status(db, order, new_status, actor_id)
        if comment and comment.strip():
            LabOrderService._record(db, order, actor_id, "comment", body=comment.strip())
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def assign(
        db: AsyncSession, clinic_id: UUID, order_id: UUID, technician_id: UUID
    ) -> LabOrder:
        """The acting technician takes over an order (without moving it)."""
        order = await LabOrderService.get_order(db, clinic_id, order_id)
        if order.status in ("received", "cancelled"):
            raise HTTPException(http_status.HTTP_409_CONFLICT, "Lab order is closed")
        if order.technician_id != technician_id:
            order.technician_id = technician_id
            LabOrderService._record(db, order, technician_id, "assigned")
            await db.commit()
            await db.refresh(order)
        return order

    @staticmethod
    async def add_comment(
        db: AsyncSession, clinic_id: UUID, order_id: UUID, author_id: UUID, body: str
    ) -> LabOrderEvent:
        order = await LabOrderService.get_order(db, clinic_id, order_id)
        text = body.strip()
        if not text:
            raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, "Comment is empty")
        event = LabOrderEvent(
            clinic_id=clinic_id, order_id=order.id, author_id=author_id, kind="comment", body=text
        )
        db.add(event)
        # Touch the order so "recently updated" sorts surface new messages.
        order.updated_at = func.now()
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def list_events(db: AsyncSession, clinic_id: UUID, order_id: UUID) -> list[dict]:
        await LabOrderService.get_order(db, clinic_id, order_id)
        events = (
            (
                await db.execute(
                    select(LabOrderEvent)
                    .where(LabOrderEvent.order_id == order_id, LabOrderEvent.clinic_id == clinic_id)
                    .order_by(LabOrderEvent.created_at, LabOrderEvent.id)
                )
            )
            .scalars()
            .all()
        )
        names = await _user_names(db, {e.author_id for e in events if e.author_id})
        return [
            {
                "id": e.id,
                "order_id": e.order_id,
                "author_id": e.author_id,
                "author_name": names.get(e.author_id) if e.author_id else None,
                "kind": e.kind,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "body": e.body,
                "created_at": e.created_at,
            }
            for e in events
        ]

    @staticmethod
    async def status_counts(
        db: AsyncSession, clinic_id: UUID, technician_id: UUID | None = None
    ) -> dict[str, int]:
        stmt = (
            select(LabOrder.status, func.count())
            .where(LabOrder.clinic_id == clinic_id)
            .group_by(LabOrder.status)
        )
        if technician_id:
            stmt = stmt.where(LabOrder.technician_id == technician_id)
        return {row[0]: row[1] for row in (await db.execute(stmt)).all()}
