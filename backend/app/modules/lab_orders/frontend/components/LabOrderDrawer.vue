<script setup lang="ts">
import { PERMISSIONS } from '~~/app/config/permissions'
import {
  ORDER_STATUSES,
  STATUS_COLORS,
  TECHNICIAN_TRANSITIONS,
  isOverdue,
  useLabOrders,
  type LabOrder,
  type LabOrderEvent,
  type OrderStatus,
  type TechnicianStatus
} from '../composables/useLabOrders'

// One order, both sides of the conversation: clinic staff (lab_orders.write)
// and the dental technician (lab_orders.work) open this same drawer, so a
// status move or a message by one is what the other sees next.
const props = defineProps<{ orderId: string | null }>()
const emit = defineEmits<{ (e: 'close'): void, (e: 'changed', order: LabOrder): void }>()

const { t, d } = useI18n()
const { can } = usePermissions()
const toast = useToast()
const api = useLabOrders()

const open = computed(() => props.orderId !== null)
const order = ref<LabOrder | null>(null)
const events = ref<LabOrderEvent[]>([])
const loading = ref(false)
const busy = ref(false)
const message = ref('')

const canWork = computed(() => can(PERMISSIONS.labOrders.work))
const canWrite = computed(() => can(PERMISSIONS.labOrders.write))
const canComment = computed(() => can(PERMISSIONS.labOrders.comment))
const nextSteps = computed<TechnicianStatus[]>(() =>
  order.value && canWork.value ? TECHNICIAN_TRANSITIONS[order.value.status] ?? [] : []
)
const overdue = computed(() => (order.value ? isOverdue(order.value) : false))

async function load(id: string) {
  loading.value = true
  try {
    const [o, ev] = await Promise.all([api.get(id), api.events(id)])
    order.value = o.data
    events.value = ev.data
  } catch {
    toast.add({ title: t('labOrders.errors.load'), color: 'error' })
  } finally {
    loading.value = false
  }
}

watch(() => props.orderId, (id) => {
  order.value = null
  events.value = []
  message.value = ''
  if (id) load(id)
}, { immediate: true })

async function run(action: () => Promise<{ data: LabOrder }>, successKey: string) {
  if (!order.value) return
  busy.value = true
  try {
    const res = await action()
    message.value = ''
    await load(res.data.id)
    emit('changed', res.data)
    toast.add({ title: t(successKey), color: 'success' })
  } catch {
    toast.add({ title: t('labOrders.errors.action'), color: 'error' })
  } finally {
    busy.value = false
  }
}

function move(status: TechnicianStatus) {
  const id = order.value!.id
  return run(() => api.transition(id, status, message.value.trim() || undefined), 'labOrders.toast.moved')
}

function takeOver() {
  const id = order.value!.id
  return run(() => api.assign(id), 'labOrders.toast.assigned')
}

function setStatus(status: OrderStatus) {
  const id = order.value!.id
  if (status === order.value!.status) return
  return run(() => api.update(id, { status }), 'labOrders.toast.moved')
}

async function send() {
  if (!order.value || !message.value.trim()) return
  busy.value = true
  try {
    await api.comment(order.value.id, message.value.trim())
    message.value = ''
    events.value = (await api.events(order.value.id)).data
    emit('changed', order.value)
  } catch {
    toast.add({ title: t('labOrders.errors.action'), color: 'error' })
  } finally {
    busy.value = false
  }
}

const { user } = useAuth()
const isMine = computed(() => !!order.value?.technician_id && order.value.technician_id === user.value?.id)

