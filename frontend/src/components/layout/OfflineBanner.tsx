import { useEffect, useState } from 'react'
import { t } from '@/i18n'

export function OfflineBanner() {
  const [offline, setOffline] = useState(
    typeof navigator !== 'undefined' ? !navigator.onLine : false,
  )

  useEffect(() => {
    const goOnline = () => setOffline(false)
    const goOffline = () => setOffline(true)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  if (!offline) return null

  return (
    <div
      role="status"
      className="border-b border-amber-700/30 bg-amber-100 px-4 py-2 text-center font-sans text-sm text-amber-950"
    >
      {t('offline.banner')}
    </div>
  )
}
