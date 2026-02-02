'use client'

import { ReactNode } from 'react'

interface StatsCardProps {
  title: string
  value: number
  icon: ReactNode
  color: 'blue' | 'purple' | 'orange' | 'green'
  loading?: boolean
  change?: number
}

const colorClasses = {
  blue: 'bg-blue-50 text-blue-600',
  purple: 'bg-purple-50 text-purple-600',
  orange: 'bg-orange-50 text-orange-600',
  green: 'bg-green-50 text-green-600',
}

export default function StatsCard({ 
  title, 
  value, 
  icon, 
  color, 
  loading,
  change 
}: StatsCardProps) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        {change !== undefined && (
          <span className="text-sm text-gray-500">
            {change}%
          </span>
        )}
      </div>
      
      <div>
        {loading ? (
          <div className="h-8 w-20 bg-gray-200 rounded animate-pulse"></div>
        ) : (
          <div className="text-3xl font-bold text-gray-900">
            {value.toLocaleString()}
          </div>
        )}
        <div className="text-sm text-gray-500 mt-1">{title}</div>
      </div>
    </div>
  )
}
