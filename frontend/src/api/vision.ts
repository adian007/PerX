import { getAuthHeaders, ApiError } from '@/api/client'

const baseUrl = import.meta.env.VITE_API_URL ?? ''

function buildUrl(path: string): string {
  const origin = baseUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173')
  return new URL(path, origin).toString()
}

interface ApiEnvelope<T> {
  data: T
}

export type VisionTask = 'lifestyle' | 'receipt' | 'ocr' | 'catalog_tag' | 'visual_search'
export type VisionJobStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface VisionJob {
  id: string
  task: VisionTask
  status: VisionJobStatus
  result: Record<string, unknown> | null
  error: Record<string, unknown> | null
  created_at: string
  updated_at: string
  completed_at: string | null
  expires_at: string | null
}

export interface VisionAnalyzeResponse {
  job: VisionJob
  source: string
}

export interface VisionAnalyzeRequest {
  task: VisionTask
  image_url?: string
  image_base64?: string
  metadata?: Record<string, unknown>
  async_mode?: boolean
}

async function visionRequest<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(buildUrl(path), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  })

  const raw = await res.text()
  const body = raw
    ? (JSON.parse(raw) as ApiEnvelope<T> & { error?: { code?: string; message?: string } })
    : ({} as ApiEnvelope<T> & { error?: { code?: string; message?: string } })
  if (!res.ok) {
    throw new ApiError(body.error?.code ?? 'VISION_ERROR', body.error?.message ?? 'Vision request failed', res.status)
  }
  return (body as ApiEnvelope<T>).data
}

export async function createVisionJob(payload: VisionAnalyzeRequest): Promise<VisionAnalyzeResponse> {
  return visionRequest<VisionAnalyzeResponse>('/api/v1/vision/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getVisionJob(jobId: string): Promise<VisionJob> {
  return visionRequest<VisionJob>(`/api/v1/vision/jobs/${jobId}`, { method: 'GET' })
}
