export type WorkType = 'crown' | 'bridge' | 'denture' | 'implant' | 'veneer' | 'orthodontic' | 'repair' | 'other'
export type OrderStatus = 'sent' | 'in_progress' | 'try_in' | 'ready' | 'received' | 'cancelled'
export type TechnicianStatus = 'in_progress' | 'try_in' | 'ready'
export type ImpressionType = 'alginate' | 'pvs_silicone' | 'digital_scan' | 'other'
export const VITA_CLASSICAL_SHADES = ['A1', 'A2', 'A3', 'A3.5', 'A4', 'B1', 'B2', 'B3', 'B4', 'C1', 'C2', 'C3', 'C4', 'D2', 'D3', 'D4'] as const
export type Shade = typeof VITA_CLASSICAL_SHADES[number]

export const ORDER_STATUSES: OrderStatus[] = ['sent', 'in_progress', 'try_in', 'ready', 'received', 'cancelled']
export const OPEN_STATUSES: OrderStatus[] = ['sent', 'in_progress', 'try_in', 'ready']

// Mirrors TECHNICIAN_TRANSITIONS in the backend service.
export const TECHNICIAN_TRANSITIONS: Record<string, TechnicianStatus[]> = {
  sent: ['in_progress'],
  in_progress: ['try_in', 'ready'],
  try_in: ['in_progress', 'ready'],
  ready: ['in_progress']
}

export const STATUS_COLORS: Record<OrderStatus, 'neutral' | 'info' | 'warning' | 'success' | 'primary' | 'error'> = {
  sent: 'info',
  in_progress: 'warning',
  try_in: 'primary',
  ready: 'success',
  received: 'neutral',
  cancelled: 'error'
}

export interface LabOrder {
  id: string
  clinic_id: string
  patient_id: string
  patient_name: string
  lab_contact_id: string
  lab_contact_name: string
  work_type: WorkType
  tooth_reference?: string | null
  impression_type?: ImpressionType | null
  antagonist_info?: string | null
  shade?: Shade | null
  status: OrderStatus
  sent_date: string
  expected_date?: string | null
  received_date?: string | null
  notes?: string | null
  created_by?: string | null
  technician_id?: string | null
  technician_name?: string | null
  created_at: string
  updated_at: string
}

export interface LabOrderEvent {
  id: string
  order_id: string
  author_id: string | null
  author_name: string | null
  kind: 'status' | 'comment' | 'assigned'
  from_status: OrderStatus | null
  to_status: OrderStatus | null
  body: string | null
  created_at: string
}

export interface LabOrderCreatePayload {
  patient_id: string
  lab_contact_id: string
  work_type: WorkType
  tooth_reference?: string | null
  impression_type?: ImpressionType | null
  antagonist_info?: string | null
  shade?: Shade | null
  sent_date: string
  expected_date?: string | null
  notes?: string | null
}

export interface LabOrderUpdatePayload {
  lab_contact_id?: string
  work_type?: WorkType
  tooth_reference?: string | null
  impression_type?: ImpressionType | null
  antagonist_info?: string | null
  shade?: Shade | null
  status?: OrderStatus
  expected_date?: string | null
  received_date?: string | null
  notes?: string | null
}

export interface LabOrderFilters {
  patient_id?: string
  lab_contact_id?: string
  order_status?: OrderStatus
  statuses?: OrderStatus[]
  technician_id?: string
  page?: number
  page_size?: number
}

interface ApiOk<T> { data: T, message?: string | null }
interface ApiPaged<T> { data: T[], total: number, page: number, page_size: number }

/** True when the order is still open and its due date is in the past. */
export function isOverdue(order: Pick<LabOrder, 'status' | 'expected_date'>, today = new Date()): boolean {
  if (!order.expected_date || !OPEN_STATUSES.includes(order.status) || order.status === 'ready') return false
  const due = new Date(`${order.expected_date}T23:59:59`)
  return due.getTime() < today.getTime()
}

export function useLabOrders() {
  const api = useApi()
  async function list(filters: LabOrderFilters = {}) {
    const qs = new URLSearchParams()
    for (const [key, value] of Object.entries(filters)) {
      if (value === undefined || value === null || value === '') continue
      qs.append(key, Array.isArray(value) ? value.join(',') : String(value))
    }
    const url = `/api/v1/lab_orders/${qs.toString() ? `?${qs}` : ''}`
    return await api.get<ApiPaged<LabOrder>>(url)
  }
  async function get(id: string): Promise<ApiOk<LabOrder>> {
    return await api.get<ApiOk<LabOrder>>(`/api/v1/lab_orders/${id}`)
  }
  async function stats(technicianId?: string): Promise<ApiOk<Partial<Record<OrderStatus, number>>>> {
    const qs = technicianId ? `?technician_id=${technicianId}` : ''
    return await api.get<ApiOk<Partial<Record<OrderStatus, number>>>>(`/api/v1/lab_orders/stats${qs}`)
  }
  async function create(payload: LabOrderCreatePayload): Promise<ApiOk<LabOrder>> {
    return await api.post<ApiOk<LabOrder>>('/api/v1/lab_orders/', payload)
  }
  async function update(id: string, payload: LabOrderUpdatePayload): Promise<ApiOk<LabOrder>> {
    return await api.patch<ApiOk<LabOrder>>(`/api/v1/lab_orders/${id}`, payload)
  }
  async function transition(id: string, status: TechnicianStatus, comment?: string): Promise<ApiOk<LabOrder>> {
    return await api.post<ApiOk<LabOrder>>(`/api/v1/lab_orders/${id}/transition`, { status, comment: comment || null })
  }
  async function assign(id: string): Promise<ApiOk<LabOrder>> {
    return await api.post<ApiOk<LabOrder>>(`/api/v1/lab_orders/${id}/assign`, {})
  }
  async function events(id: string): Promise<ApiOk<LabOrderEvent[]>> {
    return await api.get<ApiOk<LabOrderEvent[]>>(`/api/v1/lab_orders/${id}/events`)
  }
  async function comment(id: string, body: string): Promise<ApiOk<LabOrderEvent>> {
    return await api.post<ApiOk<LabOrderEvent>>(`/api/v1/lab_orders/${id}/comments`, { body })
  }
  return { list, get, stats, create, update, transition, assign, events, comment }
}
