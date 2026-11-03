"""HTTP routes for lab orders."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import ClinicContext, get_clinic_context, require_permission
from app.core.schemas import ApiResponse, PaginatedApiResponse
from app.database import get_db

from .schemas import (
    LabOrderCommentCreate,
    LabOrderCreate,
    LabOrderEventResponse,
    LabOrderResponse,
    LabOrderTransition,
    LabOrderUpdate,
)
from .service import LabOrderService

router = APIRouter()


@router.get("/", response_model=PaginatedApiResponse[LabOrderResponse])
async def list_lab_orders(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    patient_id: UUID | None = Query(default=None),
    lab_contact_id: UUID | None = Query(default=None),
    order_status: str | None = Query(default=None),
    statuses: str | None = Query(
        default=None, description="Comma-separated statuses, e.g. sent,in_progress"
    ),
    technician_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedApiResponse[LabOrderResponse]:
    status_list = [s.strip() for s in statuses.split(",") if s.strip()] if statuses else None
    orders, total = await LabOrderService.list_order_responses(
        db,
        ctx.clinic_id,
        patient_id,
        lab_contact_id,
        order_status,
        page,
        page_size,
        status_list,
        technician_id,
    )
    return PaginatedApiResponse(
        data=[LabOrderResponse.model_validate(order) for order in orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=ApiResponse[dict[str, int]])
async def lab_order_stats(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    technician_id: UUID | None = Query(default=None),
) -> ApiResponse[dict[str, int]]:
    """Order count per status (optionally for one technician)."""
    return ApiResponse(data=await LabOrderService.status_counts(db, ctx.clinic_id, technician_id))


@router.get("/{order_id}", response_model=ApiResponse[LabOrderResponse])
async def get_lab_order(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    order_id: UUID,
) -> ApiResponse[LabOrderResponse]:
    order = await LabOrderService.get_order_response(db, ctx.clinic_id, order_id)
    return ApiResponse(data=LabOrderResponse.model_validate(order))


@router.post("/", response_model=ApiResponse[LabOrderResponse], status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: LabOrderCreate,
) -> ApiResponse[LabOrderResponse]:
    order = await LabOrderService.create_order(db, ctx.clinic_id, payload, ctx.user_id)
    enriched = await LabOrderService.get_order_response(db, ctx.clinic_id, order.id)
    return ApiResponse(data=LabOrderResponse.model_validate(enriched))


@router.patch("/{order_id}", response_model=ApiResponse[LabOrderResponse])
async def update_lab_order(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    order_id: UUID,
    payload: LabOrderUpdate,
) -> ApiResponse[LabOrderResponse]:
    order = await LabOrderService.update_order(
        db, ctx.clinic_id, order_id, payload, actor_id=ctx.user_id
    )
    enriched = await LabOrderService.get_order_response(db, ctx.clinic_id, order.id)
    return ApiResponse(data=LabOrderResponse.model_validate(enriched))


@router.post("/{order_id}/transition", response_model=ApiResponse[LabOrderResponse])
async def transition_lab_order(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.work"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    order_id: UUID,
    payload: LabOrderTransition,
) -> ApiResponse[LabOrderResponse]:
    """Technician workbench: move the order along the lab workflow."""
    order = await LabOrderService.transition(
        db, ctx.clinic_id, order_id, payload.status, ctx.user_id, payload.comment
    )
    enriched = await LabOrderService.get_order_response(db, ctx.clinic_id, order.id)
    return ApiResponse(data=LabOrderResponse.model_validate(enriched))


@router.post("/{order_id}/assign", response_model=ApiResponse[LabOrderResponse])
async def assign_lab_order(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.work"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    order_id: UUID,
) -> ApiResponse[LabOrderResponse]:
    """The acting technician takes the order over."""
    order = await LabOrderService.assign(db, ctx.clinic_id, order_id, ctx.user_id)
    enriched = await LabOrderService.get_order_response(db, ctx.clinic_id, order.id)
    return ApiResponse(data=LabOrderResponse.model_validate(enriched))


@router.get("/{order_id}/events", response_model=ApiResponse[list[LabOrderEventResponse]])
async def list_lab_order_events(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    order_id: UUID,
) -> ApiResponse[list[LabOrderEventResponse]]:
    events = await LabOrderService.list_events(db, ctx.clinic_id, order_id)
    return ApiResponse(data=[LabOrderEventResponse.model_validate(e) for e in events])


@router.post(
    "/{order_id}/comments",
    response_model=ApiResponse[LabOrderEventResponse],
    status_code=status.HTTP_201_CREATED,
)
async def comment_lab_order(
    ctx: Annotated[ClinicContext, Depends(get_clinic_context)],
    _: Annotated[None, Depends(require_permission("lab_orders.comment"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    order_id: UUID,
    payload: LabOrderCommentCreate,
) -> ApiResponse[LabOrderEventResponse]:
    event = await LabOrderService.add_comment(
        db, ctx.clinic_id, order_id, ctx.user_id, payload.body
    )
    events = await LabOrderService.list_events(db, ctx.clinic_id, order_id)
    created = next((e for e in events if e["id"] == event.id), None)
    if created is None:  # pragma: no cover - row was just inserted
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Comment not stored")
    return ApiResponse(data=LabOrderEventResponse.model_validate(created))
