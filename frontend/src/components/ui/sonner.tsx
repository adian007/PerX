import { Toaster as Sonner } from 'sonner'

export function Toaster() {
  return (
    <Sonner
      theme="light"
      position="bottom-right"
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            'group toast rounded-none border border-[#1A1A1A]/12 bg-cream text-ink shadow-none font-sans',
          description: 'text-muted',
          actionButton: 'bg-ink text-cream rounded-none',
          cancelButton: 'bg-paper text-ink rounded-none border border-[#1A1A1A]/12',
        },
      }}
    />
  )
}
