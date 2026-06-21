import { t } from '@/i18n'

interface DemoBannerProps {
  messageKey: string
}

export function DemoBanner({ messageKey }: DemoBannerProps) {
  return (
    <div className="border border-amber-700/30 bg-amber-50 px-4 py-3 font-sans text-sm text-amber-900">
      {t(messageKey)}
    </div>
  )
}
