import { useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getQuizQuestions } from '@/data/mockQuiz'
import { usePerkActions } from '@/hooks/usePerkActions'
import { categoryLabel, t } from '@/i18n'
import { useUserState } from '@/stores/userState'
import { POINTS } from '@/types'
import { cn } from '@/lib/utils'

export function QuizPage() {
  const { category } = useParams<{ category?: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const bonusMode = searchParams.get('bonus') === 'true'
  const perkId = searchParams.get('perkId')

  const cat = category ?? 'default'
  const questions = getQuizQuestions(category)
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<boolean | null>(null)
  const correctCountRef = useRef(0)
  const [finished, setFinished] = useState(false)
  const [finalScore, setFinalScore] = useState(0)

  const { setQuizScore, quizProgress, syncFromServer } = useUserState()
  const savedScore = quizProgress[cat] ?? 0
  const { claimPerk } = usePerkActions()
  const current = questions[index]

  const handleAnswer = (answer: boolean) => {
    if (selected !== null) return
    setSelected(answer)
    if (answer === current.answer) {
      correctCountRef.current += 1
    }
  }

  const handleContinue = async () => {
    if (index < questions.length - 1) {
      setIndex((i) => i + 1)
      setSelected(null)
      return
    }

    const score = correctCountRef.current

    setFinalScore(score)
    setFinished(true)

    const perfect = score === questions.length

    await setQuizScore(cat, score, questions.length)

    if (perfect) {
      toast.success(t('quiz.completeToast'), {
        description: (
          <span className="font-mono tabular-nums">
            +{POINTS.QUIZ_PERFECT} {t('common.points')} · {t('quiz.perfectScore')}
          </span>
        ),
      })
    } else {
      toast(`${t('quiz.completeToast')}: ${score}/${questions.length}`)
    }

    if (bonusMode && perkId && score >= Math.ceil(questions.length * 0.6)) {
      try {
        await claimPerk({
          id: perkId,
          name: t('quiz.selectedPerk'),
          category: cat,
          short_description: '',
          employee_price_formatted: '',
          employee_price_cents: 0,
          tags: [],
        })
        await syncFromServer()
        toast.success(t('quiz.bonusApplied'), {
          description: (
            <span className="font-mono tabular-nums">
              +{POINTS.QUIZ_BONUS} {t('quiz.bonusPts')}
            </span>
          ),
        })
        navigate('/employee')
      } catch {
        navigate('/employee/explore')
      }
    }
  }

  if (finished && !(bonusMode && perkId)) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('quiz.completeTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="font-mono tabular-nums">
              {t('quiz.score')}: {finalScore}/{questions.length}
            </p>
            <p className="text-sm text-muted">
              {t('quiz.progressSaved')} {categoryLabel(cat)}.{' '}
              {finalScore >= Math.ceil(questions.length * 0.6)
                ? t('quiz.pathComplete')
                : t('quiz.passHint')}{' '}
              {finalScore === questions.length
                ? `${t('quiz.perfectPts')}${POINTS.QUIZ_PERFECT}${t('quiz.ptsAwarded')}`
                : finalScore >= Math.ceil(questions.length * 0.6)
                  ? `${t('quiz.score')}: ${finalScore}/${questions.length}.`
                  : `${t('quiz.best')}: ${Math.max(savedScore, finalScore)}/${questions.length}.`}
            </p>
            <Button onClick={() => navigate(-1)}>{t('common.back')}</Button>
            <Button variant="outline" onClick={() => navigate('/employee/selections')}>
              {t('quiz.viewSelections')}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">

      <div>
        <h1 className="font-display text-3xl font-semibold">{t('quiz.title')}</h1>
        <p className="mt-2 capitalize text-muted">
          {category ? categoryLabel(category) : t('quiz.general')} · {t('quiz.question')}{' '}
          {index + 1} {t('quiz.of')} {questions.length}
          {savedScore > 0 && ` · ${t('quiz.best')}: ${savedScore}/${questions.length}`}
          {bonusMode && t('quiz.bonusRequired')}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl leading-snug">{current.question}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex gap-3">
            <Button
              variant={selected === true ? (current.answer ? 'default' : 'accent') : 'outline'}
              className={cn(
                selected === true &&
                  (current.answer ? 'bg-ink text-cream' : 'border-sienna text-sienna'),
              )}
              onClick={() => handleAnswer(true)}
              disabled={selected !== null}
            >
              {t('common.true')}
            </Button>
            <Button
              variant={selected === false ? (current.answer ? 'default' : 'accent') : 'outline'}
              className={cn(
                selected === false &&
                  (current.answer ? 'border-sienna text-sienna' : 'bg-ink text-cream'),
              )}
              onClick={() => handleAnswer(false)}
              disabled={selected !== null}
            >
              {t('common.false')}
            </Button>
          </div>

          {selected !== null && (
            <div className="space-y-2 border-t border-[#1A1A1A]/12 pt-4">
              <p
                className={cn(
                  'font-sans font-medium',
                  selected === current.answer ? 'text-ink' : 'text-sienna',
                )}
              >
                {selected === current.answer ? t('common.correct') : t('common.incorrect')}
              </p>
              <p className="text-sm text-muted">{current.fact}</p>
            </div>
          )}

          {selected !== null && (
            <Button onClick={() => void handleContinue()}>
              {index < questions.length - 1 ? t('common.continue') : t('common.finish')}
            </Button>
          )}
        </CardContent>
      </Card>

      <Button variant="ghost" onClick={() => navigate(-1)}>
        {t('quiz.skip')}
      </Button>
    </div>
  )
}
