import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { ApiError, fetchOnboardingExplanation, submitOnboarding } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { categoryLabel, t } from '@/i18n'
import { useAuthStore } from '@/stores/authStore'

const LIFESTYLE_TAGS = [
  'gym_goer',
  'remote_worker',
  'cyclist',
  'foodie',
  'traveler',
  'parent',
  'night_owl',
] as const

const LIFESTYLE_LABELS: Record<(typeof LIFESTYLE_TAGS)[number], string> = {
  gym_goer: 'Palestër',
  remote_worker: 'Punë nga shtëpia',
  cyclist: 'Çiklist',
  foodie: 'Gastronom',
  traveler: 'Udhëtar',
  parent: 'Prind',
  night_owl: 'Natë vonë',
}

const CATEGORIES = ['fitness', 'wellness', 'food', 'travel', 'transport'] as const

const FAMILY_OPTIONS = [
  { value: 'single', labelKey: 'onboarding.familySingle' },
  { value: 'couple', labelKey: 'onboarding.familyCouple' },
  { value: 'family', labelKey: 'onboarding.familyFamily' },
] as const

const BUDGET_LEVELS = [
  { value: 'low', labelKey: 'onboarding.sensitivityLow' },
  { value: 'medium', labelKey: 'onboarding.sensitivityMedium' },
  { value: 'high', labelKey: 'onboarding.sensitivityHigh' },
] as const

const STEPS = [
  { titleKey: 'onboarding.lifestyleTitle', descKey: 'onboarding.lifestyleDesc' },
  { titleKey: 'onboarding.categoriesTitle', descKey: 'onboarding.categoriesDesc' },
  { titleKey: 'onboarding.budgetTitle', descKey: 'onboarding.budgetDesc' },
  { titleKey: 'onboarding.wellnessTitle', descKey: 'onboarding.wellnessDesc' },
  { titleKey: 'onboarding.familyTitle', descKey: 'onboarding.familyDesc' },
] as const

export function OnboardingPage() {
  const navigate = useNavigate()
  const { setOnboardingCompleted } = useAuthStore()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [explanation, setExplanation] = useState<string | null>(null)

  const [lifestyleTags, setLifestyleTags] = useState<string[]>([])
  const [preferredCategories, setPreferredCategories] = useState<string[]>([])
  const [budgetSensitivity, setBudgetSensitivity] = useState('medium')
  const [wellnessPriority, setWellnessPriority] = useState(7)
  const [familySituation, setFamilySituation] = useState('single')

  const toggleTag = (tag: string, list: string[], setList: (v: string[]) => void) => {
    setList(list.includes(tag) ? list.filter((item) => item !== tag) : [...list, tag])
  }

  const canContinue = () => {
    if (step === 0) return lifestyleTags.length > 0
    if (step === 1) return preferredCategories.length > 0
    return true
  }

  const pollExplanation = async () => {
    for (let i = 0; i < 10; i++) {
      const result = await fetchOnboardingExplanation()
      if (result.ready && result.explanation) {
        setExplanation(result.explanation)
        return
      }
      await new Promise((r) => setTimeout(r, 1500))
    }
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      const result = await submitOnboarding({
        lifestyle_tags: lifestyleTags,
        preferred_categories: preferredCategories,
        budget_sensitivity: budgetSensitivity,
        wellness_priority: wellnessPriority,
        family_situation: familySituation,
      })
      setOnboardingCompleted(result.onboarding_completed)
      if (result.explanation) {
        setExplanation(result.explanation)
      } else {
        await pollExplanation()
      }
      toast.success(t('onboarding.saved'), { description: t('onboarding.savedDesc') })
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t('onboarding.saveFailed')
      toast.error(t('onboarding.failed'), { description: message })
    } finally {
      setLoading(false)
    }
  }

  if (explanation) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="font-display text-2xl">{t('onboarding.welcomeTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="leading-relaxed text-muted">{explanation}</p>
            <Button className="w-full" onClick={() => navigate('/employee')}>
              {t('onboarding.exploreBenefits')}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-sienna">
          {t('onboarding.step')} {step + 1} {t('onboarding.of')} {STEPS.length}
        </p>
        <h1 className="mt-2 font-display text-3xl font-semibold">{t(STEPS[step].titleKey)}</h1>
        <p className="mt-2 text-muted">{t(STEPS[step].descKey)}</p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-6">
          {step === 0 && (
            <div className="flex flex-wrap gap-2">
              {LIFESTYLE_TAGS.map((tag) => (
                <Button
                  key={tag}
                  type="button"
                  size="sm"
                  variant={lifestyleTags.includes(tag) ? 'default' : 'outline'}
                  onClick={() => toggleTag(tag, lifestyleTags, setLifestyleTags)}
                >
                  {LIFESTYLE_LABELS[tag]}
                </Button>
              ))}
            </div>
          )}

          {step === 1 && (
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <Button
                  key={cat}
                  type="button"
                  size="sm"
                  variant={preferredCategories.includes(cat) ? 'default' : 'outline'}
                  onClick={() => toggleTag(cat, preferredCategories, setPreferredCategories)}
                >
                  {categoryLabel(cat)}
                </Button>
              ))}
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-wrap gap-2">
              {BUDGET_LEVELS.map(({ value, labelKey }) => (
                <Button
                  key={value}
                  type="button"
                  size="sm"
                  variant={budgetSensitivity === value ? 'default' : 'outline'}
                  onClick={() => setBudgetSensitivity(value)}
                >
                  {t(labelKey)}
                </Button>
              ))}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-2">
              <input
                type="range"
                min={1}
                max={10}
                value={wellnessPriority}
                onChange={(e) => setWellnessPriority(Number(e.target.value))}
                className="w-full accent-sienna"
              />
              <p className="font-mono text-sm tabular-nums">{wellnessPriority} / 10</p>
            </div>
          )}

          {step === 4 && (
            <div className="flex flex-wrap gap-2">
              {FAMILY_OPTIONS.map(({ value, labelKey }) => (
                <Button
                  key={value}
                  type="button"
                  size="sm"
                  variant={familySituation === value ? 'default' : 'outline'}
                  onClick={() => setFamilySituation(value)}
                >
                  {t(labelKey)}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          disabled={step === 0 || loading}
          onClick={() => setStep((s) => s - 1)}
        >
          {t('common.back')}
        </Button>
        {step < STEPS.length - 1 ? (
          <Button type="button" disabled={!canContinue()} onClick={() => setStep((s) => s + 1)}>
            {t('common.continue')}
          </Button>
        ) : (
          <Button type="button" disabled={loading} onClick={() => void handleSubmit()}>
            {loading ? t('onboarding.saving') : t('onboarding.finishSetup')}
          </Button>
        )}
      </div>
    </div>
  )
}
