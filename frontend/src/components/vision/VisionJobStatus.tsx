import type { VisionJob } from '@/api/vision'
import { t } from '@/i18n'

interface VisionJobStatusProps {
  job: VisionJob | null
  mock?: boolean
}

function formatResult(job: VisionJob): string {
  if (job.error) {
    return JSON.stringify(job.error, null, 2)
  }
  if (job.result) {
    return JSON.stringify(job.result, null, 2)
  }
  return ''
}

export function VisionJobStatus({ job, mock = false }: VisionJobStatusProps) {
  if (!job) {
    return <p className="font-sans text-sm text-muted">{t('vision.resultsPlaceholder')}</p>
  }

  const failed = job.status === 'failed'
  const resultText = formatResult(job)

  return (
    <div className="space-y-3 border border-[#1A1A1A]/12 bg-paper p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-display text-xl font-semibold">{t('vision.resultsTitle')}</h2>
        <span
          className={`font-mono text-xs uppercase tracking-wide px-2 py-1 ${
            failed ? 'bg-red-100 text-red-800' : 'bg-cream text-ink'
          }`}
        >
          {job.status}
        </span>
      </div>

      <p className="font-sans text-sm text-muted">
        {t('vision.task')}: <span className="text-ink">{job.task}</span>
      </p>

      {mock || job.result?.mock ? (
        <p className="font-sans text-sm text-red-800">{t('vision.mockNote')}</p>
      ) : null}

      {resultText ? (
        <pre className="max-h-96 overflow-auto bg-cream p-4 font-mono text-xs leading-relaxed text-ink">
          {resultText}
        </pre>
      ) : (
        <p className="font-sans text-sm text-muted">{t('vision.noPayload')}</p>
      )}
    </div>
  )
}
