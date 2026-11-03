---
module: lab_orders
screen: lab-workbench
route: /lab-workbench
related_endpoints:
  - GET /api/v1/lab_orders/
  - GET /api/v1/lab_orders/{order_id}
  - POST /api/v1/lab_orders/{order_id}/transition
  - POST /api/v1/lab_orders/{order_id}/assign
  - GET /api/v1/lab_orders/{order_id}/events
  - POST /api/v1/lab_orders/{order_id}/comments
related_permissions:
  - lab_orders.read
  - lab_orders.work
  - lab_orders.comment
related_paths:
  - backend/app/modules/lab_orders/router.py
  - backend/app/modules/lab_orders/frontend/pages/lab-workbench/index.vue
  - backend/app/modules/lab_orders/frontend/components/LabOrderDrawer.vue
last_verified_commit: 8170cf4
---

# Technician workbench

The **Technician workbench** is the dental technician's screen. It shows every open lab order of the clinic in four columns: **New**, **In work**, **Try-in** and **Ready to collect**. Overdue orders are outlined in red and listed first.

- **All / Mine** switches between every order and the ones assigned to you.
- Open a card to see the order details and the conversation with the clinic.
- The **Next step** buttons move the order: *Take into work*, *Send for try-in*, *Mark ready*, *Back to work*. Text typed in the message box is attached to the move as a comment.
- **Assign to me** takes over an order assigned to another technician.

The clinic sees the same thread from **Lab orders → Open** and confirms receipt by setting the status to *Received*.
