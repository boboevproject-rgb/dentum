<script setup lang="ts">
import { PERMISSIONS } from '~~/app/config/permissions'
import { useLabOrders, type OrderStatus } from '../composables/useLabOrders'

// Dashboard counters. The technician lands on their workbench, clinic
// staff on the order list.
const { t } = useI18n()
const { can } = usePermissions()
const api = useLabOrders()

const counts = ref<Partial<Record<OrderStatus, number>> | null>(null)
const isLoading = ref(false)
const target = computed(() => (can(PERMISSIONS.labOrders.work) ? '/lab-workbench' : '/lab-orders'))
const TILES: OrderStatus[] = ['sent', 'in_progress', 'try_in', 'ready']

onMounted(async () => {
  isLoading.value = true
  try {
    counts.value = (await api.stats()).data
  } catch {
    counts.value = null
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <UCard
    v-if="counts || isLoading"
    :ui="{ body: 'p-3' }"
  >
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <UIcon
            name="i-lucide-flask-conical"
            class="w-4 h-4 text-default"
          />
          <span class="font-medium">{{ t('labOrders.dashboard.title') }}</span>
        </div>
        <NuxtLink
          :to="target"
          class="text-primary-accent hover:underline text-caption"
        >
          {{ t('labOrders.dashboard.open') }} →
        </NuxtLink>
      </div>
    </template>
    <USkeleton
      v-if="isLoading || !counts"
      class="h-16 w-full"
    />
    <div
      v-else
      class="grid grid-cols-2 gap-2 sm:grid-cols-4 text-center"
    >
      <div
        v-for="status in TILES"
        :key="status"
      >
        <div class="text-h2 text-default tnum">
          {{ counts[status] ?? 0 }}
        </div>
        <div class="text-caption text-subtle">
          {{ t(`labOrders.statuses.${status}`) }}
        </div>
      </div>
    </div>
  </UCard>
</template>
