import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BenefitPathMap } from '@/components/editorial/BenefitPathMap'
import { useCategories } from '@/hooks/usePerks'
import { JOURNEY_NODES, JOURNEY_PATH, AI_TIP } from '@/data/mockJourney'
import { getQuizQuestions } from '@/data/mockQuiz'
import {
  categoryLabel,
  journeyAiTipCurrent,
  journeyAiTipTop,
  journeyReasonAvailable,
  journeyReasonCompleted,
  journeyReasonCurrent,
  perkCountLabel,
  t,
} from '@/i18n'
import { useUserState } from '@/stores/userState'
import { POINTS, type JourneyNode } from '@/types'
import { cn } from '@/lib/utils'

const STATUS_BADGE: Record<JourneyNode['status'], string> = {
  locked: 'journey.statusLocked',
  available: 'journey.statusAvailable',
  current: 'journey.statusCurrent',
  completed: 'journey.statusCompleted',
}

function reasonForNode(node: JourneyNode, status: JourneyNode['status']): string {
  const pct = Math.round(node.affinityScore * 100)
  const label = categoryLabel(node.category)

  if (status === 'completed') {
    return journeyReasonCompleted(label, pct)
  }
  if (status === 'locked') {
    return node.reasonText
  }
  if (status === 'current') {
    return journeyReasonCurrent(label, pct, node.perkCount)
  }
  return journeyReasonAvailable(label, pct, node.perkCount)
}

function mergeNodes(
  categories: ReturnType<typeof useCategories>['data'],
  completedPathNodes: string[],
): JourneyNode[] {
  const merged = JOURNEY_NODES.map((template) => {
    const apiCat = categories?.categories?.find((c) => c.category === template.category)
    return {
      ...template,
      label: categoryLabel(template.category),
      affinityScore: apiCat?.score ?? template.affinityScore,
      perkCount: apiCat?.perk_count ?? template.perkCount,
    }
  })

  const withStatus = merged.map((node) => {
    if (completedPathNodes.includes(node.category)) {
      return { ...node, status: 'completed' as const }
    }
    if (node.status === 'locked') {
      return { ...node, status: 'locked' as const }
    }
    return { ...node, status: 'available' as const }
  })

  const eligible = withStatus.filter((n) => n.status === 'available')
  if (eligible.length === 0) {
    return withStatus.map((node) => ({
      ...node,
      reasonText: reasonForNode(node, node.status),
    }))
  }

  const currentCategory = eligible.reduce((best, node) =>
    node.affinityScore > best.affinityScore ? node : best,
  ).category

  return withStatus.map((node) => {
    let status: JourneyNode['status'] = node.status
    if (status === 'available') {
      status = node.category === currentCategory ? 'current' : 'available'
    }
    return {
      ...node,
      status,
      reasonText: reasonForNode(node, status),
    }
  })
}

export function JourneyPage() {
  const navigate = useNavigate()
  const { completedPathNodes, quizProgress } = useUserState()
  const { data: categoryData } = useCategories()

  const nodes = useMemo(
    () => mergeNodes(categoryData, completedPathNodes),
    [categoryData, completedPathNodes],
  )

  const aiTip = useMemo(() => {
    const current = nodes.find((n) => n.status === 'current')
    if (current) {
      const pct = Math.round(current.affinityScore * 100)
      return journeyAiTipCurrent(current.label, pct, current.perkCount)
    }
    const top = [...(categoryData?.categories ?? [])].sort((a, b) => b.score - a.score)[0]
    if (top) {
      return journeyAiTipTop(top.category, Math.round(top.score * 100))
    }
    return AI_TIP
  }, [nodes, categoryData])

  const topCategory =
    nodes.find((n) => n.status === 'current')?.category ??
    [...(categoryData?.categories ?? [])].sort((a, b) => b.score - a.score)[0]?.category ??
    'fitness'

  const [selected, setSelected] = useState<JourneyNode | null>(null)
  const activeNode = selected ?? nodes.find((n) => n.status === 'current') ?? nodes[0]

  const activeQuizTotal = activeNode ? getQuizQuestions(activeNode.category).length : 0
  const activeQuizScore = activeNode ? (quizProgress[activeNode.category] ?? 0) : 0
  const activeQuizPerfect = activeQuizTotal > 0 && activeQuizScore >= activeQuizTotal

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold">{t('journey.title')}</h1>
        <p className="mt-2 max-w-2xl text-muted">{t('journey.body')}</p>
      </div>

      <div className="grid gap-8 xl:grid-cols-[minmax(0,240px)_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-lg">{t('journey.aiTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-muted">{aiTip}</p>
            <Button
              variant="accent"
              size="sm"
              onClick={() => navigate(`/employee/explore?category=${topCategory}`)}
            >
              {t('journey.browseTop')}
            </Button>
          </CardContent>
        </Card>

        <div className="border border-ink/12 bg-paper p-6 md:p-8">
          <BenefitPathMap
            nodes={nodes}
            pathD={JOURNEY_PATH}
            selectedCategory={activeNode.category}
            onSelect={setSelected}
          />
        </div>
      </div>

      {activeNode && (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle>{activeNode.label}</CardTitle>
              <p className="font-mono text-sm tabular-nums text-muted">
                {(activeNode.affinityScore * 100).toFixed(0)}% · {perkCountLabel(activeNode.perkCount)}
                {activeQuizScore > 0 &&
                  ` · ${t('journey.quizPts')} ${activeQuizScore}/${activeQuizTotal}${activeQuizPerfect ? ' ✓' : ''}`}
              </p>
            </div>
            <span
              className={cn(
                'border px-2 py-1 font-mono text-[10px] uppercase tracking-wider',
                activeNode.status === 'current' && 'border-sienna text-sienna',
                activeNode.status === 'completed' && 'border-ink bg-ink text-cream',
                activeNode.status === 'locked' && 'border-dashed text-muted',
                activeNode.status === 'available' && 'border-ink/30 text-muted',
              )}
            >
              {t(STATUS_BADGE[activeNode.status])}
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-relaxed text-muted">{activeNode.reasonText}</p>
            <div className="flex flex-wrap gap-3">
              {activeNode.status !== 'locked' ? (
                <>
                  <Button asChild size="sm">
                    <Link to={`/employee/explore?category=${activeNode.category}`}>
                      {t('journey.viewPerks')}
                    </Link>
                  </Button>
                  <Button
                    size="sm"
                    variant={activeQuizPerfect ? 'default' : 'outline'}
                    onClick={() => navigate(`/employee/quiz/${activeNode.category}`)}
                  >
                    {activeQuizPerfect
                      ? `${t('journey.quizComplete')} · ${activeQuizScore}/${activeQuizTotal}`
                      : activeQuizScore > 0
                        ? `${t('journey.retakeQuiz')} · ${activeQuizScore}/${activeQuizTotal}`
                        : `${t('journey.quizPts')} +${POINTS.QUIZ_PERFECT} ${t('common.points')}`}
                  </Button>
                </>
              ) : (
                <p className="text-sm text-muted">{t('journey.lockedHint')}</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
