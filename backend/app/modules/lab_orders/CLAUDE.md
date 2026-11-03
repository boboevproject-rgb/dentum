# lab_orders module

Tracks work sent to external laboratories for a specific patient, with a lifecycle from `sent` through `received` (or `cancelled`), and gives the
dental technician (core role `technician`) a workbench at `/lab-workbench`.

## Dependencies

`manifest.depends = ["patients", "contacts"]`.

- `patient_id` references `patients.id`.
- `lab_contact_id` references `contacts.id`.
- Every service query and agent tool is scoped by `clinic_id`.
- The initial Alembic revision declares `depends_on = ("pat_0003", "con_0001")` in addition to the module dependency manifest because migration-graph ordering is separate from module installation ordering.

## Permissions

`lab_orders.read`, `lab_orders.write`, `lab_orders.work`, `lab_orders.comment`.

- `write` — clinic side: create, edit, set any status (incl. `received`, `cancelled`).
- `work` — technician side: only the lab moves in `TECHNICIAN_TRANSITIONS`
  (`sent→in_progress`, `in_progress→try_in|ready`, `try_in→in_progress|ready`,
  `ready→in_progress`) plus taking an order over. A first move auto-assigns.
- `comment` — write in the order thread.

## Workflow and thread

Statuses: `sent`, `in_progress`, `try_in`, `ready`, `received`, `cancelled`.
Every status change (from PATCH or `/transition`), assignment and comment
is a row in `lab_order_events`; both sides read the same thread via
`GET /{id}/events`. The state machine lives in `service.TECHNICIAN_TRANSITIONS`
and is mirrored in `frontend/composables/useLabOrders.ts`.

## HTTP

Routes are mounted under `/api/v1/lab_orders/`.

- GET list/detail — read
- POST create — write, returns 201
- PATCH update/status — write
- GET `/stats` — read (count per status, optional `technician_id`)
- POST `/{id}/transition` — work (409 on a move outside the state machine)
- POST `/{id}/assign` — work (409 on received/cancelled)
- GET `/{id}/events` — read
- POST `/{id}/comments` — comment, returns 201

There is no DELETE: orders are terminated via `status = "cancelled"`
(patient-linked records are never hard-deleted).

## Tools exposed

All handlers wrap `LabOrderService` and are scoped by `ctx.clinic_id`.
Summaries return only structured fields (ids, dates, enums) — no
`notes` / names — so none sets `exposes_free_text`.

| Tool | Category | Permission |
|------|----------|------------|
| `list_lab_orders` | READ | `lab_orders.read` |
| `create_lab_order` | WRITE | `lab_orders.write` |
| `update_lab_order_status` | WRITE | `lab_orders.write` |

## Slots

- `dashboard.attention` — `LabDashboardWidget` (counts per lab stage).
- `patient.summary.feed` — `LabOrdersPatientFeed` (patient's lab work).

## Events

The module emits `lab_order.status_changed` after a successful status transition (PATCH or technician `/transition`). No bundled handler consumes it; other optional modules may subscribe without importing `lab_orders`.

## Lifecycle

`installable=True`, `auto_install=False`, `removable=True`.

The module owns three Alembic revisions on the `lab_orders` branch, and the test suite verifies branch-scoped uninstall/reinstall.
