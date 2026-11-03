---
module: lab_orders
last_verified_commit: c9c20493
---

# lab_orders — permissions

| Permission | Gates | Endpoints |
|---|---|---|
| `lab_orders.read` | View lab orders | `GET /api/v1/lab_orders/`, `GET /api/v1/lab_orders/{id}` |
| `lab_orders.read` (also) | Status counters, order thread | `GET /api/v1/lab_orders/stats`, `GET /api/v1/lab_orders/{id}/events` |
| `lab_orders.write` | Create/update lab orders (cancel via status; no hard delete) | `POST`, `PATCH` under `/api/v1/lab_orders/` |
| `lab_orders.work` | Technician workflow moves and take-over | `POST /api/v1/lab_orders/{id}/transition`, `POST /api/v1/lab_orders/{id}/assign` |
| `lab_orders.comment` | Write in the order thread | `POST /api/v1/lab_orders/{id}/comments` |

Default role mapping:

| Role | Permissions |
|---|---|
| `admin` | all (`*`) |
| `dentist` | read, write, comment |
| `hygienist` | read only |
| `assistant` | read, write, comment |
| `receptionist` | read, write, comment |
| `technician` | read, work, comment |
