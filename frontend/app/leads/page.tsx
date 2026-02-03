'use client'

import { useState, useEffect, useMemo } from 'react'
import { Users, Search, Mail, MessageSquare, Phone, ExternalLink, Send, Calculator, X, Settings, CheckSquare, Square, Ban, Clock, CheckCircle, XCircle, RefreshCw, AlertCircle, Inbox, MailCheck, Bot, SendHorizontal, Eye, Zap } from 'lucide-react'

const API_URL = ''

// ========== Types ==========

interface Lead {
  id: number
  domain: string
  site_name: string
  status: string
  category: string | null
  contact_info: {
    whois_email?: string
    whois_name?: string
    whois_phone?: string
    emails?: string[]
    phones?: string[]
  }
  ai_status: {
    calc_score?: number
    calc_reason?: string
  }
  recommended_calc_id: number | null
  recommended_calc_name?: string
  source_campaign_id: number | null
  created_at: string
  last_contacted_at?: string
  last_response_at?: string
  outreach_count?: number
}

interface EmailTemplate {
  id: number
  name: string
  subject: string
  body_text: string
  category: string
}

interface OutreachStats {
  today: { pending: number; sent: number; failed: number }
  total: { pending: number; sent: number }
  leads: { can_contact: number; waiting_response: number; responded: number }
  settings: { daily_limit: number; start_hour: number; end_hour: number; interval_minutes: number; enabled: boolean }
}

interface QueueItem {
  id: number
  lead_id: number
  lead_domain: string
  to_email: string
  subject: string
  scheduled_at: string
  status: string
}

interface Message {
  id: number
  lead_id: number
  channel: string
  direction: string
  message_body: string
  subject?: string
  status: string
  is_auto_reply: boolean
  sent_at: string
  opens_count?: number
  clicks?: any[]
  thread_id?: string
  to_email?: string
  domain?: string
}

interface GroupedMessages {
  email: string
  messages: Message[]
  domains: string[]
  total_sent: number
  last_sent: string
}

interface PendingReply {
  id: number
  communication_id: number | null
  lead_id: number | null
  suggested_reply: string
  suggested_subject?: string
  ai_reasoning?: string
  status: string
  created_at: string
  original_message?: string
  original_subject?: string
  sender_email?: string
  lead_domain?: string
  scenario_name?: string
  scenario_category?: string
  match_confidence?: string
  match_method?: string
}

interface PendingStats {
  pending: number
  approved: number
  rejected: number
  auto_sent: number
}

// ========== Config ==========

const statusConfig: Record<string, { color: string; label: string; canContact: boolean }> = {
  new: { color: 'bg-gray-100 text-gray-700', label: 'חדש', canContact: true },
  matched: { color: 'bg-green-100 text-green-700', label: 'נמצאה התאמה', canContact: true },
  queued: { color: 'bg-yellow-100 text-yellow-700', label: 'בתור', canContact: false },
  contacted: { color: 'bg-blue-100 text-blue-700', label: 'נשלח מייל', canContact: false },
  responded: { color: 'bg-purple-100 text-purple-700', label: 'השיב', canContact: true },
  installed: { color: 'bg-emerald-100 text-emerald-700', label: 'התקין', canContact: true },
  bounced: { color: 'bg-red-100 text-red-700', label: 'חזר', canContact: false },
  blacklisted: { color: 'bg-gray-800 text-white', label: 'חסום', canContact: false },
  rejected: { color: 'bg-red-100 text-red-700', label: 'נדחה', canContact: false }
}

type QuickFilter = 'all' | 'ready' | 'waiting' | 'responded' | 'blocked'

const quickFilters: { value: QuickFilter; label: string; icon: React.ReactNode }[] = [
  { value: 'all', label: 'הכל', icon: <Users className="w-4 h-4" /> },
  { value: 'ready', label: 'מוכנים', icon: <Mail className="w-4 h-4" /> },
  { value: 'waiting', label: 'ממתינים', icon: <Clock className="w-4 h-4" /> },
  { value: 'responded', label: 'השיבו', icon: <CheckCircle className="w-4 h-4" /> },
  { value: 'blocked', label: 'חסומים', icon: <Ban className="w-4 h-4" /> }
]

type MainTab = 'leads' | 'inbox' | 'pending' | 'sent'

// ========== Component ==========

