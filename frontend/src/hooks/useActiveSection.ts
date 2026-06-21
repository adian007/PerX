import { useEffect, useState } from 'react'
import type { LandingSectionId } from '@/components/landing/landingMotion'

export function useActiveSection(sectionIds: LandingSectionId[]) {
  const [activeId, setActiveId] = useState<LandingSectionId>(sectionIds[0])

  useEffect(() => {
    const elements = sectionIds
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null)

    if (elements.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)

        const top = visible[0]
        if (top?.target.id) {
          setActiveId(top.target.id as LandingSectionId)
        }
      },
      { root: null, threshold: [0.35, 0.5, 0.65] },
    )

    for (const el of elements) {
      observer.observe(el)
    }

    return () => observer.disconnect()
  }, [sectionIds])

  return activeId
}
