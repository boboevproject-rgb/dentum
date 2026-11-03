<script setup lang="ts">
import { PERMISSIONS } from '~~/app/config/permissions'
import LabOrderDrawer from '../../components/LabOrderDrawer.vue'
import {
  STATUS_COLORS,
  isOverdue,
  useLabOrders,
  type LabOrder,
  type OrderStatus
} from '../../composables/useLabOrders'

// Dental technician workbench: every open lab order of the clinic laid
// out by lab stage. Status moves and messages go through the same order
// thread the clinic sees on /lab-orders.
definePageMeta({ middleware: ['auth'] })

const { t, d } = useI18n()
const { can } = usePermissions()
const { user } = useAuth()
const api = useLabOrders()

if (!can(PERMISSIONS.labOrders.work)) await navigateTo('/')

const COLUMNS: { status: OrderStatus, icon: string }[] = [
  { status: 'sent', icon: 'i-lucide-inbox' },
  { status: 'in_progress', icon: 'i-lucide-hammer' },
  { status: 'try_in', icon: 'i-lucide-scan-face' },
  { status: 'ready', icon: 'i-lucide-package-check' }
]

const scope = ref<'all' | 'mine'>('all')
const search = ref('')
const orders = ref<LabOrder[]>([])
const loading = ref(false)
const selectedId = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await api.list({
      statuses: COLUMNS.map(c => c.status),
      technician_id: scope.value === 'mine' ? user.value?.id : undefined,
      page_size: 100
    })
    orders.value = res.data
  } finally {
    loading.value = false
  }
}

watch(scope, load)
onMounted(load)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return orders.value
  return orders.value.filter(o =>
    [o.patient_name, o.tooth_reference, o.lab_contact_name, t(`labOrders.workTypes.${o.work_type}`)]
      .some(v => v?.toLowerCase().includes(q))
  )
})

// Overdue first, then by due date (no date last).
function byUrgency(a: LabOrder, b: LabOrder) {
  const oa = isOverdue(a) ? 0 : 1
  const ob = isOverdue(b) ? 0 : 1
  if (oa !== ob) return oa - ob
  return (a.expected_date ?? '9999').localeCompare(b.expected_date ?? '9999')
}
const board = computed(() =>
  COLUMNS.map(col => ({
    ...col,
    items: filtered.value.filter(o => o.status === col.status).sort(byUrgency)
  }))
)
const overdueCount = computed(() => orders.value.filter(o => isOverdue(o)).length)

function fmtDate(value?: string | null) {
  return value ? d(new Date(`${value}T00:00:00`), { day: 'numeric', month: 'short' }) : '—'
}
</script>

<template>
  <div class="p-4 space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-h2 text-default">
          {{ t('labOrders.workbench.title') }}
        </h1>
        <p class="text-caption text-subtle">
          {{ t('labOrders.workbench.subtitle') }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <UInput
          v-model="search"
          icon="i-lucide-search"
          class="w-56"
          :placeholder="t('labOrders.workbench.search')"
          :aria-label="t('labOrders.workbench.search')"
        />
        <UFieldGroup>
          <UButton
            :variant="scope === 'all' ? 'solid' : 'outline'"
            color="neutral"
            @click="scope = 'all'"
          >
            {{ t('labOrders.workbench.all') }}
          </UButton>
          <UButton
            :variant="scope === 'mine' ? 'solid' : 'outline'"
            color="neutral"
            @click="scope = 'mine'"
          >
            {{ t('labOrders.workbench.mine') }}
          </UButton>
        </UFieldGroup>
        <UButton
          icon="i-lucide-refresh-cw"
          color="neutral"
          variant="ghost"
          :loading="loading"
          :aria-label="t('labOrders.workbench.refresh')"
          @click="load"
        />
      </div>
    </div>

    <UAlert
      v-if="overdueCount"
      color="error"
      variant="subtle"
      icon="i-lucide-alarm-clock"
      :title="t('labOrders.workbench.overdueAlert', { n: overdueCount }, overdueCount)"
    />

    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <section
        v-for="col in board"
        :key="col.status"
        class="rounded-token-lg bg-surface ring-1 ring-[var(--color-border)] p-3 space-y-2 min-h-40"
      >
        <header class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <UIcon
              :name="col.icon"
              class="w-4 h-4 text-subtle"
            />
            <span class="font-medium text-default">{{ t(`labOrders.workbench.columns.${col.status}`) }}</span>
          </div>
          <UBadge
            :color="STATUS_COLORS[col.status]"
            variant="subtle"
          >
            {{ col.items.length }}
          </UBadge>
        </header>

        <template v-if="loading && !orders.length">
          <USkeleton
            v-for="n in 2"
            :key="n"
            class="h-20 w-full"
          />
        </template>
        <p
          v-else-if="!col.items.length"
          class="text-caption text-subtle py-4 text-center"
        >
          {{ t('labOrders.workbench.empty') }}
        </p>
        <button
          v-for="order in col.items"
          :key="order.id"
          type="button"
          class="w-full text-left rounded-token-md bg-elevated hover:ring-1 hover:ring-[var(--color-primary)] px-3 py-2 space-y-1 transition"
          :class="isOverdue(order) ? 'ring-1 ring-[var(--ui-error)]' : ''"
          @click="selectedId = order.id"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-body font-medium text-default truncate">
              {{ t(`labOrders.workTypes.${order.work_type}`) }}
              <span
                v-if="order.tooth_reference"
                class="text-muted font-normal"
              >· {{ order.tooth_reference }}</span>
            </span>
            <UBadge
              v-if="order.shade"
              color="neutral"
              variant="outline"
              size="sm"
            >
              {{ order.shade }}
            </UBadge>
          </div>
          <p class="text-caption text-subtle truncate">
            {{ order.patient_name }}
          </p>
          <div class="flex items-center justify-between text-caption">
            <span :class="isOverdue(order) ? 'text-error font-medium' : 'text-subtle'">
              <UIcon
                name="i-lucide-calendar-clock"
                class="w-3 h-3 align-[-2px]"
              />
              {{ fmtDate(order.expected_date) }}
            </span>
            <span class="text-subtle truncate">
              {{ order.technician_name || t('labOrders.unassigned') }}
            </span>
          </div>
        </button>
      </section>
    </div>

    <LabOrderDrawer
      :order-id="selectedId"
      @close="selectedId = null"
      @changed="load"
    />
  </div>
</template>
