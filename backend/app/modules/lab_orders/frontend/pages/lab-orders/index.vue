<script setup lang="ts">
import { PERMISSIONS } from '~~/app/config/permissions'
import LabOrderDrawer from '../../components/LabOrderDrawer.vue'
import {
  ORDER_STATUSES,
  STATUS_COLORS,
  isOverdue,
  useLabOrders,
  type LabOrder,
  type OrderStatus
} from '../../composables/useLabOrders'

definePageMeta({ middleware: ['auth'] })

const { t, d } = useI18n()
const { can } = usePermissions()
const toast = useToast()
const api = useLabOrders()
const loading = ref(false)
const orders = ref<LabOrder[]>([])
const total = ref(0)
const page = ref(1)
const statusFilter = ref<OrderStatus | 'all'>('all')
const selectedId = ref<string | null>(null)
const PAGE_SIZE = 20
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

if (!can(PERMISSIONS.labOrders.read)) await navigateTo('/')

async function load() {
  loading.value = true
  try {
    const response = await api.list({
      page: page.value,
      page_size: PAGE_SIZE,
      order_status: statusFilter.value === 'all' ? undefined : statusFilter.value
    })
    orders.value = response.data
    total.value = response.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  load()
}

watch(statusFilter, () => {
  page.value = 1
  load()
})

async function updateStatus(id: string, status: OrderStatus) {
  try {
    await api.update(id, { status })
    toast.add({ title: t('labOrders.toast.moved'), color: 'success' })
  } catch {
    toast.add({ title: t('labOrders.errors.action'), color: 'error' })
  }
  await load()
}

function fmtDate(value?: string | null) {
  return value ? d(new Date(`${value}T00:00:00`), { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
}

const filterItems = computed(() => [
  { value: 'all', label: t('labOrders.allStatuses') },
  ...ORDER_STATUSES.map(value => ({ value, label: t(`labOrders.statuses.${value}`) }))
])

onMounted(load)
</script>

<template>
  <div class="p-4 space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-h2 text-default">
        {{ t('labOrders.title') }}
      </h1>
      <div class="flex items-center gap-2">
        <USelect
          v-model="statusFilter"
          class="w-48"
          :items="filterItems"
          :aria-label="t('labOrders.status')"
        />
        <UButton
          v-if="can(PERMISSIONS.labOrders.write)"
          to="/lab-orders/new"
          icon="i-lucide-plus"
        >
          {{ t('labOrders.add') }}
        </UButton>
      </div>
    </div>
    <div
      v-if="loading"
      class="text-caption text-subtle"
    >
      {{ t('labOrders.loading') }}
    </div>
    <p
      v-else-if="!orders.length"
      class="text-caption text-subtle py-6 text-center"
    >
      {{ t('labOrders.empty') }}
    </p>
    <UTable
      v-else
      :data="orders"
      :columns="[
        { accessorKey: 'patient_name', header: t('labOrders.patient') },
        { accessorKey: 'work_type', header: t('labOrders.workType') },
        { accessorKey: 'lab_contact_name', header: t('labOrders.lab') },
        { accessorKey: 'technician_name', header: t('labOrders.technician') },
        { accessorKey: 'sent_date', header: t('labOrders.sentDate') },
        { accessorKey: 'expected_date', header: t('labOrders.expectedDate') },
        { accessorKey: 'status', header: t('labOrders.status') },
        { id: 'open', header: '' }
      ]"
    >
      <template #work_type-cell="{ row }">
        {{ t(`labOrders.workTypes.${row.original.work_type}`) }}
        <span
          v-if="row.original.tooth_reference"
          class="text-muted"
        >· {{ row.original.tooth_reference }}</span>
      </template>
      <template #technician_name-cell="{ row }">
        <span :class="row.original.technician_name ? 'text-default' : 'text-subtle'">
          {{ row.original.technician_name || t('labOrders.unassigned') }}
        </span>
      </template>
      <template #sent_date-cell="{ row }">
        {{ fmtDate(row.original.sent_date) }}
      </template>
      <template #expected_date-cell="{ row }">
        <span :class="isOverdue(row.original) ? 'text-error font-medium' : ''">
          {{ fmtDate(row.original.expected_date) }}
        </span>
      </template>
      <template #status-cell="{ row }">
        <USelect
          v-if="can(PERMISSIONS.labOrders.write)"
          class="w-40"
          :model-value="row.original.status"
          :items="ORDER_STATUSES.map(value => ({ value, label: t(`labOrders.statuses.${value}`) }))"
          :aria-label="t('labOrders.status')"
          @update:model-value="value => updateStatus(row.original.id, value as OrderStatus)"
        />
        <UBadge
          v-else
          :color="STATUS_COLORS[row.original.status as OrderStatus]"
          variant="subtle"
        >
          {{ t(`labOrders.statuses.${row.original.status}`) }}
        </UBadge>
      </template>
      <template #open-cell="{ row }">
        <UButton
          icon="i-lucide-messages-square"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="selectedId = row.original.id"
        >
          {{ t('labOrders.open') }}
        </UButton>
      </template>
    </UTable>

    <PaginationBar
      :page="page"
      :total-pages="totalPages"
      :total="total"
      :page-size="PAGE_SIZE"
      @update:page="onPage"
    />

    <LabOrderDrawer
      :order-id="selectedId"
      @close="selectedId = null"
      @changed="load"
    />
  </div>
</template>