function fmtDate(value?: string | null) {
  return value ? d(new Date(`${value}T00:00:00`), { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
}
function fmtStamp(value: string) {
  return d(new Date(value), { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
const stepIcon: Record<TechnicianStatus, string> = {
  in_progress: 'i-lucide-hammer',
  try_in: 'i-lucide-scan-face',
  ready: 'i-lucide-package-check'
}
function stepLabel(status: TechnicianStatus) {
  if (order.value?.status === 'sent') return t('labOrders.actions.take')
  if (status === 'in_progress') return t('labOrders.actions.rework')
  return t(`labOrders.actions.${status}`)
}
</script>

<template>
  <USlideover
    :open="open"
    side="right"
    :title="t('labOrders.detail.title')"
    :ui="{ content: 'w-[520px] max-w-[96vw] bg-surface' }"
    @update:open="value => { if (!value) emit('close') }"
  >
    <template #content>
      <div class="flex flex-col h-full">
        <header class="flex items-center justify-between gap-2 px-4 h-14 border-b border-default">
          <div class="min-w-0">
            <p class="text-body font-medium text-default truncate">
              {{ order ? t(`labOrders.workTypes.${order.work_type}`) : t('labOrders.detail.title') }}
              <span
                v-if="order?.tooth_reference"
                class="text-muted"
              >· {{ order.tooth_reference }}</span>
            </p>
            <p
              v-if="order"
              class="text-caption text-subtle truncate"
            >
              {{ order.patient_name }}
            </p>
          </div>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            :aria-label="t('labOrders.cancel')"
            @click="emit('close')"
          />
        </header>

        <div
          v-if="loading && !order"
          class="p-4 space-y-3"
        >
          <USkeleton class="h-6 w-1/2" />
          <USkeleton class="h-24 w-full" />
          <USkeleton class="h-40 w-full" />
        </div>

        <div
          v-else-if="order"
          class="flex-1 overflow-y-auto p-4 space-y-5"
        >
          <div class="flex flex-wrap items-center gap-2">
            <UBadge
              :color="STATUS_COLORS[order.status]"
              variant="subtle"
              size="lg"
            >
              {{ t(`labOrders.statuses.${order.status}`) }}
            </UBadge>
            <UBadge
              v-if="overdue"
              color="error"
              variant="soft"
              icon="i-lucide-alarm-clock"
            >
              {{ t('labOrders.overdue') }}
            </UBadge>
            <USelect
              v-if="canWrite"
              class="ml-auto w-44"
              size="sm"
              :model-value="order.status"
              :disabled="busy"
              :items="ORDER_STATUSES.map(value => ({ value, label: t(`labOrders.statuses.${value}`) }))"
              :aria-label="t('labOrders.status')"
              @update:model-value="value => setStatus(value as OrderStatus)"
            />
          </div>

          <dl class="grid grid-cols-2 gap-x-4 gap-y-3 text-body">
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.patient') }}
              </dt>
              <dd class="text-default">
                {{ order.patient_name }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.lab') }}
              </dt>
              <dd class="text-default">
                {{ order.lab_contact_name }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.tooth') }}
              </dt>
              <dd class="text-default">
                {{ order.tooth_reference || '—' }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.shade') }}
              </dt>
              <dd class="text-default">
                {{ order.shade || '—' }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.impressionType') }}
              </dt>
              <dd class="text-default">
                {{ order.impression_type ? t(`labOrders.impressionTypes.${order.impression_type}`) : '—' }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.technician') }}
              </dt>
              <dd class="text-default">
                {{ order.technician_name || t('labOrders.unassigned') }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.sentDate') }}
              </dt>
              <dd class="text-default">
                {{ fmtDate(order.sent_date) }}
              </dd>
            </div>
            <div>
              <dt class="text-caption text-subtle">
                {{ t('labOrders.expectedDate') }}
              </dt>
              <dd :class="overdue ? 'text-error font-medium' : 'text-default'">
                {{ fmtDate(order.expected_date) }}
              </dd>
            </div>
            <div
              v-if="order.received_date"
              class="col-span-2"
            >
              <dt class="text-caption text-subtle">
                {{ t('labOrders.receivedDate') }}
              </dt>
              <dd class="text-default">
                {{ fmtDate(order.received_date) }}
              </dd>
            </div>
            <div
              v-if="order.antagonist_info"
              class="col-span-2"
            >
              <dt class="text-caption text-subtle">
                {{ t('labOrders.antagonistInfo') }}
              </dt>
              <dd class="text-default whitespace-pre-line">
                {{ order.antagonist_info }}
              </dd>
            </div>
            <div
              v-if="order.notes"
              class="col-span-2"
            >
              <dt class="text-caption text-subtle">
                {{ t('labOrders.notes') }}
              </dt>
              <dd class="text-default whitespace-pre-line">
                {{ order.notes }}
              </dd>
            </div>
          </dl>

          <div
            v-if="canWork && (nextSteps.length || !isMine)"
            class="rounded-token-md ring-1 ring-[var(--color-border)] p-3 space-y-2"
          >
            <p class="text-caption text-subtle">
              {{ t('labOrders.detail.nextStep') }}
            </p>
            <div class="flex flex-wrap gap-2">
              <UButton
                v-for="step in nextSteps"
                :key="step"
                :icon="stepIcon[step]"
                :color="step === 'ready' ? 'success' : 'primary'"
                :variant="step === 'in_progress' && order.status !== 'sent' ? 'outline' : 'solid'"
                :loading="busy"
                @click="move(step)"
              >
                {{ stepLabel(step) }}
              </UButton>
              <UButton
                v-if="!isMine && !['received', 'cancelled'].includes(order.status) && order.status !== 'sent'"
                icon="i-lucide-user-check"
                color="neutral"
                variant="outline"
                :loading="busy"
                @click="takeOver"
              >
                {{ t('labOrders.actions.assignMe') }}
              </UButton>
            </div>
            <p
              v-if="nextSteps.length"
              class="text-caption text-muted"
            >
              {{ t('labOrders.detail.commentHint') }}
            </p>
          </div>

          <section class="space-y-3">
            <h3 class="text-body font-medium text-default">
              {{ t('labOrders.detail.history') }}
            </h3>
            <p
              v-if="!events.length"
              class="text-caption text-subtle"
            >
              {{ t('labOrders.detail.noHistory') }}
            </p>
            <ol class="space-y-3">
              <li
                v-for="event in events"
                :key="event.id"
                class="flex gap-3"
              >
                <UIcon
                  :name="event.kind === 'comment' ? 'i-lucide-message-square' : event.kind === 'assigned' ? 'i-lucide-user-check' : 'i-lucide-arrow-right-left'"
                  class="w-4 h-4 mt-0.5 shrink-0 text-subtle"
                />
                <div class="min-w-0 flex-1">
                  <p class="text-caption text-subtle">
                    <span class="text-default font-medium">{{ event.author_name || t('labOrders.detail.system') }}</span>
                    · {{ fmtStamp(event.created_at) }}
                  </p>
                  <p
                    v-if="event.kind === 'status'"
                    class="text-body text-default"
                  >
                    <template v-if="event.from_status">
                      {{ t('labOrders.detail.statusChanged', {
                        from: t(`labOrders.statuses.${event.from_status}`),
                        to: t(`labOrders.statuses.${event.to_status}`)
                      }) }}
                    </template>
                    <template v-else>
                      {{ t('labOrders.detail.created') }}
                    </template>
                  </p>
                  <p
                    v-else-if="event.kind === 'assigned'"
                    class="text-body text-default"
                  >
                    {{ t('labOrders.detail.assigned') }}
                  </p>
                  <p
                    v-else
                    class="text-body text-default whitespace-pre-line rounded-token-md bg-elevated px-3 py-2 mt-1"
                  >
                    {{ event.body }}
                  </p>
                </div>
              </li>
            </ol>
          </section>
        </div>

        <footer
          v-if="order && canComment"
          class="border-t border-default p-3 space-y-2"
        >
          <UTextarea
            v-model="message"
            :rows="2"
            autoresize
            class="w-full"
            :maxlength="2000"
            :placeholder="t('labOrders.detail.messagePlaceholder')"
            :aria-label="t('labOrders.detail.messagePlaceholder')"
          />
          <div class="flex justify-end">
            <UButton
              icon="i-lucide-send"
              :disabled="!message.trim()"
              :loading="busy"
              @click="send"
            >
              {{ t('labOrders.detail.send') }}
            </UButton>
          </div>
        </footer>
      </div>
    </template>
  </USlideover>
</template>
