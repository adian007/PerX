import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import {
  ApiError,
  addToWishlist,
  type ChatAction,
  type ChatHistoryMessage,
  sendChatMessage,
} from '@/api/client'
import { chatEn, CHAT_SAMPLE_PROMPTS } from '@/i18n/chat-en'
import { t } from '@/i18n'
import { useUserState } from '@/stores/userState'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  source?: string
  actions?: ChatAction[]
}

export function AiConsultantDrawer() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { displayName, syncFromServer } = useUserState()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: `${chatEn.hello} ${displayName}. ${chatEn.intro}`,
    },
  ])
  const [loading, setLoading] = useState(false)

  const handleAction = async (action: ChatAction) => {
    if (action.type === 'link' && action.href) {
      setOpen(false)
      navigate(action.href)
      return
    }

    if (action.type === 'save_perk' && action.perk_id) {
      try {
        await addToWishlist(action.perk_id)
        await queryClient.invalidateQueries({ queryKey: ['wishlist'] })
        await syncFromServer()
        toast.success(action.perk_name ?? t('perks.wishlistAdd'))
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : t('perks.wishlistFailed')
        toast.error(t('perks.wishlistFailed'), { description: message })
      }
    }
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return
    const userMsg = text.trim()
    const history: ChatHistoryMessage[] = messages
      .slice(-8)
      .map(({ role, content }) => ({ role, content }))

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const data = await sendChatMessage(userMsg, history)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          source: data.source,
          actions: data.actions?.length ? data.actions : undefined,
        },
      ])
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : chatEn.unavailable
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: message, source: 'error' },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Button
        variant="outline"
        className="fixed bottom-20 right-4 z-50 md:bottom-6"
        onClick={() => setOpen(true)}
      >
        {t('ai.askPerx')}
      </Button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="flex w-full flex-col sm:max-w-md">
          <SheetHeader>
            <SheetTitle>{chatEn.title}</SheetTitle>
            <SheetDescription>{chatEn.subtitle}</SheetDescription>
          </SheetHeader>

          <div className="flex flex-1 flex-col gap-4 overflow-hidden">
            <div className="flex flex-wrap gap-2">
              {CHAT_SAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void sendMessage(prompt)}
                  disabled={loading}
                  className="border border-[#1A1A1A]/12 bg-cream px-3 py-1.5 text-left text-xs hover:bg-ink hover:text-cream rounded-none"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-1">
              {messages.map((msg, i) => (
                <div key={`${msg.role}-${i}`}>
                  <div
                    className={
                      msg.role === 'user'
                        ? 'ml-8 border border-[#1A1A1A]/12 bg-ink p-3 text-sm text-cream'
                        : 'mr-8 border border-[#1A1A1A]/12 bg-cream p-3 text-sm text-ink'
                    }
                  >
                    {msg.content}
                  </div>
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="mr-8 mt-2 flex flex-wrap gap-2">
                      {msg.actions.map((action, actionIndex) => (
                        <Button
                          key={`${action.type}-${action.perk_id ?? action.href ?? actionIndex}`}
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-auto whitespace-normal px-2 py-1 text-xs"
                          onClick={() => void handleAction(action)}
                        >
                          {action.label}
                        </Button>
                      ))}
                    </div>
                  )}
                  {msg.source && msg.role === 'assistant' && msg.source !== 'error' && (
                    <p className="mr-8 mt-1 text-right font-mono text-[10px] uppercase text-muted">
                      {chatEn.via} {msg.source}
                    </p>
                  )}
                </div>
              ))}
              {loading && <p className="text-sm text-muted">{chatEn.thinking}</p>}
            </div>

            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                void sendMessage(input)
              }}
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={chatEn.placeholder}
                className="flex-1"
                disabled={loading}
              />
              <Button type="submit" disabled={loading}>
                {chatEn.send}
              </Button>
            </form>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
