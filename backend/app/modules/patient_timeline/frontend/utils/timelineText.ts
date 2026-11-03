/**
 * Timeline rows store a ready-made title (written by the event handlers in
 * Spanish, by the demo seed in the demo language). Re-render the known
 * shapes in the viewer's language; anything unrecognised is shown as stored.
 *
 * Each rule: patterns (Spanish handler text + English demo text) whose
 * first capture group, if any, is the variable part, and the i18n key under
 * `timelineText.titles` that takes it as `{x}`.
 */
type Rule = { key: string, patterns: RegExp[] }

const P = (prefix: string, suffix: 'colon' | 'paren' | 'none' = 'colon'): RegExp => {
  const esc = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  if (suffix === 'colon') return new RegExp(`^${esc}(?::\\s*(.+))?$`, 's')
  if (suffix === 'paren') return new RegExp(`^${esc}(?:\\s*\\((.+)\\))?$`, 's')
  return new RegExp(`^${esc}$`)
}

const RULES: Rule[] = [
  { key: 'apptScheduled', patterns: [P('Cita programada'), P('Scheduled appointment'), P('Appointment scheduled')] },
  { key: 'apptCompleted', patterns: [P('Cita completada'), P('Completed appointment'), P('Appointment completed')] },
  { key: 'apptCancelled', patterns: [P('Cita cancelada'), P('Cancelled appointment'), P('Appointment cancelled')] },
  { key: 'apptNoShow', patterns: [P('Paciente no asistió'), P('Patient no-show')] },
  { key: 'apptConfirmed', patterns: [P('Cita confirmada'), P('Appointment confirmed')] },
  { key: 'apptCheckedIn', patterns: [P('Paciente llegó a la clínica', 'paren')] },
  { key: 'apptInTreatment', patterns: [P('Paciente en gabinete', 'paren')] },
  { key: 'treatmentPerformed', patterns: [P('Tratamiento realizado'), P('Treatment performed')] },
  { key: 'planCreated', patterns: [P('Plan de tratamiento creado'), P('Treatment plan created')] },
  { key: 'planItemCompleted', patterns: [P('Tratamiento del plan completado'), P('Plan treatment completed')] },
  { key: 'budgetSent', patterns: [P('Presupuesto enviado'), P('Budget sent')] },
  { key: 'budgetAccepted', patterns: [P('Presupuesto aceptado'), P('Budget accepted')] },
  { key: 'budgetRejected', patterns: [P('Presupuesto rechazado'), P('Budget rejected')] },
  { key: 'budgetExpired', patterns: [P('Presupuesto caducado'), P('Budget expired')] },
  { key: 'budgetRenegotiated', patterns: [P('Presupuesto en renegociación', 'none')] },
  { key: 'budgetViewed', patterns: [P('Presupuesto visto por el paciente', 'none')] },
  { key: 'budgetReminder', patterns: [P('Recordatorio enviado', 'paren')] },
  { key: 'planConfirmed', patterns: [P('Plan confirmado')] },
  { key: 'planClosed', patterns: [P('Plan cerrado', 'paren')] },
  { key: 'planReactivated', patterns: [P('Plan reactivado', 'none')] },
  { key: 'invoiceIssued', patterns: [P('Factura emitida'), P('Invoice issued')] },
  { key: 'invoicePaid', patterns: [P('Factura pagada'), P('Invoice paid')] },
  { key: 'emailSent', patterns: [P('Email enviado')] },
  { key: 'whatsappSent', patterns: [P('WhatsApp enviado')] },
  { key: 'messageSent', patterns: [P('Mensaje enviado')] },
  { key: 'emailFailed', patterns: [P('Email fallido')] },
  { key: 'whatsappFailed', patterns: [P('WhatsApp fallido')] },
  { key: 'messageFailed', patterns: [P('Mensaje fallido')] },
  { key: 'whatsappReply', patterns: [P('Respuesta recibida por WhatsApp', 'none')] },
  { key: 'medicalHistoryUpdated', patterns: [P('Historia clínica actualizada', 'none')] },
  { key: 'document', patterns: [P('Documento')] },
  { key: 'xray', patterns: [P('Radiografía')] },
  { key: 'clinicalPhoto', patterns: [P('Foto clínica')] },
  { key: 'beforeAfter', patterns: [P('Comparativa antes/después creada', 'none')] },
  { key: 'noteAdministrative', patterns: [P('Nota administrativa', 'none')] },
  { key: 'noteDiagnosis', patterns: [P('Nota de diagnóstico', 'none')] },
  { key: 'noteTreatment', patterns: [P('Nota clínica en tratamiento', 'none')] },
  { key: 'notePlan', patterns: [P('Nota clínica en plan de tratamiento', 'none')] },
  { key: 'noteVisit', patterns: [P('Nota clínica de visita', 'none')] },
  { key: 'note', patterns: [P('Nota clínica', 'none')] },
  { key: 'completedWithoutNote', patterns: [/^(.+) completado sin nota$/s] },
  { key: 'prescriptionIssued', patterns: [P('Receta emitida', 'none')] },
  { key: 'prescriptionCancelled', patterns: [P('Receta cancelada', 'none')] },
  { key: 'imagingStudy', patterns: [P('Estudio de imagen', 'none')] },
  { key: 'orthoOpened', patterns: [P('Caso de ortodoncia abierto', 'none')] },
  { key: 'orthoStatus', patterns: [P('Estado de ortodoncia actualizado', 'none')] },
  { key: 'orthoReview', patterns: [P('Control de ortodoncia', 'none')] }
]

const TOOTH_SUFFIX = /^(.*) \(diente (\d+)\)$/s
const TEETH = /^(?:Dientes|Teeth): (.+)$/s

type Translate = (key: string, named?: Record<string, unknown>) => string
type Exists = (key: string) => boolean

// Odontogram writes the raw clinical type ("crown", "root_canal_full").
const CLINICAL_TYPE = /^[a-z][a-z0-9_]*$/

export function localizeTimelineTitle(title: string, t: Translate, te?: Exists): string {
  let tooth: string | null = null
  let text = title
  const toothMatch = TOOTH_SUFFIX.exec(title)
  if (toothMatch) {
    text = toothMatch[1]!
    tooth = toothMatch[2]!
  }
  for (const rule of RULES) {
    for (const re of rule.patterns) {
      const m = re.exec(text)
      if (!m) continue
      let x = m[1]
      if (x && te && CLINICAL_TYPE.test(x) && te(`odontogram.treatments.types.${x}`)) {
        x = t(`odontogram.treatments.types.${x}`)
      }
      let out = x
        ? t(`timelineText.titles.${rule.key}`, { x })
        : t(`timelineText.bare.${rule.key}`)
      if (tooth) out = t('timelineText.withTooth', { text: out, tooth })
      return out
    }
  }
  return title
}

export function localizeTimelineDescription(description: string, t: Translate): string {
  const m = TEETH.exec(description)
  return m ? t('timelineText.teeth', { teeth: m[1] }) : description
}
