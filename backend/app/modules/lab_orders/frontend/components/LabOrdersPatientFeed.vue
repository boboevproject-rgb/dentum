<script setup lang="ts">
import LabOrderDrawer from './LabOrderDrawer.vue'
import { STATUS_COLORS, isOverdue, useLabOrders, type LabOrder } from '../composables/useLabOrders'

// Slot entry into `patient.summary.feed`: the patient's lab work and
// where it stands in the lab.
const props = defineProps<{ ctx: { patient: { id: string } } }>()

const { t, d } = useI18n()
const api = useLabOrders()
const orders = ref<LabOrder[]>([])
const isLoading = ref(false)
const selectedId = ref<string | null>(null)

async function load() {
  const patientId = props.ctx?.patient?.id
  if (!patientId) return
  isLoading.value = true
  try {
    orders.value = (await api.list({ patient_id: patientId, page_size: 5 })).data
  } catch {
    orders.value = []
  } finally {
    isLoading.value = false
  }
}
onMounted(load)

function fmtDate(value?: string | null) {
  return value ? d(new Date(`${value}T00:00:00`), { day: 'numeric', month: 'short' }) : '—'
}
</script>

<template>
  <UCard
    v-if="orders.length > 0 || isLoading"
    :ui="{ body: 'p-3' }"
  >
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon
          name="i-lucide-flask-conical"
          class="w-4 h-4 text-default"
        />
        <span class="font-medium">{{ t('labOrders.patientFeed.title') }}</span>
      </div>
    </template>
    <USkeleton
      v-if="isLoading"
      class="h-12 w-full"
    />
    <ul
      v-else
      class="divide-y divide-default"
    >
      <li
        v-for="order in orders"
        :key="order.id"
      >
        <button
          type="button"
          class="w-full flex items-center justify-between gap-2 py-2 text-left hover:bg-elevated rounded-token-sm px-1"
          @click="selectedId = order.id"
        >
          <span class="min-w-0">
            <span class="block text-body text-default truncate">
              {{ t(`labOrders.workTypes.${order.work_type}`) }}
              <span
                v-if="order.tooth_reference"
                class="text-muted"
              >· {{ order.tooth_reference }}</span>
            </span>
            <span
              class="block text-caption"
              :class="isOverdue(order) ? 'text-error' : 'text-subtle'"
            >
              {{ t('labOrders.patientFeed.due', { date: fmtDate(order.expected_date) }) }}
            </span>
          </span>
          <UBadge
            :color="STATUS_COLORS[order.status]"
            variant="subtle"
          >
            {{ t(`labOrders.statuses.${order.status}`) }}
          </UBadge>
        </button>
      </li>
    </ul>
    <LabOrderDrawer
      :order-id="selectedId"
      @close="selectedId = null"
      @changed="load"
    />
  </UCard>
</template>
