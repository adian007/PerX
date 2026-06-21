import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { createVisionJob, type VisionTask, type VisionAnalyzeResponse } from '@/api/vision'
import { t } from '@/i18n'

interface VisionUploadProps {
  defaultTask?: VisionTask
  onSubmitted?: (response: VisionAnalyzeResponse) => void
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result
      if (typeof result !== 'string') {
        reject(new Error(t('vision.chooseFile')))
        return
      }
      const base64 = result.includes(',') ? result.split(',')[1] : result
      resolve(base64)
    }
    reader.onerror = () => reject(new Error(t('vision.chooseFile')))
    reader.readAsDataURL(file)
  })
}

export function VisionUpload({ defaultTask = 'lifestyle', onSubmitted }: VisionUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [task] = useState<VisionTask>(defaultTask)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleFileChange(next: File | null) {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    setFile(next)
    setPreviewUrl(next ? URL.createObjectURL(next) : null)
    setError(null)
  }

  async function handleSubmit() {
    if (!file) {
      setError(t('vision.chooseFile'))
      return
    }

    setError(null)
    setLoading(true)
    try {
      const image_base64 = await readFileAsBase64(file)
      const res = await createVisionJob({
        task,
        image_base64,
        metadata: { source: 'frontend-vision-upload', filename: file.name },
      })
      onSubmitted?.(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('vision.requestFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 border border-border bg-paper p-6">
      <div className="space-y-2">
        <label className="block font-sans text-sm text-muted">{t('vision.uploadLabel')}</label>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          capture="environment"
          className="block w-full font-sans text-sm file:mr-4 file:border file:border-border file:bg-cream file:px-4 file:py-2 file:font-sans file:text-sm file:text-ink hover:file:bg-paper"
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
        />
        <p className="font-sans text-xs text-muted">{t('vision.uploadHint')}</p>
      </div>

      {previewUrl ? (
        <img
          src={previewUrl}
          alt={t('vision.previewAlt')}
          className="max-h-64 w-full border border-border object-contain bg-cream"
        />
      ) : null}

      <Button onClick={() => void handleSubmit()} disabled={loading || !file}>
        {loading ? t('vision.analyzing') : t('vision.analyze')}
      </Button>

      {error ? (
        <div className="border border-red-700/30 bg-red-50 px-4 py-3 font-sans text-sm text-red-900">
          {error}
        </div>
      ) : null}
    </div>
  )
}
