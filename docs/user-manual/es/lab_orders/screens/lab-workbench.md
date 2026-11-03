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

# Mesa del técnico

La **Mesa del técnico** es la pantalla del técnico dental. Muestra todos los pedidos de laboratorio abiertos de la clínica en cuatro columnas: **Nuevos**, **En trabajo**, **Prueba** y **Listos para recoger**. Los pedidos vencidos aparecen primero y marcados en rojo.

- **Todos / Míos** alterna entre todos los pedidos y los asignados a ti.
- Abre una tarjeta para ver el detalle del pedido y la conversación con la clínica.
- Los botones de **Siguiente paso** mueven el pedido: *Empezar*, *Enviar a prueba*, *Marcar listo*, *Volver a trabajo*. El texto del mensaje se adjunta al cambio como comentario.
- **Asignarme** toma un pedido asignado a otro técnico.

La clínica ve el mismo hilo desde **Pedidos de laboratorio → Abrir** y confirma la recepción con el estado *Recibido*.
