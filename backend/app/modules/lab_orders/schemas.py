"""Pydantic schemas for lab_orders."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WorkType = Literal[
    "crown", "bridge", "denture", "implant", "veneer", "orthodontic", "repair", "other"
]
OrderStatus = Literal["sent", "in_progress", "try_in", "ready", "received", "cancelled"]
# Statuses a technician may move an order *to* from the workbench. Receipt
# and cancellation stay with the clinic (lab_orders.write).
TechnicianStatus = Literal["in_progress", "try_in", "ready"]
EventKind = Literal["status", "comment", "assigned"]
ImpressionType = Literal["alginate", "pvs_silicone", "digital_scan", "other"]
ShadeSelection = Literal[
    "A1",
    "A2",
    "A3",
    "A3.5",
    "A4",
    "B1",
    "B2",
    "B3",
    "B4",
    "C1",
    "C2",
    "C3",
    "C4",
    "D2",
    "D3",
    "D4",
]


class LabOrderCreate(BaseModel):
    patient_id: UUID
    lab_contact_id: UUID
    work_type: WorkType
    tooth_reference: str | None = Field(default=None, max_length=50)
    impression_type: ImpressionType | None = None
    antagonist_info: str | None = Field(default=None, max_length=500)
    shade: ShadeSelection | None = None
    sent_date: date
    expected_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class LabOrderUpdate(BaseModel):
    lab_contact_id: UUID | None = None
    work_type: WorkType | None = None
    tooth_reference: str | None = Field(default=None, max_length=50)
    impression_type: ImpressionType | None = None
    antagonist_info: str | None = Field(default=None, max_length=500)
    shade: ShadeSelection | None = None
    status: OrderStatus | None = None
    expected_date: date | None = None
    received_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class LabOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    patient_name: str
    lab_contact_id: UUID
    lab_contact_name: str
    work_type: WorkType
    tooth_reference: str | None
    impression_type: ImpressionType | None
    antagonist_info: str | None
    shade: ShadeSelection | None
    status: OrderStatus
    sent_date: date
    expected_date: date | None
    received_date: date | None
    notes: str | None
    created_by: UUID | None
    technician_id: UUID | None = None
    technician_name: str | None = None
    created_at: datetime
    updated_at: datetime


class LabOrderTransition(BaseModel):
    """Technician workbench move; an optional comment travels with it."""

    status: TechnicianStatus
    comment: str | None = Field(default=None, max_length=2000)


class LabOrderCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class LabOrderEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    author_id: UUID | None
    author_name: str | None
    kind: EventKind
    from_status: OrderStatus | None
    to_status: OrderStatus | None
    body: str | None
    created_at: datetime
