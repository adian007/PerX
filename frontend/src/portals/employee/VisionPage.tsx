import { useEffect, useState } from 'react'
import { VisionJobStatus, VisionUpload } from '@/components/vision'
import type { VisionAnalyzeResponse, VisionJob, VisionTask } from '@/api/vision'
import { getVisionJob } from '@/api/vision'
import { getAuthHeaders } from '@/api/client'
import { t } from '@/i18n'

const VISION_TASKS: VisionTask[] = [
  'lifestyle',
  'receipt',
  'ocr',
  'catalog_tag',
  'visual_search',
]

interface VisionHealth {
  enabled: boolean
  service_url: string
}

async function fetchVisionHealth(): Promise<VisionHealth | null> {
  try {
    const base = import.meta.env.VITE_API_URL ?? ''
    const origin = base || window.location.origin
    const res = await fetch(new URL('/api/v1/vision/health', origin), {
      headers: getAuthHeaders(),
    })
    if (!res.ok) return null
    const body = (await res.json()) as { data: VisionHealth }
    return body.data
  } catch {
    return null
  }
}

function isMockSource(source: string | null): boolean {
  return source === 'backend-mock' || source === 'backend-fallback'
}

export function VisionPage() {
  const [selectedTask, setSelectedTask] = useState<VisionTask>('ocr')
  const [visionJob, setVisionJob] = useState<VisionJob | null>(null)
  const [source, setSource] = useState<string | null>(null)
  const [cvHealth, setCvHealth] = useState<VisionHealth | null>(null)

  useEffect(() => {
    void fetchVisionHealth().then(setCvHealth)
  }, [])

  async function handleSubmitted(payload: VisionAnalyzeResponse) {
    setVisionJob(payload.job)
    setSource(payload.source)
    const latest = await getVisionJob(payload.job.id)
    setVisionJob(latest)
  }

  const mockActive = isMockSource(source)
  const cvOffline = cvHealth && !cvHealth.enabled

  return (
    <div className="mx-auto max-w-3xl space-y-10 pb-8">
      <header className="space-y-3">
        <p className="font-sans text-xs uppercase tracking-[0.2em] text-sienna">
          {t('visionPage.eyebrow')}
        </p>
        <h1 className="font-display text-4xl font-bold italic md:text-5xl">{t('visionPage.title')}</h1>
        <p className="font-sans text-lg text-muted">{t('visionPage.body')}</p>
      </header>

      {cvOffline ? (
        <div className="border border-amber-700/30 bg-amber-50 px-4 py-3 font-sans text-sm text-amber-900">
          {t('visionPage.cvOffline')}
        </div>
      ) : null}

      {mockActive ? (
        <div className="border border-red-700/30 bg-red-50 px-4 py-3 font-sans text-sm text-red-900">
          {t('visionPage.mockActive')}
        </div>
      ) : null}

      <section className="space-y-4">
        <p className="font-sans text-sm font-medium text-ink">{t('visionPage.chooseTask')}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {VISION_TASKS.map((task) => {
            const active = selectedTask === task
            return (
              <button
                key={task}
                type="button"
                onClick={() => setSelectedTask(task)}
                className={`border p-4 text-left transition-colors ${
                  active
                    ? 'border-ink bg-ink text-cream'
                    : 'border-[#1A1A1A]/12 bg-paper text-ink hover:bg-cream'
                }`}
              >
                <p className="font-display text-lg font-semibold">
                  {t(`visionPage.tasks.${task}.title`)}
                </p>
                <p className={`mt-1 font-sans text-sm ${active ? 'text-cream/80' : 'text-muted'}`}>
                  {t(`visionPage.tasks.${task}.description`)}
                </p>
                <p className={`mt-2 font-sans text-xs ${active ? 'text-cream/60' : 'text-muted'}`}>
                  {t('visionPage.bestFor')}: {t(`visionPage.tasks.${task}.bestFor`)}
                </p>
              </button>
            )
          })}
        </div>
      </section>

      <section className="space-y-4">
        <VisionUpload
          key={selectedTask}
          defaultTask={selectedTask}
          onSubmitted={(payload) => void handleSubmitted(payload)}
        />
        {source ? (
          <p className="font-mono text-xs text-muted">
            {t('visionPage.processedVia')}: {source}
            {source === 'cv-service' ? ` ${t('visionPage.realAnalysis')}` : ''}
          </p>
        ) : null}
        <VisionJobStatus job={visionJob} mock={mockActive || Boolean(visionJob?.result?.mock)} />
      </section>
    </div>
  )
}
