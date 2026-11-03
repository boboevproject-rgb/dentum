"""Demo data for the lab orders module and the technician workbench.

Seeds one in-house lab contact and a handful of orders spread across the
lab workflow, with the conversation between the clinic and the dental
technician on each order's timeline. Idempotent: does nothing when the
clinic already has lab orders.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contacts.models import Contact

from .models import LabOrder, LabOrderEvent

# (patient index, work_type, tooth, shade, impression, status, days ago sent,
#  days until due, assigned to technician, thread)
# thread: list of (author, kind, from, to, body) with author in {"dentist", "tech"}
_ORDERS = [
    (
        0,
        "crown",
        "36",
        "A2",
        "digital_scan",
        "sent",
        1,
        6,
        False,
        [
            (
                "dentist",
                "comment",
                None,
                None,
                "Metal-ceramic crown on 36, shoulder preparation. Please keep the occlusal contact light.",
            ),
        ],
    ),
    (
        1,
        "bridge",
        "14-16",
        "A3",
        "pvs_silicone",
        "in_progress",
        4,
        3,
        True,
        [
            ("tech", "status", "sent", "in_progress", None),
            (
                "tech",
                "comment",
                None,
                None,
                "Model is cast. The distal margin on 16 is not clear, please confirm the finish line.",
            ),
            ("dentist", "comment", None, None, "Finish line is 0.5 mm subgingival, see the scan."),
        ],
    ),
    (
        2,
        "veneer",
        "11, 21",
        "B1",
        "digital_scan",
        "try_in",
        7,
        2,
        True,
        [
            ("tech", "status", "sent", "in_progress", None),
            ("tech", "status", "in_progress", "try_in", None),
            (
                "tech",
                "comment",
                None,
                None,
                "Wax-up sent for try-in. Waiting for the patient's feedback.",
            ),
        ],
    ),
    (
        3,
        "denture",
        "Upper arch",
        None,
        "alginate",
        "ready",
        10,
        -1,
        True,
        [
            ("tech", "status", "sent", "in_progress", None),
            ("tech", "status", "in_progress", "ready", None),
            (
                "tech",
                "comment",
                None,
                None,
                "Denture is finished and packed. Can be collected today.",
            ),
        ],
    ),
    (
        4,
        "implant",
        "46",
        "A3.5",
        "digital_scan",
        "received",
        20,
        -8,
        True,
        [
            ("tech", "status", "sent", "in_progress", None),
            ("tech", "status", "in_progress", "ready", None),
            ("dentist", "status", "ready", "received", None),
        ],
    ),
    (
        5,
        "repair",
        "Lower denture",
        None,
        None,
        "in_progress",
        2,
        -1,
        True,
        [
            ("tech", "status", "sent", "in_progress", None),
        ],
    ),
]


async def seed_lab_orders_demo(
    db: AsyncSession,
    clinic_id: UUID,
    patient_ids: list[UUID],
    dentist_id: UUID,
    technician_id: UUID,
    today: date | None = None,
) -> dict[str, int]:
    existing = (
        await db.execute(select(func.count()).where(LabOrder.clinic_id == clinic_id))
    ).scalar_one()
    if existing:
        return {"orders": 0, "events": 0}

    lab = (
        (
            await db.execute(
                select(Contact).where(Contact.clinic_id == clinic_id, Contact.contact_type == "lab")
            )
        )
        .scalars()
        .first()
    )
    if lab is None:
        lab = Contact(
            clinic_id=clinic_id,
            name="In-house dental lab",
            contact_type="lab",
            phone="+1 212 555 0199",
            email="lab@demo.clinic",
            is_active=True,
        )
        db.add(lab)
        await db.flush()

    today = today or date.today()
    authors = {"dentist": dentist_id, "tech": technician_id}
    n_events = 0
    for idx, work, tooth, shade, impression, status, ago, due, assigned, thread in _ORDERS:
        sent = today - timedelta(days=ago)
        order = LabOrder(
            clinic_id=clinic_id,
            patient_id=patient_ids[idx % len(patient_ids)],
            lab_contact_id=lab.id,
            work_type=work,
            tooth_reference=tooth,
            shade=shade,
            impression_type=impression,
            status=status,
            sent_date=sent,
            expected_date=today + timedelta(days=due),
            received_date=today - timedelta(days=2) if status == "received" else None,
            created_by=dentist_id,
            technician_id=technician_id if assigned else None,
        )
        db.add(order)
        await db.flush()
        stamp = datetime.combine(sent, datetime.min.time(), tzinfo=UTC) + timedelta(hours=9)
        db.add(
            LabOrderEvent(
                clinic_id=clinic_id,
                order_id=order.id,
                author_id=dentist_id,
                kind="status",
                to_status="sent",
                created_at=stamp,
            )
        )
        for step, (who, kind, frm, to, body) in enumerate(thread, start=1):
            db.add(
                LabOrderEvent(
                    clinic_id=clinic_id,
                    order_id=order.id,
                    author_id=authors[who],
                    kind=kind,
                    from_status=frm,
                    to_status=to,
                    body=body,
                    created_at=stamp + timedelta(hours=5 * step),
                )
            )
        n_events += 1 + len(thread)
    await db.flush()
    return {"orders": len(_ORDERS), "events": n_events}
