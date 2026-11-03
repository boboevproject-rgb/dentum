import { defineAsyncComponent } from 'vue'
import { registerSlot } from '~~/app/composables/useModuleSlots'
import { PERMISSIONS } from '~~/app/config/permissions'

/**
 * Slot registrations for the `lab_orders` module. Hosts expose the slot
 * names and never import this module.
 */
export default defineNuxtPlugin(() => {
  // Dashboard — lab stage counters (clinic staff and technician).
  registerSlot('dashboard.attention', {
    id: 'lab_orders.dashboard.counters',
    component: defineAsyncComponent(() => import('../components/LabDashboardWidget.vue')),
    permission: PERMISSIONS.labOrders.read,
    order: 40
  })

  // Patient summary feed — the patient's lab work and its status.
  registerSlot('patient.summary.feed', {
    id: 'lab_orders.patient.feed',
    component: defineAsyncComponent(() => import('../components/LabOrdersPatientFeed.vue')),
    permission: PERMISSIONS.labOrders.read,
    order: 40
  })
})
