'use client'

import { useState, useEffect } from 'react'
import { 
  Search, Users, Send, Download, TrendingUp, 
  ArrowUpRight, ArrowDownRight, Activity
} from 'lucide-react'
import StatsCard from '@/components/dashboard/StatsCard'
import FunnelChart from '@/components/dashboard/FunnelChart'
import ChannelStats from '@/components/dashboard/ChannelStats'

interface OverviewStats {
  scanned: number
  matched: number
  sent: number
  installations: number
}

export default function DashboardPage() {
  const [stats, setStats] = useState<OverviewStats>({
    scanned: 0,
    matched: 0,
    sent: 0,
    installations: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/stats/overview')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* כותרת */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">דאשבורד</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Activity className="w-4 h-4" />
          <span>עודכן לאחרונה: עכשיו</span>
        </div>
      </div>

      {/* כרטיסי סטטיסטיקות */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="נסרקו"
          value={stats.scanned}
          icon={<Search className="w-6 h-6" />}
          color="blue"
          loading={loading}
        />
        <StatsCard
          title="התאמה נמצאה"
          value={stats.matched}
          icon={<Users className="w-6 h-6" />}
          color="purple"
          loading={loading}
          change={stats.scanned > 0 ? Math.round((stats.matched / stats.scanned) * 100) : 0}
        />
        <StatsCard
          title="נשלחו פניות"
          value={stats.sent}
          icon={<Send className="w-6 h-6" />}
          color="orange"
          loading={loading}
        />
        <StatsCard
          title="התקנות פעילות"
          value={stats.installations}
          icon={<Download className="w-6 h-6" />}
          color="green"
          loading={loading}
        />
      </div>

      {/* Funnel וסטטיסטיקות ערוצים */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">מסלול ההמרה (Funnel)</h2>
          <FunnelChart />
        </div>
        
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">פילוח לפי ערוץ</h2>
          <ChannelStats />
        </div>
      </div>

      {/* סריקות פעילות */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">סריקות פעילות</h2>
          <a href="/scans" className="text-primary-600 hover:text-primary-700 text-sm">
            ראה הכל ←
          </a>
        </div>
        
        <ActiveScans />
      </div>
    </div>
  )
}

function ActiveScans() {
  const [scans, setScans] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchActiveScans()
    const interval = setInterval(fetchActiveScans, 5000) // עדכון כל 5 שניות
    return () => clearInterval(interval)
  }, [])

  const fetchActiveScans = async () => {
    try {
      const response = await fetch('/api/stats/active-scans')
      if (response.ok) {
        const data = await response.json()
        setScans(data)
      }
    } catch (error) {
      console.error('Failed to fetch active scans:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-4 text-gray-500">טוען...</div>
  }

  if (scans.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Search className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>אין סריקות פעילות כרגע</p>
        <a href="/scans" className="text-primary-600 hover:underline text-sm">
          התחל סריקה חדשה
        </a>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {scans.map((scan) => (
        <div key={scan.id} className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">{scan.name}</span>
            <span className="text-sm text-gray-500">
              {scan.scanned_count}/{scan.total_urls} URLs
            </span>
          </div>
          
          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div 
              className="bg-primary-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${scan.progress_percent}%` }}
            />
          </div>
          
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>נמצאו: {scan.matched_count} התאמות</span>
            <span>{Math.round(scan.progress_percent)}%</span>
          </div>
        </div>
      ))}
    </div>
  )
}
