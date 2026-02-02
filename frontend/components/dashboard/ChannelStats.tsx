'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, Mail, Phone } from 'lucide-react'

interface ChannelStat {
  channel: string
  sent: number
  responses: number
  response_rate: number
}

const channelIcons: Record<string, any> = {
  whatsapp: MessageSquare,
  email: Mail,
  sms: Phone,
}

const channelNames: Record<string, string> = {
  whatsapp: 'WhatsApp',
  email: 'Email',
  sms: 'SMS',
}

const channelColors: Record<string, string> = {
  whatsapp: 'bg-green-500',
  email: 'bg-blue-500',
  sms: 'bg-purple-500',
}

export default function ChannelStats() {
  const [channels, setChannels] = useState<ChannelStat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchChannels()
  }, [])

  const fetchChannels = async () => {
    try {
      const response = await fetch('/api/stats/by-channel')
      if (response.ok) {
        const data = await response.json()
        setChannels(data)
      }
    } catch (error) {
      console.error('Failed to fetch channel stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 bg-gray-100 rounded-lg animate-pulse"></div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {channels.map((channel) => {
        const Icon = channelIcons[channel.channel] || MessageSquare
        
        return (
          <div key={channel.channel} className="bg-gray-50 rounded-lg p-4 text-center">
            <div className={`w-10 h-10 ${channelColors[channel.channel]} rounded-full flex items-center justify-center mx-auto mb-3`}>
              <Icon className="w-5 h-5 text-white" />
            </div>
            
            <div className="text-lg font-semibold text-gray-900">
              {channel.sent.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 mb-2">נשלחו</div>
            
            <div className="text-sm text-gray-600">
              {channel.responses} תגובות
            </div>
            <div className="text-xs text-gray-400">
              {channel.response_rate}% המרה
            </div>
          </div>
        )
      })}
    </div>
  )
}
