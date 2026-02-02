'use client'

import { useState, useEffect } from 'react'

interface FunnelStage {
  stage: string
  count: number
  percent: number
}

export default function FunnelChart() {
  const [stages, setStages] = useState<FunnelStage[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFunnel()
  }, [])

  const fetchFunnel = async () => {
    try {
      const response = await fetch('/api/stats/funnel')
      if (response.ok) {
        const data = await response.json()
        setStages(data)
      }
    } catch (error) {
      console.error('Failed to fetch funnel:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-12 bg-gray-100 rounded animate-pulse"></div>
        ))}
      </div>
    )
  }

  const maxCount = Math.max(...stages.map(s => s.count), 1)

  return (
    <div className="space-y-4">
      {stages.map((stage, index) => (
        <div key={stage.stage} className="relative">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-700">{stage.stage}</span>
            <span className="text-sm text-gray-500">
              {stage.count.toLocaleString()} ({stage.percent}%)
            </span>
          </div>
          
          {/* Bar */}
          <div className="h-8 bg-gray-100 rounded-lg overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                index === 0 ? 'bg-blue-500' :
                index === 1 ? 'bg-purple-500' :
                index === 2 ? 'bg-orange-500' :
                'bg-green-500'
              }`}
              style={{ width: `${(stage.count / maxCount) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