export default function LeadsPage() {
  // Main tab state
  const [activeTab, setActiveTab] = useState<MainTab>('leads')
  
  // Leads tab state
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('all')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  
  // Email tabs state
  const [inboxMessages, setInboxMessages] = useState<Message[]>([])
  const [groupedSentMessages, setGroupedSentMessages] = useState<GroupedMessages[]>([])
  const [pendingReplies, setPendingReplies] = useState<PendingReply[]>([])
  const [pendingStats, setPendingStats] = useState<PendingStats | null>(null)
  
  // Sent tracking state
  const [sentMessages, setSentMessages] = useState<Message[]>([])
  const [sentFilter, setSentFilter] = useState<string>('all')
  const [sentStats, setSentStats] = useState<{
    total: number
    delivered: number
    opened: number
    clicked: number
    bounced: number
    open_rate: number
    click_rate: number
    bounce_rate: number
  } | null>(null)
  
  // Modal states
  const [bulkModalOpen, setBulkModalOpen] = useState(false)
  const [isTestSendMode, setIsTestSendMode] = useState(false)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)
  const [queueModalOpen, setQueueModalOpen] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<GroupedMessages | null>(null)
  const [editingReply, setEditingReply] = useState<{id: number, text: string} | null>(null)
  
  // Templates
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null)
  const [customSubject, setCustomSubject] = useState('')
  const [customBody, setCustomBody] = useState('')
  
  // Stats & Settings
  const [stats, setStats] = useState<OutreachStats | null>(null)
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [settings, setSettings] = useState({
    daily_limit: 100,
    start_hour: 8,
    end_hour: 20,
    interval_minutes: 15,
    enabled: true
  })
  
  const [actionLoading, setActionLoading] = useState(false)
  const [generatingReply, setGeneratingReply] = useState<number | null>(null)

  // ========== Data Fetching ==========

  useEffect(() => {
    fetchStats()
    fetchTemplates()
    fetchInboxCount() // Load inbox count on mount
  }, [])

  // Auto-refresh inbox count every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchInboxCount()
    }, 30000) // 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchInboxCount = async () => {
    try {
      const res = await fetch(`/api/communication/inbox`)
      if (res.ok) {
        const data = await res.json()
        setInboxMessages(data)
      }
    } catch (error) {
      console.error('Failed to fetch inbox count:', error)
    }
  }

  useEffect(() => {
    if (activeTab === 'leads') {
      fetchLeads()
    } else if (activeTab === 'inbox') {
      fetchInbox()
    } else if (activeTab === 'pending') {
      fetchPendingReplies()
    } else if (activeTab === 'sent') {
      fetchSentMessages()
    }
  }, [activeTab, page, quickFilter, searchTerm, sentFilter])

  const fetchLeads = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '50'
      })
      
      if (quickFilter === 'ready') {
        params.append('status', 'matched')
      } else if (quickFilter === 'waiting') {
        params.append('status', 'contacted')
      } else if (quickFilter === 'responded') {
        params.append('status', 'responded')
      } else if (quickFilter === 'blocked') {
        params.append('status', 'blacklisted')
      }
      
      // 🔍 Server-side search
      if (searchTerm && searchTerm.trim()) {
        params.append('search', searchTerm.trim())
      }
      
      const response = await fetch(`${API_URL}/api/leads?${params}`)
      if (response.ok) {
        const data = await response.json()
        setLeads(data.items || data)
        setTotal(data.total || data.length)
      }
    } catch (error) {
      console.error('Failed to fetch leads:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchInbox = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/communication/inbox`)
      const data = await res.json()
      setInboxMessages(data)
    } catch (error) {
      console.error('Failed to fetch inbox:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchPendingReplies = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/ai-reply/pending`)
      const data = await res.json()
      setPendingReplies(data)
      
      const statsRes = await fetch(`${API_URL}/api/ai-reply/stats`)
      const statsData = await statsRes.json()
      setPendingStats(statsData)
    } catch (error) {
      console.error('Failed to fetch pending:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchSentMessages = async () => {
    setLoading(true)
    try {
      // Fetch with tracking data
      const statusParam = sentFilter !== 'all' ? `&status=${sentFilter}` : ''
      const res = await fetch(`${API_URL}/api/communication/sent-tracking?per_page=100${statusParam}`)
      const data = await res.json()
      
      if (data.items) {
        setSentMessages(data.items)
        setSentStats(data.stats)
      }
      
      // Also fetch grouped for backward compatibility
      const groupedRes = await fetch(`${API_URL}/api/communication/?direction=outbound&channel=email&group_by_recipient=true`)
      const groupedData = await groupedRes.json()
      setGroupedSentMessages(groupedData)
    } catch (error) {
      console.error('Failed to fetch sent:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/outreach/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
        if (data.settings) {
          setSettings(data.settings)
        }
      }
      
      // Also fetch pending stats
      const pendingRes = await fetch(`${API_URL}/api/ai-reply/stats`)
      if (pendingRes.ok) {
        const pendingData = await pendingRes.json()
        setPendingStats(pendingData)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_URL}/api/templates/`)
      if (response.ok) {
        const data = await response.json()
        setTemplates(data)
        // Auto-select first template if available
        if (data.length > 0 && !selectedTemplate) {
          setSelectedTemplate(data[0].id)
          setCustomSubject(data[0].subject)
          setCustomBody(data[0].body_text)
        }
      }
    } catch (error) {
      console.error('Failed to fetch templates:', error)
    }
  }

  const fetchQueue = async () => {
    try {
      const response = await fetch(`${API_URL}/api/outreach/queue?status=pending&limit=100`)
      if (response.ok) {
        const data = await response.json()
        setQueue(data.items || [])
      }
    } catch (error) {
      console.error('Failed to fetch queue:', error)
    }
  }

  // ========== Helpers ==========

  const filteredLeads = useMemo(() => {
    return leads.filter(lead => {
      if (searchTerm) {
        const term = searchTerm.toLowerCase()
        const matchesDomain = lead.domain?.toLowerCase().includes(term)
        const matchesSite = lead.site_name?.toLowerCase().includes(term)
        const matchesEmail = lead.contact_info?.whois_email?.toLowerCase().includes(term) ||
          lead.contact_info?.emails?.some(e => e.toLowerCase().includes(term))
        
        if (!matchesDomain && !matchesSite && !matchesEmail) {
          return false
        }
      }
      return true
    })
  }, [leads, searchTerm])

  // 🧪 Test emails - allowed unlimited contact
  const TEST_EMAILS = ['afterunew@gmail.com', 'eyal@afteru.co.il', 'test@test.com']
  
  const canContactLead = (lead: Lead): boolean => {
    const email = lead.contact_info?.whois_email || lead.contact_info?.emails?.[0]
    if (!email) return false
    
    // 🧪 Test emails always allowed
    if (TEST_EMAILS.includes(email.toLowerCase())) return true
    
    if (lead.last_contacted_at && !lead.last_response_at) return false
    if (['blacklisted', 'bounced', 'queued'].includes(lead.status)) return false
    return true
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('he-IL')
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      sent: 'bg-blue-100 text-blue-800',
      delivered: 'bg-green-100 text-green-800',
      read: 'bg-purple-100 text-purple-800',
      failed: 'bg-red-100 text-red-800'
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  // ========== Lead Actions ==========

  const toggleSelection = (id: number) => {
    const newSet = new Set(selectedIds)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setSelectedIds(newSet)
  }

  const selectAll = () => {
    const contactable = filteredLeads.filter(canContactLead)
    if (selectedIds.size === contactable.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(contactable.map(l => l.id)))
    }
  }

  const selectContactable = (count: number) => {
    const contactable = filteredLeads
      .filter(canContactLead)
      .slice(0, count)
    setSelectedIds(new Set(contactable.map(l => l.id)))
  }

  const addToQueue = async () => {
    if (selectedIds.size === 0) return
    
    setActionLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/outreach/queue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_ids: Array.from(selectedIds),
          template_id: selectedTemplate,
          subject: customSubject || undefined,
          body: customBody || undefined
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`✅ נוספו ${result.added} לידים לתור\n⏭️ דולגו: ${result.skipped?.length || 0}`)
        setBulkModalOpen(false)
        setSelectedIds(new Set())
        fetchLeads()
        fetchStats()
      } else {
        const error = await response.json()
        alert(`❌ שגיאה: ${error.detail || 'נכשל'}`)
      }
    } catch (error) {
      console.error('Failed to add to queue:', error)
      alert('❌ שגיאה בהוספה לתור')
    } finally {
      setActionLoading(false)
    }
  }

  const addToBlacklist = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`האם להוסיף ${selectedIds.size} לידים לרשימה השחורה?`)) return
    
    setActionLoading(true)
    try {
      const selectedLeads = leads.filter(l => selectedIds.has(l.id))
      const items = selectedLeads.map(lead => ({
        email: lead.contact_info?.whois_email || lead.contact_info?.emails?.[0],
        domain: lead.domain,
        reason: 'manual',
        source: 'bulk_action'
      })).filter(item => item.email || item.domain)
      
      const response = await fetch(`${API_URL}/api/blacklist/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`✅ נוספו ${result.added} לרשימה השחורה`)
        setSelectedIds(new Set())
        fetchLeads()
      }
    } catch (error) {
      console.error('Failed to add to blacklist:', error)
      alert('❌ שגיאה')
    } finally {
      setActionLoading(false)
    }
  }

  const testSendToLead = async (leadId: number, domain: string, email: string) => {
    setActionLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/outreach/test-send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: leadId,
          template_id: selectedTemplate || undefined
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`✅ מייל נשלח ל-${result.email}!`)
        fetchLeads()
        fetchStats()
      } else {
        const error = await response.json()
        alert(`❌ שגיאה: ${error.detail || 'נכשל'}`)
      }
    } catch (error) {
      console.error('Failed to send test:', error)
      alert('❌ שגיאה בשליחה')
    } finally {
      setActionLoading(false)
    }
  }

  const updateSettings = async () => {
    setActionLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/outreach/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })
      
      if (response.ok) {
        alert('✅ ההגדרות נשמרו')
        setSettingsModalOpen(false)
        fetchStats()
      }
    } catch (error) {
      console.error('Failed to update settings:', error)
      alert('❌ שגיאה בשמירה')
    } finally {
      setActionLoading(false)
    }
  }

  const cancelQueueItem = async (id: number) => {
    try {
      const response = await fetch(`${API_URL}/api/outreach/queue/${id}`, { method: 'DELETE' })
      if (response.ok) {
        fetchQueue()
        fetchStats()
      }
    } catch (error) {
      console.error('Failed to cancel:', error)
    }
  }

  const handleTemplateSelect = (templateId: number) => {
    setSelectedTemplate(templateId)
    const template = templates.find(t => t.id === templateId)
    if (template) {
      setCustomSubject(template.subject)
      setCustomBody(template.body_text)
    }
  }

  // ========== AI Reply Actions ==========

  const generateReplyForMessage = async (communicationId: number) => {
    setGeneratingReply(communicationId)
    try {
      const res = await fetch(`${API_URL}/api/ai-reply/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ communication_id: communicationId })
      })
      if (res.ok) {
        const data = await res.json()
        alert(`✅ נוצרה תשובה מתרחיש "${data.scenario}"`)
        setActiveTab('pending')
        fetchPendingReplies()
        fetchStats()
      } else {
        const error = await res.json()
        alert(`שגיאה: ${error.detail}`)
      }
    } catch (error) {
      console.error('Error generating:', error)
      alert('שגיאה ביצירת תשובה')
    } finally {
      setGeneratingReply(null)
    }
  }

  const approveReply = async (pendingId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/ai-reply/${pendingId}/approve`, { method: 'POST' })
      if (res.ok) {
        fetchPendingReplies()
        fetchStats()
      } else {
        alert('שגיאה באישור התשובה')
      }
    } catch (error) {
      console.error('Error approving:', error)
    }
  }

  const rejectReply = async (pendingId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/ai-reply/${pendingId}/reject`, { method: 'POST' })
      if (res.ok) {
        fetchPendingReplies()
        fetchStats()
      }
    } catch (error) {
      console.error('Error rejecting:', error)
    }
  }

  const editAndSendReply = async (pendingId: number, text: string) => {
    try {
      const res = await fetch(`${API_URL}/api/ai-reply/${pendingId}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reply_text: text })
      })
      if (res.ok) {
        setEditingReply(null)
        fetchPendingReplies()
        fetchStats()
      } else {
        alert('שגיאה בשליחת התשובה')
      }
    } catch (error) {
      console.error('Error editing:', error)
    }
  }

  // ========== Render ==========

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Users className="w-7 h-7" />
          מרכז לידים ו-Outreach
        </h1>
        <div className="flex items-center gap-4">
          <button
            onClick={() => { fetchQueue(); setQueueModalOpen(true) }}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Inbox className="w-4 h-4" />
            תור ({stats?.total.pending || 0})
          </button>
          <button
            onClick={() => setSettingsModalOpen(true)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            הגדרות
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">{stats.leads.can_contact}</div>
            <div className="text-xs text-gray-500">מוכנים לשליחה</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600">{stats.total.pending}</div>
            <div className="text-xs text-gray-500">בתור</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-blue-500">{stats.leads.waiting_response}</div>
            <div className="text-xs text-gray-500">ממתינים לתגובה</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{stats.leads.responded}</div>
            <div className="text-xs text-gray-500">השיבו</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-purple-600">{inboxMessages.length || 0}</div>
            <div className="text-xs text-gray-500">נכנסים</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-2xl font-bold text-orange-600">{pendingStats?.pending || 0}</div>
            <div className="text-xs text-gray-500">ממתינים לאישור</div>
          </div>
        </div>
      )}

      {/* Main Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {[
          { id: 'leads' as MainTab, label: 'לידים', icon: <Users className="w-4 h-4" />, badge: total },
          { id: 'inbox' as MainTab, label: 'נכנסים', icon: <Inbox className="w-4 h-4" />, badge: inboxMessages.length },
          { id: 'pending' as MainTab, label: 'תשובות AI', icon: <Bot className="w-4 h-4" />, badge: pendingStats?.pending },
          { id: 'sent' as MainTab, label: 'נשלחו', icon: <SendHorizontal className="w-4 h-4" />, badge: null }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 -mb-[2px] transition ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.icon}
            {tab.label}
            {tab.badge != null && tab.badge > 0 && activeTab !== tab.id && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                tab.id === 'pending' ? 'bg-red-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'leads' && (
        <>
          {/* Quick Filters & Search */}
          <div className="card">
            <div className="flex flex-wrap items-center gap-2 mb-4">
              {quickFilters.map(filter => (
                <button
                  key={filter.value}
                  onClick={() => { setQuickFilter(filter.value); setPage(1) }}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition ${
                    quickFilter === filter.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {filter.icon}
                  {filter.label}
                </button>
              ))}
              
              {/* כפתורי בחירה מהירה */}
              <div className="flex items-center gap-2 mr-4 border-r border-gray-200 pr-4">
                <span className="text-sm text-gray-500">בחירה מהירה:</span>
                <button
                  onClick={() => selectContactable(50)}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 flex items-center gap-1"
                >
                  <CheckSquare className="w-4 h-4" />
                  50
                </button>
                <button
                  onClick={() => selectContactable(100)}
                  className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 flex items-center gap-1"
                >
                  <CheckSquare className="w-4 h-4" />
                  100
                </button>
              </div>
              
              {/* 📧 Template Selector for Test Send */}
              <div className="mr-auto flex items-center gap-2">
                <span className="text-sm text-gray-500">תבנית לשליחה:</span>
                <select
                  value={selectedTemplate || ''}
                  onChange={(e) => setSelectedTemplate(e.target.value ? parseInt(e.target.value) : null)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white"
                >
                  <option value="">ללא תבנית</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="relative">
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                className="input pr-10"
                placeholder="חיפוש לפי דומיין, שם או מייל..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          {/* Bulk Actions Bar */}
          {selectedIds.size > 0 && (
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-white shadow-xl rounded-xl border border-gray-200 p-4 flex items-center gap-4">
              <div className="flex items-center gap-2 text-gray-700 font-medium">
                <CheckSquare className="w-5 h-5 text-blue-600" />
                נבחרו {selectedIds.size}
              </div>
              <div className="h-8 w-px bg-gray-200" />
              <button onClick={() => setBulkModalOpen(true)} className="btn bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2">
                <Send className="w-4 h-4" />
                הוסף לתור
              </button>
              <button onClick={addToBlacklist} className="btn bg-gray-800 hover:bg-gray-900 text-white flex items-center gap-2">
                <Ban className="w-4 h-4" />
                חסום
              </button>
              <button onClick={() => setSelectedIds(new Set())} className="btn btn-secondary">
                בטל
              </button>
            </div>
          )}

          {/* Leads Table */}
          <div className="card overflow-hidden p-0">
            {loading ? (
              <div className="p-8 text-center text-gray-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
                טוען...
              </div>
            ) : filteredLeads.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Users className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>לא נמצאו לידים</p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 w-12">
                      <button onClick={selectAll} className="p-1">
                        {selectedIds.size === filteredLeads.filter(canContactLead).length && selectedIds.size > 0 ? (
                          <CheckSquare className="w-5 h-5 text-blue-600" />
                        ) : (
                          <Square className="w-5 h-5 text-gray-400" />
                        )}
                      </button>
                    </th>
                    <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">דומיין</th>
                    <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">מייל</th>
                    <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">מחשבון</th>
                    <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">סטטוס</th>
                    <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">פעולות</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredLeads.map((lead) => {
                    const email = lead.contact_info?.whois_email || lead.contact_info?.emails?.[0]
                    const canContact = canContactLead(lead)
                    const isSelected = selectedIds.has(lead.id)
                    const config = statusConfig[lead.status] || statusConfig.new
                    
                    return (
                      <tr key={lead.id} className={`hover:bg-gray-50 ${!canContact ? 'opacity-60' : ''}`}>
                        <td className="px-4 py-3">
                          {canContact ? (
                            <button onClick={() => toggleSelection(lead.id)} className="p-1">
                              {isSelected ? <CheckSquare className="w-5 h-5 text-blue-600" /> : <Square className="w-5 h-5 text-gray-400" />}
                            </button>
                          ) : (
                            <div className="p-1" title="לא ניתן לפנות"><Ban className="w-5 h-5 text-gray-300" /></div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <a href={`https://${lead.domain}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-blue-600 hover:underline font-medium">
                            {lead.domain}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </td>
                        <td className="px-4 py-3">
                          {email ? (
                            <div className="flex items-center gap-1 text-sm">
                              <Mail className="w-4 h-4 text-gray-400" />
                              <span className="text-gray-700">{email}</span>
                            </div>
                          ) : <span className="text-xs text-gray-400">—</span>}
                        </td>
                        <td className="px-4 py-3">
                          {lead.recommended_calc_name ? (
                            <div className="flex items-center gap-1 text-xs">
                              <Calculator className="w-3 h-3 text-green-600" />
                              <span>{lead.recommended_calc_name}</span>
                            </div>
                          ) : <span className="text-xs text-gray-400">—</span>}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${config.color}`}>
                            {config.label}
                          </span>
                          {!canContact && lead.last_contacted_at && !lead.last_response_at && (
                            <div className="text-xs text-orange-500 mt-1 flex items-center gap-1">
                              <AlertCircle className="w-3 h-3" />
                              ממתין לתגובה
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            {canContact && email && (
                              <>
                                <button
                                  onClick={() => { 
                                    setSelectedIds(new Set([lead.id]))
                                    setIsTestSendMode(false)
                                    setBulkModalOpen(true) 
                                  }}
                                  className="btn bg-blue-500 hover:bg-blue-600 text-white text-xs py-1 px-2"
                                  title="הוסף לתור"
                                >
                                  <Mail className="w-3 h-3" />
                                </button>
                                <button
                                  onClick={() => { 
                                    setSelectedIds(new Set([lead.id]))
                                    setIsTestSendMode(true)
                                    setBulkModalOpen(true)
                                  }}
                                  className="btn bg-orange-500 hover:bg-orange-600 text-white text-xs py-1 px-2"
                                  title="שלח עכשיו (טסט)"
                                >
                                  <Zap className="w-3 h-3" />
                                </button>
                              </>
                            )}
                            {lead.contact_info?.whois_phone && (
                              <a href={`https://wa.me/${lead.contact_info.whois_phone.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer" className="btn bg-green-500 hover:bg-green-600 text-white text-xs py-1 px-2">
                                <MessageSquare className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {total > 50 && (
            <div className="flex justify-center gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn btn-secondary">הקודם</button>
              <span className="px-4 py-2">עמוד {page} מתוך {Math.ceil(total / 50)}</span>
              <button onClick={() => setPage(p => p + 1)} disabled={leads.length < 50} className="btn btn-secondary">הבא</button>
            </div>
          )}
        </>
      )}

      {/* Inbox Tab */}
      {activeTab === 'inbox' && (
        <div className="card overflow-hidden p-0">
          {loading ? (
            <div className="p-8 text-center text-gray-500">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
              טוען...
            </div>
          ) : inboxMessages.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Inbox className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>אין הודעות נכנסות</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">מ:</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">נושא</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">תוכן</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">תאריך</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">פעולות</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {inboxMessages.map(msg => (
                  <tr key={msg.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">Lead #{msg.lead_id}</td>
                    <td className="px-4 py-3 text-sm font-medium cursor-pointer" onClick={() => setSelectedMessage(msg)}>{msg.subject || '(ללא נושא)'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 max-w-md truncate cursor-pointer" onClick={() => setSelectedMessage(msg)}>{msg.message_body.substring(0, 80)}...</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{formatDate(msg.sent_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => generateReplyForMessage(msg.id)}
                        disabled={generatingReply === msg.id}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                      >
                        {generatingReply === msg.id ? '⏳ מייצר...' : '🤖 צור תשובה'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Pending AI Replies Tab */}
      {activeTab === 'pending' && (
        <div className="space-y-4">
          {loading ? (
            <div className="card p-8 text-center text-gray-500">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
              טוען...
            </div>
          ) : pendingReplies.length === 0 ? (
            <div className="card p-8 text-center text-gray-500">
              <Bot className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">🎉 אין תשובות ממתינות לאישור</p>
              <p className="text-sm mt-2">כאשר יגיע מייל נכנס, ה-AI יציע תשובה לאישורך</p>
            </div>
          ) : (
            pendingReplies.map(pending => (
              <div key={pending.id} className="card">
                {/* Header */}
                <div className="flex justify-between items-start mb-4 pb-4 border-b">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <p className="font-medium">מ: {pending.sender_email || 'לא ידוע'}</p>
                      {pending.scenario_name && (
                        <span className={`px-2 py-0.5 text-xs rounded-full ${
                          pending.scenario_category === 'positive' ? 'bg-green-100 text-green-700' :
                          pending.scenario_category === 'negative' ? 'bg-red-100 text-red-700' :
                          pending.scenario_category === 'question' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          🎯 {pending.scenario_name}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500">דומיין: {pending.lead_domain || 'לא ידוע'}</p>
                  </div>
                  <span className="text-sm text-gray-400">{formatDate(pending.created_at)}</span>
                </div>

                {/* Original Message */}
                <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-600 mb-1">📨 הודעת הלקוח:</p>
                  <p className="text-gray-800 whitespace-pre-wrap">{pending.original_message || '(אין תוכן)'}</p>
                </div>

                {/* AI Reply */}
                <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="text-sm font-medium text-blue-600 mb-2">🤖 הצעת AI:</p>
                  {editingReply?.id === pending.id ? (
                    <textarea
                      value={editingReply.text}
                      onChange={(e) => setEditingReply({ id: pending.id, text: e.target.value })}
                      className="w-full p-2 border rounded-lg"
                      rows={6}
                    />
                  ) : (
                    <p className="text-gray-800 whitespace-pre-wrap">{pending.suggested_reply}</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 justify-end">
                  <button onClick={() => rejectReply(pending.id)} className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg">❌ דחה</button>
                  {editingReply?.id === pending.id ? (
                    <>
                      <button onClick={() => setEditingReply(null)} className="px-4 py-2 text-gray-600 hover:bg-gray-50 rounded-lg">ביטול</button>
                      <button onClick={() => editAndSendReply(pending.id, editingReply.text)} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">✅ שלח</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => setEditingReply({ id: pending.id, text: pending.suggested_reply })} className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg">✏️ ערוך</button>
                      <button onClick={() => approveReply(pending.id)} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">✅ אשר ושלח</button>
                    </>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Sent Tab - Enhanced with Tracking */}
      {activeTab === 'sent' && (
        <div className="card overflow-hidden p-0">
          {/* Stats Bar */}
          {sentStats && (
            <div className="grid grid-cols-5 gap-4 p-4 bg-gradient-to-r from-gray-50 to-gray-100 border-b">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{sentStats.total}</div>
                <div className="text-xs text-gray-500">נשלחו</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{sentStats.delivered}</div>
                <div className="text-xs text-gray-500">נמסרו</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{sentStats.opened}</div>
                <div className="text-xs text-gray-500">נפתחו ({sentStats.open_rate}%)</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">{sentStats.clicked}</div>
                <div className="text-xs text-gray-500">קליקים ({sentStats.click_rate}%)</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{sentStats.bounced}</div>
                <div className="text-xs text-gray-500">חזרו ({sentStats.bounce_rate}%)</div>
              </div>
            </div>
          )}

          {/* Filter Buttons */}
          <div className="p-4 border-b flex gap-2 flex-wrap">
            {[
              { value: 'all', label: 'הכל', icon: '📧' },
              { value: 'sent', label: 'נשלחו', icon: '📤' },
              { value: 'opened', label: 'נפתחו', icon: '👁️' },
              { value: 'clicked', label: 'קליקים', icon: '🔗' },
              { value: 'bounced', label: 'חזרו', icon: '❌' }
            ].map(filter => (
              <button
                key={filter.value}
                onClick={() => setSentFilter(filter.value)}
                className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 transition ${
                  sentFilter === filter.value 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                }`}
              >
                {filter.icon} {filter.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-500">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
              טוען...
            </div>
          ) : sentMessages.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <SendHorizontal className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>אין הודעות יוצאות</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">דומיין</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">נמען</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">נושא</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">נשלח</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">סטטוס</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">👁️</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">🔗</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sentMessages.map(msg => (
                    <tr key={msg.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="text-sm font-medium text-gray-900">{msg.domain || '-'}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-blue-600">{msg.to_email}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-700 max-w-xs truncate block">{msg.subject}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {msg.sent_at ? formatDate(msg.sent_at) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          msg.status === 'failed' ? 'bg-red-100 text-red-800' :
                          msg.status === 'delivered' ? 'bg-green-100 text-green-800' :
                          msg.status === 'read' ? 'bg-purple-100 text-purple-800' :
                          msg.status === 'sent' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {msg.status === 'failed' ? '❌ נכשל' :
                           msg.status === 'delivered' ? '✅ נמסר' :
                           msg.status === 'read' ? '👁️ נקרא' :
                           msg.status === 'sent' ? '📤 נשלח' :
                           msg.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {msg.opens_count && msg.opens_count > 0 ? (
                          <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-medium">
                            {msg.opens_count}
                          </span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {msg.clicks && msg.clicks.length > 0 ? (
                          <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-medium">
                            {msg.clicks.length}
                          </span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========== Modals ========== */}

      {/* Bulk Send Modal */}
      {bulkModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-xl font-bold">
                    {isTestSendMode ? '⚡ שליחה מיידית' : '📧 הוספה לתור שליחה'}
                  </h2>
                  <p className="text-gray-500 mt-1">{selectedIds.size} לידים נבחרו</p>
                </div>
                <button onClick={() => { setBulkModalOpen(false); setIsTestSendMode(false) }} className="p-2 hover:bg-gray-100 rounded-full">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">בחר תבנית</label>
                <select
                  value={selectedTemplate || ''}
                  onChange={(e) => handleTemplateSelect(parseInt(e.target.value))}
                  className="w-full p-2 border rounded-lg"
                >
                  {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">נושא</label>
                <input type="text" value={customSubject} onChange={(e) => setCustomSubject(e.target.value)} className="w-full p-2 border rounded-lg" placeholder="נושא המייל..." />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">תוכן</label>
                <textarea value={customBody} onChange={(e) => setCustomBody(e.target.value)} className="w-full p-2 border rounded-lg" rows={8} placeholder="תוכן המייל..." />
              </div>

              <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  המיילים יישלחו בהדרגה ({settings.daily_limit} ביום, {settings.start_hour}:00-{settings.end_hour}:00)
                </p>
              </div>

              <div className="flex gap-2 justify-end">
                <button onClick={() => { setBulkModalOpen(false); setIsTestSendMode(false) }} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">ביטול</button>
                {isTestSendMode ? (
                  <button 
                    onClick={async () => {
                      const leadId = Array.from(selectedIds)[0]
                      const lead = leads.find(l => l.id === leadId)
                      const email = lead?.contact_info?.whois_email || lead?.contact_info?.emails?.[0]
                      if (lead && email) {
                        await testSendToLead(leadId, lead.domain, email)
                        setBulkModalOpen(false)
                        setIsTestSendMode(false)
                      }
                    }} 
                    disabled={actionLoading} 
                    className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 flex items-center gap-2"
                  >
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    שלח עכשיו
                  </button>
                ) : (
                  <button onClick={addToQueue} disabled={actionLoading} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2">
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    הוסף לתור
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {settingsModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold">⚙️ הגדרות Outreach</h2>
                <button onClick={() => setSettingsModalOpen(false)} className="p-2 hover:bg-gray-100 rounded-full"><X className="w-5 h-5" /></button>
              </div>

              <div className="mb-6 flex items-center justify-between">
                <label className="font-medium">שליחה אוטומטית</label>
                <button
                  onClick={() => setSettings(s => ({ ...s, enabled: !s.enabled }))}
                  className={`relative w-12 h-6 rounded-full transition ${settings.enabled ? 'bg-green-500' : 'bg-gray-300'}`}
                >
                  <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition ${settings.enabled ? 'right-1' : 'left-1'}`} />
                </button>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">מגבלה יומית: {settings.daily_limit}</label>
                <input type="range" min="1" max="100" value={settings.daily_limit} onChange={(e) => setSettings(s => ({ ...s, daily_limit: parseInt(e.target.value) }))} className="w-full" />
              </div>

              <div className="mb-4 grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">התחלה</label>
                  <select value={settings.start_hour} onChange={(e) => setSettings(s => ({ ...s, start_hour: parseInt(e.target.value) }))} className="w-full p-2 border rounded-lg">
                    {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{i}:00</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">סיום</label>
                  <select value={settings.end_hour} onChange={(e) => setSettings(s => ({ ...s, end_hour: parseInt(e.target.value) }))} className="w-full p-2 border rounded-lg">
                    {Array.from({ length: 24 }, (_, i) => <option key={i} value={i}>{i}:00</option>)}
                  </select>
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">מרווח: {settings.interval_minutes} דקות</label>
                <select value={settings.interval_minutes} onChange={(e) => setSettings(s => ({ ...s, interval_minutes: parseInt(e.target.value) }))} className="w-full p-2 border rounded-lg">
                  <option value="5">5 דקות</option>
                  <option value="10">10 דקות</option>
                  <option value="15">15 דקות</option>
                  <option value="30">30 דקות</option>
                  <option value="60">שעה</option>
                </select>
              </div>

              <div className="flex gap-2 justify-end">
                <button onClick={() => setSettingsModalOpen(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">ביטול</button>
                <button onClick={updateSettings} disabled={actionLoading} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">שמור</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Queue Modal */}
      {queueModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-xl font-bold">📬 תור מיילים</h2>
                  <p className="text-gray-500 mt-1">{queue.length} בתור</p>
                </div>
                <button onClick={() => setQueueModalOpen(false)} className="p-2 hover:bg-gray-100 rounded-full"><X className="w-5 h-5" /></button>
              </div>

              {queue.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Inbox className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>התור ריק</p>
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-right px-4 py-2 text-sm">דומיין</th>
                      <th className="text-right px-4 py-2 text-sm">מייל</th>
                      <th className="text-right px-4 py-2 text-sm">נושא</th>
                      <th className="text-right px-4 py-2 text-sm">מתוזמן</th>
                      <th className="px-4 py-2"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {queue.map(item => (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 text-sm">{item.lead_domain}</td>
                        <td className="px-4 py-2 text-sm">{item.to_email}</td>
                        <td className="px-4 py-2 text-sm truncate max-w-xs">{item.subject}</td>
                        <td className="px-4 py-2 text-sm">{new Date(item.scheduled_at).toLocaleString('he-IL')}</td>
                        <td className="px-4 py-2">
                          <button onClick={() => cancelQueueItem(item.id)} className="text-red-500 hover:text-red-700"><XCircle className="w-4 h-4" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Message Detail Modal */}
      {selectedMessage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold">{selectedMessage.subject || '(ללא נושא)'}</h3>
                  <p className="text-sm text-gray-500">Lead #{selectedMessage.lead_id}</p>
                  <p className="text-sm text-gray-500">{formatDate(selectedMessage.sent_at)}</p>
                </div>
                <button onClick={() => setSelectedMessage(null)} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
              </div>
              <div className="border-t pt-4">
                <div className="flex gap-2 mb-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(selectedMessage.status)}`}>{selectedMessage.status}</span>
                  {selectedMessage.is_auto_reply && <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">🤖 תשובה אוטומטית</span>}
                </div>
                <div className="bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">{selectedMessage.message_body}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sent Group Modal */}
      {selectedGroup && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4 border-b pb-4">
                <div>
                  <h3 className="text-lg font-bold">📧 הודעות ל: {selectedGroup.email}</h3>
                  <p className="text-sm text-gray-500">דומיינים: {selectedGroup.domains.join(', ')}</p>
                </div>
                <button onClick={() => setSelectedGroup(null)} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
              </div>
              <div className="space-y-4">
                {selectedGroup.messages.map(msg => (
                  <div key={msg.id} className="border rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex justify-between items-start mb-2">
                      <p className="font-medium">{msg.subject || '(ללא נושא)'}</p>
                      <div className="text-left">
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadge(msg.status)}`}>{msg.status}</span>
                        <p className="text-sm text-gray-400 mt-1">{formatDate(msg.sent_at)}</p>
                      </div>
                    </div>
                    <p className="text-gray-700 text-sm whitespace-pre-wrap line-clamp-3">{msg.message_body}</p>
                    {msg.opens_count && msg.opens_count > 0 && (
                      <p className="text-xs text-green-600 mt-2">👁️ נפתח {msg.opens_count} פעמים</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
