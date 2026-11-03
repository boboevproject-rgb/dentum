"""Technician workbench: lab workflow state machine, shared thread, RBAC."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.models import Clinic, ClinicMembership, User
from app.modules.contacts.models import Contact
from app.modules.lab_orders.models import LabOrder
from app.modules.lab_orders.schemas import LabOrderCreate, LabOrderUpdate
from app.modules.lab_orders.service import LabOrderService
from app.modules.patients.models import Patient


@pytest_asyncio.fixture
async def role_user(db_session: AsyncSession, test_clinic: Clinic):
    """Factory: (user, auth headers) for a fresh member with the given role."""
    from app.core.auth.service import create_access_token, hash_password

    async def _make(role: str) -> tuple[User, dict[str, str]]:
        user = User(
            email=f"{role}-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass1234"),
            first_name=role.title(),
            last_name="Test",
        )
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            ClinicMembership(id=uuid4(), user_id=user.id, clinic_id=test_clinic.id, role=role)
        )
        await db_session.commit()
        token = create_access_token(user.id, token_version=user.token_version)
        return user, {"Authorization": f"Bearer {token}"}

    return _make


@pytest_asyncio.fixture
async def lab_order(
    db_session: AsyncSession, test_clinic: Clinic, test_patient: Patient
) -> LabOrder:
    contact = Contact(clinic_id=test_clinic.id, name="Lab", contact_type="lab", is_active=True)
    db_session.add(contact)
    await db_session.commit()
    return await LabOrderService.create_order(
        db_session,
        test_clinic.id,
        LabOrderCreate(
            patient_id=test_patient.id,
            lab_contact_id=contact.id,
            work_type="crown",
            sent_date=date(2026, 10, 1),
            expected_date=date(2026, 10, 8),
        ),
        None,
    )


@pytest.mark.asyncio
async def test_workflow_assigns_logs_and_rejects_jumps(
    db_session: AsyncSession, test_clinic: Clinic, lab_order: LabOrder, role_user
):
    tech, _ = await role_user("technician")

    with pytest.raises(HTTPException) as exc:
        await LabOrderService.transition(db_session, test_clinic.id, lab_order.id, "ready", tech.id)
    assert exc.value.status_code == 409

    order = await LabOrderService.transition(
        db_session, test_clinic.id, lab_order.id, "in_progress", tech.id, "Model cast"
    )
    assert order.status == "in_progress"
    assert order.technician_id == tech.id

    order = await LabOrderService.transition(
        db_session, test_clinic.id, order.id, "try_in", tech.id
    )
    order = await LabOrderService.transition(db_session, test_clinic.id, order.id, "ready", tech.id)
    assert order.status == "ready"

    events = await LabOrderService.list_events(db_session, test_clinic.id, order.id)
    kinds = [(e["kind"], e["from_status"], e["to_status"]) for e in events]
    assert kinds == [
        ("status", None, "sent"),
        ("assigned", None, None),
        ("status", "sent", "in_progress"),
        ("comment", None, None),
        ("status", "in_progress", "try_in"),
        ("status", "try_in", "ready"),
    ]
    assert events[3]["body"] == "Model cast"
    assert events[2]["author_name"] == "Technician Test"

    counts = await LabOrderService.status_counts(db_session, test_clinic.id, tech.id)
    assert counts == {"ready": 1}

    # Clinic receives the order through the regular PATCH; it is then out
    # of the technician's hands.
    order = await LabOrderService.update_order(
        db_session, test_clinic.id, order.id, LabOrderUpdate(status="received")
    )
    with pytest.raises(HTTPException) as exc:
        await LabOrderService.transition(
            db_session, test_clinic.id, order.id, "in_progress", tech.id
        )
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        await LabOrderService.assign(db_session, test_clinic.id, order.id, tech.id)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_list_filters_by_statuses_and_technician(
    db_session: AsyncSession, test_clinic: Clinic, lab_order: LabOrder, role_user
):
    tech, _ = await role_user("technician")
    rows, total = await LabOrderService.list_order_responses(
        db_session, test_clinic.id, statuses=["in_progress"]
    )
    assert total == 0
    await LabOrderService.transition(
        db_session, test_clinic.id, lab_order.id, "in_progress", tech.id
    )
    rows, total = await LabOrderService.list_order_responses(
        db_session, test_clinic.id, statuses=["sent", "in_progress"], technician_id=tech.id
    )
    assert total == 1
    assert rows[0]["technician_name"] == "Technician Test"


@pytest.mark.asyncio
async def test_http_rbac_technician_vs_clinic(client: AsyncClient, lab_order: LabOrder, role_user):
    _, tech = await role_user("technician")
    _, dentist = await role_user("dentist")
    _, hygienist = await role_user("hygienist")
    base = f"/api/v1/lab_orders/{lab_order.id}"

    # Technician: works and comments, never edits/creates.
    r = await client.post(f"{base}/transition", json={"status": "in_progress"}, headers=tech)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["technician_name"]
    r = await client.post(f"{base}/comments", json={"body": "Need a new scan"}, headers=tech)
    assert r.status_code == 201
    assert (await client.patch(base, json={"status": "received"}, headers=tech)).status_code == 403

    # Dentist: same thread, comments, cannot drive the lab workflow.
    r = await client.get(f"{base}/events", headers=dentist)
    assert r.status_code == 200
    assert [e["kind"] for e in r.json()["data"]][-1] == "comment"
    assert (
        await client.post(f"{base}/comments", json={"body": "Sent"}, headers=dentist)
    ).status_code == 201
    r = await client.post(f"{base}/transition", json={"status": "ready"}, headers=dentist)
    assert r.status_code == 403

    # Hygienist: read only.
    assert (await client.get("/api/v1/lab_orders/stats", headers=hygienist)).status_code == 200
    r = await client.post(f"{base}/comments", json={"body": "x"}, headers=hygienist)
    assert r.status_code == 403
