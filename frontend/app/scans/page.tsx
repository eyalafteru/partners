'use client'

import { useState, useEffect } from 'react'
import { Search, Play, Pause, Trash2, Plus, RefreshCw, Eye, Zap, Loader2 } from 'lucide-react'

interface Scan {
  id: number
  name: string
  status: string
  keywords: string[]
  results_per_keyword: number
  total_urls: number
  scanned_count: number
  matched_count: number
  contacted_count: number
  created_at: string
  completed_at: string
  // Extended stats
  whois_contacts?: number
  has_content?: number
  ai_analyzed?: number
  // AI progress
  ai_current_domain?: string
  ai_processed?: number
  ai_total?: number
  // Rescan
  rescan_status?: string
  rescan_processed?: number
  rescan_total?: number
  // Deep Scan & Calculator Match
  deep_scanned?: number
  calc_matched?: number
  gpt_calc_matched?: number
  // Deep Scan Status
  deep_scan_status?: string
  deep_scan_processed?: number
  deep_scan_total?: number
  deep_scan_current?: string
  // Calculator Match Status
  calc_match_status?: string
  calc_match_processed?: number
  calc_match_total?: number
  // GPT Calculator Match Status
  gpt_match_status?: string
  gpt_match_processed?: number
  gpt_match_total?: number
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  paused: 'bg-yellow-100 text-yellow-700',
  failed: 'bg-red-100 text-red-700'
}

const statusLabels: Record<string, string> = {
  pending: 'ממתין',
  running: 'פועל',
  completed: 'הושלם',
  paused: 'מושהה',
  failed: 'נכשל'
}

interface ScanResult {
  id: number
  url: string
  title: string
  status: string
  error_message: string | null
  description: string | null
  // WHOIS
  owner_name: string | null
  owner_org: string | null
  owner_email: string | null
  owner_phone: string | null
  whois_is_private: boolean
  // AI
  business_type: string | null
  business_type_reason: string | null
  // Content
  has_content: boolean
  html_text: string | null
  // Deep Scan
  deep_scan_status: string | null
  pages_scanned: number
  scanned_pages?: Array<{
    url: string
    path: string
    page_type: string
    title: string
    has_contact_form: boolean
  }>
  // Calculator Match (Ollama)
  recommended_calc_id: number | null
  recommended_calc_name: string | null
  recommended_calc_score: number | null
  recommended_calc_reason: string | null
  all_recommended_calcs: Array<{
    calc_id: number
    calc_name: string
    score: number
    reason: string
  }> | null
  // GPT Calculator Match
  gpt_recommended_calc_id: number | null
  gpt_recommended_calc_name: string | null
  gpt_recommended_calc_score: number | null
  gpt_recommended_calc_reason: string | null
  gpt_match_duration_seconds: number | null
  gpt_all_recommended_calcs: Array<{
    calc_id: number
    calc_name: string
    score: number
    reason: string
  }> | null
}

interface DomainItem {
  id: number
  domain: string
  url: string
  title: string
  status: string
  campaign_name: string
  keywords: string[]
  description: string
  processed_at: string | null
  // WHOIS
  owner_name: string | null
  owner_org: string | null
  owner_email: string | null
  owner_phone: string | null
  whois_is_private: boolean
  // AI
  business_type: string | null
  business_type_reason: string | null
  // Content
  has_content: boolean
  html_text: string | null
  // Blacklist
  is_blacklisted: boolean
  // Deep Scan
  deep_scanned: boolean
}

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [backgroundRefresh, setBackgroundRefresh] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null)
  const [scanResults, setScanResults] = useState<ScanResult[]>([])
  const [loadingResults, setLoadingResults] = useState(false)
  
  // AI Analysis state
  const [analyzingAI, setAnalyzingAI] = useState<number | null>(null)
  const [scanAIStats, setScanAIStats] = useState<Record<number, {
    ai_current_domain?: string,
    ai_processed?: number,
    ai_total?: number,
    is_running?: boolean
  }>>({})
  const [aiStats, setAiStats] = useState<{
    type_counts: Record<string, number>, 
    not_analyzed: number,
    ai_current_domain?: string,
    ai_processed?: number,
    ai_total?: number,
    is_running?: boolean
  } | null>(null)
  
  // Selection state for AI classification
  const [selectedResults, setSelectedResults] = useState<Set<number>>(new Set())
  const [selectAll, setSelectAll] = useState(false)
  
  // Content viewer modal
  const [viewingContent, setViewingContent] = useState<{domain: string, content: string} | null>(null)
  
  // All domains state with pagination
  const [allDomains, setAllDomains] = useState<DomainItem[]>([])
  const [loadingDomains, setLoadingDomains] = useState(false)
  const [domainFilter, setDomainFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [contentFilter, setContentFilter] = useState('')
  const [domainPage, setDomainPage] = useState(0)
  const [totalDomains, setTotalDomains] = useState(0)
  const DOMAINS_PER_PAGE = 100

  // Grouped owners state
  const [groupedOwners, setGroupedOwners] = useState<any>(null)
  const [loadingOwners, setLoadingOwners] = useState(false)
  
  // GPU Control state
  const [gpuStatus, setGpuStatus] = useState<{loaded_models: string[], count: number} | null>(null)
  const [loadingGPU, setLoadingGPU] = useState(false)
  
  // Global Rescan state
  const [globalRescanStatus, setGlobalRescanStatus] = useState<{
    is_running: boolean,
    phase: string | null,
    current_site: string | null,
    rescan_processed: number,
    rescan_total: number,
    match_processed: number,
    match_total: number,
    logs: string[]
  } | null>(null)

  // Fetch AI stats for all scans
  const fetchAllAIStats = async () => {
    for (const scan of scans) {
      try {
        const response = await fetch(`/api/scans/${scan.id}/ai-stats`)
        if (response.ok) {
          const data = await response.json()
          setScanAIStats(prev => ({
            ...prev,
            [scan.id]: {
              ai_current_domain: data.ai_current_domain,
              ai_processed: data.ai_processed,
              ai_total: data.ai_total,
              is_running: data.is_running
            }
          }))
        }
      } catch (error) {
        // Silently ignore
      }
    }
  }

  useEffect(() => {
    fetchScans()
    fetchAllDomains(0, '', '')
    fetchGPUStatus()
    fetchGlobalRescanStatus() // Check if global rescan is running
    // Initial refresh interval - refresh scans every 3 seconds for better responsiveness
    const interval = setInterval(() => {
      fetchScans()
      fetchGPUStatus()
    }, 3000) // Changed from 10000 to 3000 for faster updates
    return () => clearInterval(interval)
  }, [])

  // Fetch AI stats when scans change
  useEffect(() => {
    if (scans.length > 0) {
      fetchAllAIStats()
    }
  }, [scans])

  // Fast refresh AI stats every 3 seconds if any scan has AI running
  useEffect(() => {
    const hasAIRunning = Object.values(scanAIStats).some(s => s?.is_running)
    if (!hasAIRunning) return

    const aiInterval = setInterval(fetchAllAIStats, 3000)
    return () => clearInterval(aiInterval)
  }, [scanAIStats, scans])

  // Reset analyzingAI state when AI process completes
  useEffect(() => {
    if (analyzingAI !== null) {
      const stats = scanAIStats[analyzingAI]
      // If AI was running but now stopped, reset the state
      if (stats && stats.is_running === false) {
        console.log('🤖 AI analysis completed, resetting state')
        setAnalyzingAI(null)
      }
    }
  }, [scanAIStats, analyzingAI])

  // Fast refresh when scans are running OR rescan is running - non-blocking
  useEffect(() => {
    const hasRunningScan = scans.some(s => s.status === 'running')
    const hasRunningRescan = scans.some(s => s.rescan_status === 'running')
    const hasRunningDeepScan = scans.some(s => s.deep_scan_status === 'running')
    const hasRunningCalcMatch = scans.some(s => s.calc_match_status === 'running')
    
    const hasAnyRunning = hasRunningScan || hasRunningRescan || hasRunningDeepScan || hasRunningCalcMatch
    
    if (!hasAnyRunning) {
      setBackgroundRefresh(false)
      return
    }

    setBackgroundRefresh(true)
    const fastInterval = setInterval(() => {
      // Non-blocking fetch
      fetch('/api/scans')
        .then(r => r.ok ? r.json() : null)
        .then(data => data && setScans(data))
        .catch(() => {}) // Silently ignore errors during background refresh
    }, 1500) // Refresh every 1.5 seconds when any scan is running
    
    return () => clearInterval(fastInterval)
  }, [scans.some(s => s.status === 'running' || s.rescan_status === 'running' || s.deep_scan_status === 'running' || s.calc_match_status === 'running')])

  const fetchAllDomains = async (page = 0, status = '', content = '') => {
    setLoadingDomains(true)
    try {
      const skip = page * DOMAINS_PER_PAGE
      let url = `/api/scans/domains/all?skip=${skip}&limit=${DOMAINS_PER_PAGE}`
      if (status) url += `&status=${status}`
      if (content) url += `&content_filter=${content}`
      
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        console.log('📊 Domains API:', { total: data.total, items: data.items?.length, page })
        setAllDomains(data.items || [])
        setTotalDomains(data.total || 0)
      }
    } catch (error) {
      console.error('Failed to fetch domains:', error)
    } finally {
      setLoadingDomains(false)
    }
  }

  // Handle page change
  const handleDomainPageChange = (newPage: number) => {
    setDomainPage(newPage)
    fetchAllDomains(newPage, statusFilter, contentFilter)
  }

  // Fetch grouped owners
  const fetchGroupedOwners = async () => {
    setLoadingOwners(true)
    try {
      const response = await fetch('/api/scans/domains/grouped-by-owner')
      if (response.ok) {
        const data = await response.json()
        setGroupedOwners(data)
      }
    } catch (error) {
      console.error('Failed to fetch grouped owners:', error)
    } finally {
      setLoadingOwners(false)
    }
  }

  const fetchScans = async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout
      
      const response = await fetch('/api/scans', { signal: controller.signal })
      clearTimeout(timeoutId)
      
      if (response.ok) {
        const data = await response.json()
        console.log('📊 Scans fetched:', data.map((s: Scan) => ({ 
          id: s.id, 
          name: s.name, 
          deep_scan_status: s.deep_scan_status, 
          deep_scan_total: s.deep_scan_total 
        })))
        setScans(data)
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to fetch scans:', error)
      }
    } finally {
      setLoading(false)
    }
  }

  const startScan = async (id: number) => {
    setRunningScan(id)
    try {
      await fetch(`/api/scans/${id}/start`, { method: 'POST' })
      fetchScans()
      // Start auto-refresh while scan is running
      startScanAutoRefresh(id)
    } catch (error) {
      console.error('Failed to start scan:', error)
      setRunningScan(null)
    }
  }

  const startScanAutoRefresh = (scanId: number) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/scans')
        if (response.ok) {
          const data = await response.json()
          setScans(data)
          
          // Check if scan is still running
          const scan = data.find((s: Scan) => s.id === scanId)
          if (!scan || scan.status !== 'running') {
            clearInterval(interval)
            setRunningScan(null)
          }
        }
      } catch (error) {
        console.error('Auto-refresh failed:', error)
      }
    }, 2000) // Refresh every 2 seconds
  }

  const pauseScan = async (id: number) => {
    await fetch(`/api/scans/${id}/pause`, { method: 'POST' })
    fetchScans()
  }

  const deleteScan = async (id: number) => {
    if (!confirm('למחוק את הסריקה?')) return
    await fetch(`/api/scans/${id}`, { method: 'DELETE' })
    fetchScans()
  }

  const retryScan = async (id: number) => {
    setRunningScan(id)
    try {
      const response = await fetch(`/api/scans/${id}/retry`, { method: 'POST' })
      if (response.ok) {
        fetchScans()
        // Start auto-refresh
        startScanAutoRefresh(id)
      } else {
        alert('שגיאה בהפעלה מחדש')
        setRunningScan(null)
      }
    } catch (error) {
      console.error('Failed to retry scan:', error)
      alert('שגיאה בהפעלה מחדש')
      setRunningScan(null)
    }
  }

  const blacklistDomain = async (id: number) => {
    try {
      const response = await fetch(`/api/scans/domains/${id}/blacklist`, { method: 'POST' })
      if (response.ok) {
        fetchAllDomains(domainPage)
      }
    } catch (error) {
      console.error('Failed to blacklist domain:', error)
    }
  }

  const unblacklistDomain = async (id: number) => {
    try {
      const response = await fetch(`/api/scans/domains/${id}/unblacklist`, { method: 'POST' })
      if (response.ok) {
        fetchAllDomains(domainPage)
      }
    } catch (error) {
      console.error('Failed to unblacklist domain:', error)
    }
  }

  const [analyzing, setAnalyzing] = useState<number | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [runningScan, setRunningScan] = useState<number | null>(null)

  const startAnalysis = async (scan: Scan) => {
    setAnalyzing(scan.id)
    
    // Open results modal
    setSelectedScan(scan)
    setLoadingResults(true)
    
    try {
      // Start analysis
      const response = await fetch(`/api/scans/${scan.id}/analyze?batch_size=10&use_browser=true`, { 
        method: 'POST' 
      })
      
      if (response.ok) {
        // Start auto-refresh
        setAutoRefresh(true)
        
        // Fetch initial results
        await viewResults(scan)
      }
    } catch (error) {
      console.error('Failed to start analysis:', error)
    } finally {
      setAnalyzing(null)
    }
  }

  // AI Business Type Analysis
  const startAIAnalysis = async (scan: Scan) => {
    console.log('🤖 Starting AI analysis for scan:', scan.id)
    setAnalyzingAI(scan.id)
    
    try {
      const response = await fetch(`/api/scans/${scan.id}/analyze-business-type?batch_size=20`, { 
        method: 'POST' 
      })
      
      console.log('🤖 AI API response:', response.status, response.ok)
      
      if (response.ok) {
        const data = await response.json()
        console.log('🤖 AI API data:', data)
        // Start auto-refresh loop for AI stats (this will also update results)
        fetchAIStats(scan.id)
      } else {
        const errorText = await response.text()
        console.error('🤖 AI API error:', errorText)
        setAnalyzingAI(null)
      }
    } catch (error) {
      console.error('🤖 Failed to start AI analysis:', error)
      setAnalyzingAI(null)
    }
  }

  const fetchAIStats = async (scanId: number) => {
    try {
      console.log('📊 Fetching AI stats for scan:', scanId)
      const response = await fetch(`/api/scans/${scanId}/ai-stats`)
      if (response.ok) {
        const data = await response.json()
        console.log('📊 AI Stats:', data)
        setAiStats(data)
        
        // Save to scanAIStats for display in scan card
        setScanAIStats(prev => ({
          ...prev,
          [scanId]: {
            ai_current_domain: data.ai_current_domain,
            ai_processed: data.ai_processed,
            ai_total: data.ai_total,
            is_running: data.is_running
          }
        }))
        
        // Also refresh results table
        const resultsResponse = await fetch(`/api/scans/${scanId}/queue?limit=100`)
        if (resultsResponse.ok) {
          const resultsData = await resultsResponse.json()
          setScanResults(resultsData)
        }
        
        // If AI is running, auto-refresh faster
        if (data.is_running) {
          setTimeout(() => fetchAIStats(scanId), 2000) // Refresh every 2 seconds
        } else {
          // AI finished - reset analyzing state
          setAnalyzingAI(null)
          // Clear from scanAIStats
          setScanAIStats(prev => {
            const updated = { ...prev }
            delete updated[scanId]
            return updated
          })
        }
      }
    } catch (error) {
      console.error('Failed to fetch AI stats:', error)
      setAnalyzingAI(null)
    }
  }

  // GPU Control Functions
  const fetchGPUStatus = async () => {
    try {
      const response = await fetch('/api/scans/gpu/status')
      if (response.ok) {
        const data = await response.json()
        setGpuStatus(data)
      }
    } catch (error) {
      console.error('Failed to fetch GPU status:', error)
    }
  }
  
  // Global Rescan Functions
  const fetchGlobalRescanStatus = async () => {
    try {
      const response = await fetch('/api/scans/global/rescan-matched-no-content/status')
      if (response.ok) {
        const data = await response.json()
        setGlobalRescanStatus(data)
        
        // Continue polling if running
        if (data.is_running) {
          setTimeout(fetchGlobalRescanStatus, 2000)
        }
      }
    } catch (error) {
      console.error('Failed to fetch global rescan status:', error)
    }
  }
  
  const startGlobalRescan = async () => {
    try {
      const response = await fetch('/api/scans/global/rescan-matched-no-content', {
        method: 'POST'
      })
      if (response.ok) {
        const data = await response.json()
        alert(`${data.message}`)
        fetchGlobalRescanStatus() // Start polling
      } else {
        const error = await response.json()
        alert(`שגיאה: ${error.detail || 'לא ידוע'}`)
      }
    } catch (error) {
      console.error('Failed to start global rescan:', error)
      alert('שגיאה בהתחלת סריקה גלובלית')
    }
  }
  
  const stopGlobalRescan = async () => {
    try {
      const response = await fetch('/api/scans/global/rescan-matched-no-content/stop', {
        method: 'POST'
      })
      if (response.ok) {
        fetchGlobalRescanStatus()
      }
    } catch (error) {
      console.error('Failed to stop global rescan:', error)
    }
  }

  const loadModelToGPU = async () => {
    setLoadingGPU(true)
    try {
      const response = await fetch('/api/scans/gpu/load', { method: 'POST' })
      if (response.ok) {
        await fetchGPUStatus()
      }
    } catch (error) {
      console.error('Failed to load model:', error)
    } finally {
      setLoadingGPU(false)
    }
  }

  const unloadModelFromGPU = async () => {
    setLoadingGPU(true)
    try {
      const response = await fetch('/api/scans/gpu/unload', { method: 'POST' })
      if (response.ok) {
        await fetchGPUStatus()
      }
    } catch (error) {
      console.error('Failed to unload model:', error)
    } finally {
      setLoadingGPU(false)
    }
  }

  // Toggle single selection
  const toggleResultSelection = (id: number) => {
    const newSelected = new Set(selectedResults)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedResults(newSelected)
  }

  // Toggle select all (items with content - both analyzed and not)
  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedResults(new Set())
    } else {
      const allIds = scanResults
        .filter(r => r.has_content)
        .map(r => r.id)
      setSelectedResults(new Set(allIds))
    }
    setSelectAll(!selectAll)
  }
  
  // Count how many selected items are already analyzed (for re-analysis)
  const selectedAlreadyAnalyzed = scanResults.filter(r => selectedResults.has(r.id) && r.business_type).length
  const selectedNotAnalyzed = selectedResults.size - selectedAlreadyAnalyzed

  // Rescan sites without content
  const rescanNoContent = async (scanId: number) => {
    try {
      const response = await fetch(`/api/scans/${scanId}/rescan-no-content`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('🔄 Rescan started:', data)
        fetchScans()
        fetchAllAIStats()
      } else {
        const error = await response.text()
        console.error('Rescan error:', error)
      }
    } catch (error) {
      console.error('Failed to start rescan:', error)
    }
  }

  // Rescan all sites for navigation extraction
  const rescanForNavigation = async (scanId: number) => {
    try {
      const response = await fetch(`/api/scans/${scanId}/rescan-all-for-navigation`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('🎯 Navigation rescan started:', data)
        fetchScans()
      } else {
        const error = await response.text()
        console.error('Navigation rescan error:', error)
      }
    } catch (error) {
      console.error('Failed to rescan for navigation:', error)
    }
  }

  // Stop AI Analysis
  const stopAIAnalysis = async (scanId?: number) => {
    try {
      const url = scanId ? `/api/scans/${scanId}/stop-ai` : '/api/scans/stop-all-ai'
      const response = await fetch(url, { method: 'POST' })
      
      if (response.ok) {
        const data = await response.json()
        console.log('🛑 AI stopped:', data)
        setAnalyzingAI(null)
        // Refresh stats
        if (scanId) {
          fetchAIStats(scanId)
        }
        fetchAllAIStats()
      }
    } catch (error) {
      console.error('Failed to stop AI:', error)
    }
  }

  // Deep Scan - scan multiple pages per site
  const startDeepScan = async (scanId: number) => {
    try {
      const response = await fetch(`/api/scans/${scanId}/deep-scan`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('🔍 Deep scan started:', data)
        await fetchScans() // Make sure to wait for refresh
        console.log('✅ Scans refreshed after deep scan start')
      } else {
        console.error('❌ Deep scan failed:', await response.text())
      }
    } catch (error) {
      console.error('Failed to start deep scan:', error)
    }
  }

  // Match Calculators - AI matches best calculator for each site
  const startMatchCalculators = async (scanId: number) => {
    try {
      const response = await fetch(`/api/scans/${scanId}/match-calculators`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('🧮 Calculator matching started:', data)
        fetchScans()
      }
    } catch (error) {
      console.error('Failed to start calculator matching:', error)
    }
  }

  // GPT Match Calculators - OpenAI GPT matches best calculator for each site
  const [gptMatchStatus, setGptMatchStatus] = useState<Record<number, {
    is_running: boolean
    current_site: string | null
    processed: number
    total: number
    logs: string[]
  }>>({})

  const startMatchCalculatorsGPT = async (scanId: number) => {
    try {
      const response = await fetch(`/api/scans/${scanId}/match-calculators-gpt`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('⚡ GPT Calculator matching started:', data)
        fetchScans()
        // Start polling for GPT status
        pollGptMatchStatus(scanId)
      }
    } catch (error) {
      console.error('Failed to start GPT calculator matching:', error)
    }
  }

  const pollGptMatchStatus = async (scanId: number) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/scans/${scanId}/match-calculators-gpt/status`)
        if (response.ok) {
          const status = await response.json()
          setGptMatchStatus(prev => ({ ...prev, [scanId]: status }))
          
          // Stop polling when done
          if (!status.is_running) {
            clearInterval(interval)
            fetchScans()
          }
        }
      } catch (error) {
        console.error('Failed to poll GPT status:', error)
        clearInterval(interval)
      }
    }, 2000) // Poll every 2 seconds
  }

  // Auto-poll GPT status for scans that are running on page load
  useEffect(() => {
    scans.forEach(scan => {
      if (scan.gpt_match_status === 'running' && !gptMatchStatus[scan.id]?.is_running) {
        pollGptMatchStatus(scan.id)
      }
    })
  }, [scans])

  // Convert matched sites to leads
  const convertToLeads = async (scanId: number) => {
    try {
      const response = await fetch(`/api/scans/${scanId}/convert-to-leads`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        console.log('👥 Leads created:', data)
        alert(`נוצרו ${data.converted} לידים חדשים (${data.skipped} כבר קיימים)`)
        fetchScans()
      }
    } catch (error) {
      console.error('Failed to convert to leads:', error)
    }
  }

  // AI Analysis for selected items only
  const startAIAnalysisSelected = async () => {
    if (!selectedScan || selectedResults.size === 0) return
    
    setAnalyzingAI(selectedScan.id)
    
    try {
      const response = await fetch(`/api/scans/${selectedScan.id}/analyze-business-type-selected`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedResults) })
      })
      
      if (response.ok) {
        // Start auto-refresh loop for AI stats
        fetchAIStats(selectedScan.id)
        setSelectedResults(new Set())
        setSelectAll(false)
      }
    } catch (error) {
      console.error('Failed to start AI analysis:', error)
      setAnalyzingAI(null)
    }
    // Don't set analyzingAI to null - let the auto-refresh handle it when done
  }

  // Auto-refresh results when analyzing
  useEffect(() => {
    if (!autoRefresh || !selectedScan) return

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/scans/${selectedScan.id}/queue?limit=100`)
        if (response.ok) {
          const data = await response.json()
          setScanResults(data)
          
          // Check if all items are processed
          const stillProcessing = data.some((r: ScanResult) => 
            r.status === 'pending' || r.status === 'analyzing'
          )
          
          if (!stillProcessing) {
            setAutoRefresh(false)
            fetchScans() // Refresh main list
          }
        }
      } catch (error) {
        console.error('Failed to refresh results:', error)
      }
    }, 2000) // Refresh every 2 seconds

    return () => clearInterval(interval)
  }, [autoRefresh, selectedScan])

  const viewResults = (scan: Scan) => {
    // Open modal immediately - non-blocking
    setSelectedScan(scan)
    setLoadingResults(true)
    setScanResults([]) // Clear old results
    setAiStats(null as any) // Clear old AI stats to prevent showing wrong scan's data
    
    // Fetch AI stats for THIS scan
    fetchAIStats(scan.id)
    
    // Fetch in background - non-blocking
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
    
    fetch(`/api/scans/${scan.id}/queue?limit=100`, { signal: controller.signal })
      .then(response => {
        clearTimeout(timeoutId)
        if (response.ok) return response.json()
        throw new Error('Failed to fetch')
      })
      .then(data => {
        setScanResults(data)
        setLoadingResults(false)
      })
      .catch(error => {
        if (error.name !== 'AbortError') {
          console.error('Failed to fetch results:', error)
        }
        setLoadingResults(false)
      })
  }

  return (
    <div className="space-y-6">
      {/* כותרת */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Search className="w-7 h-7" />
          ניהול סריקות
          {/* Background refresh indicator */}
          {backgroundRefresh && (
            <span className="flex items-center gap-1 text-sm font-normal text-green-600 bg-green-50 px-2 py-1 rounded-full">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              סריקה פעילה
            </span>
          )}
          {runningScan && (
            <span className="flex items-center gap-1 text-sm font-normal text-orange-600 bg-orange-50 px-2 py-1 rounded-full">
              <Loader2 className="w-3 h-3 animate-spin" />
              מפעיל סריקה...
            </span>
          )}
        </h1>
        <button 
          onClick={() => setShowModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          סריקה חדשה
        </button>
      </div>

      {/* GPU Control Bar */}
      <div className="card p-3 flex items-center justify-between bg-gradient-to-r from-green-50 to-blue-50 border border-green-200">
        <div className="flex items-center gap-3">
          <span className="text-lg">🎮</span>
          <span className="font-medium text-gray-700">GPU Control:</span>
          {gpuStatus && gpuStatus.count > 0 ? (
            <span className="text-green-600 font-medium flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              מודל טעון ({gpuStatus.loaded_models.length})
            </span>
          ) : (
            <span className="text-gray-500">מודל לא טעון</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadModelToGPU}
            disabled={loadingGPU || (gpuStatus?.count || 0) > 0}
            className={`btn text-sm flex items-center gap-1 ${
              (gpuStatus?.count || 0) > 0
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-green-500 hover:bg-green-600 text-white'
            }`}
          >
            {loadingGPU ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>🔥 טען ל-GPU</>
            )}
          </button>
          <button
            onClick={unloadModelFromGPU}
            disabled={loadingGPU || (gpuStatus?.count || 0) === 0}
            className={`btn text-sm flex items-center gap-1 ${
              (gpuStatus?.count || 0) === 0
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            }`}
          >
            {loadingGPU ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>❄️ הורד מ-GPU</>
            )}
          </button>
          
          {/* Stop All AI Button */}
          <div className="border-l pl-2 ml-2">
            <button
              onClick={() => stopAIAnalysis()}
              className="btn text-sm flex items-center gap-1 bg-red-500 hover:bg-red-600 text-white"
            >
              🛑 עצור הכל AI
            </button>
          </div>
        </div>
      </div>

      {/* Global Activity Status */}
      {(scans.some(s => s.status === 'running' && s.scanned_count < s.total_urls) || 
        Object.values(scanAIStats).some(s => s?.is_running) ||
        scans.some(s => s.rescan_status === 'running') ||
        scans.some(s => s.ai_current_domain?.startsWith('סורק תוכן'))) && (
        <div className="card p-4 bg-gradient-to-r from-purple-50 via-blue-50 to-green-50 border border-purple-200">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">📡</span>
            <span className="font-bold text-gray-800">פעילות נוכחית</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Apify Scans */}
            <div className="bg-white rounded-lg p-3 border">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-green-600">🔍</span>
                <span className="font-medium text-sm">סריקות Apify</span>
              </div>
              {scans.filter(s => s.status === 'running' && s.scanned_count < s.total_urls).length > 0 ? (
                scans.filter(s => s.status === 'running' && s.scanned_count < s.total_urls).map(scan => (
                  <div key={scan.id} className="text-xs flex items-center gap-2 py-1">
                    <Loader2 className="w-3 h-3 animate-spin text-green-500" />
                    <span className="font-medium">{scan.name}</span>
                    <span className="text-gray-500">({scan.scanned_count}/{scan.total_urls})</span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400">אין סריקות פעילות</div>
              )}
            </div>
            
            {/* Content + Navigation Rescan */}
            <div className="bg-white rounded-lg p-3 border">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-purple-600">🎯</span>
                <span className="font-medium text-sm">סריקה מלאה</span>
              </div>
              {scans.filter(s => s.rescan_status === 'running').length > 0 ? (
                scans.filter(s => s.rescan_status === 'running').map(scan => (
                  <div key={scan.id} className="text-xs flex items-center gap-2 py-1">
                    <Loader2 className="w-3 h-3 animate-spin text-purple-500" />
                    <span className="font-medium">{scan.name}</span>
                    <span className="text-gray-500">({scan.rescan_processed}/{scan.rescan_total})</span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400">אין סריקות פעילות</div>
              )}
            </div>
            
            {/* AI Classification */}
            <div className="bg-white rounded-lg p-3 border">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-purple-600">🤖</span>
                <span className="font-medium text-sm">סיווג AI</span>
              </div>
              {Object.entries(scanAIStats).filter(([_, s]) => s?.is_running).length > 0 ? (
                Object.entries(scanAIStats).filter(([_, s]) => s?.is_running).map(([scanId, stats]) => {
                  const scan = scans.find(s => s.id === parseInt(scanId))
                  return (
                    <div key={scanId} className="text-xs flex items-center gap-2 py-1">
                      <Loader2 className="w-3 h-3 animate-spin text-purple-500" />
                      <span className="font-medium">{scan?.name || `סריקה ${scanId}`}</span>
                      <span className="text-gray-500">({stats?.ai_processed}/{stats?.ai_total})</span>
                    </div>
                  )
                })
              ) : (
                <div className="text-xs text-gray-400">אין סיווג AI פעיל</div>
              )}
            </div>
            
            {/* Deep Scan */}
            <div className="bg-white rounded-lg p-3 border">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-teal-600">🔬</span>
                <span className="font-medium text-sm">סריקה מעמיקה</span>
              </div>
              {(() => {
                const runningScans = scans.filter(s => s.deep_scan_status === 'running')
                console.log('🔬 Deep scan check:', { 
                  total: scans.length, 
                  running: runningScans.length,
                  statuses: scans.map(s => ({ id: s.id, name: s.name, status: s.deep_scan_status }))
                })
                return runningScans.length > 0 ? (
                  runningScans.map(scan => (
                    <div key={scan.id} className="text-xs flex items-center gap-2 py-1">
                      <Loader2 className="w-3 h-3 animate-spin text-teal-500" />
                      <span className="font-medium">{scan.name}</span>
                      <span className="text-gray-500">({scan.deep_scan_processed || 0}/{scan.deep_scan_total || 0})</span>
                      {scan.deep_scan_current && (
                        <span className="text-gray-400 truncate max-w-[150px]">{scan.deep_scan_current}</span>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-gray-400">אין סריקות מעמיקות פעילות</div>
                )
              })()}
            </div>
            
            {/* Calculator Matching */}
            <div className="bg-white rounded-lg p-3 border">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-indigo-600">🧮</span>
                <span className="font-medium text-sm">התאמת מחשבונים</span>
              </div>
              {scans.filter(s => s.calc_match_status === 'running').length > 0 ? (
                scans.filter(s => s.calc_match_status === 'running').map(scan => (
                  <div key={scan.id} className="text-xs flex items-center gap-2 py-1">
                    <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />
                    <span className="font-medium">{scan.name}</span>
                    <span className="text-gray-500">({scan.calc_match_processed || 0}/{scan.calc_match_total || 0})</span>
                  </div>
                ))
              ) : (
                <div className="text-xs text-gray-400">אין התאמות פעילות</div>
              )}
            </div>

            {/* GPT Calculator Matching */}
            <div className="bg-white rounded-lg p-3 border">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-green-600">⚡</span>
                <span className="font-medium text-sm">GPT התאמה</span>
              </div>
              {Object.entries(gptMatchStatus).filter(([_, s]) => s.is_running).length > 0 ? (
                Object.entries(gptMatchStatus)
                  .filter(([_, s]) => s.is_running)
                  .map(([scanId, status]) => (
                    <div key={scanId} className="text-xs">
                      <div className="flex items-center gap-2 py-1">
                        <Loader2 className="w-3 h-3 animate-spin text-green-500" />
                        <span className="font-medium">{status.current_site || '...'}</span>
                        <span className="text-gray-500">({status.processed || 0}/{status.total || 0})</span>
                      </div>
                      {status.logs?.length > 0 && (
                        <div className="text-xs text-gray-500 mt-1">
                          {status.logs.slice(-3).map((log: string, i: number) => (
                            <div key={i} className="truncate">{log}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
              ) : (
                <div className="text-xs text-gray-400">אין התאמות GPT פעילות</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* רשימת סריקות */}
      <div className="space-y-4">
        {loading ? (
          Array(3).fill(0).map((_, i) => (
            <div key={i} className="card h-32 animate-pulse bg-gray-100"></div>
          ))
        ) : scans.length === 0 ? (
          <div className="card text-center py-12">
            <Search className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 mb-4">לא נמצאו סריקות</p>
            <button onClick={() => setShowModal(true)} className="btn btn-primary">
              צור סריקה ראשונה
            </button>
          </div>
        ) : (
          scans.map((scan) => (
            <div key={scan.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-lg">{scan.name}</h3>
                  <p className="text-sm text-gray-500">
                    {new Date(scan.created_at).toLocaleDateString('he-IL')}
                  </p>
                </div>
                <span className={`badge ${statusColors[scan.status]}`}>
                  {statusLabels[scan.status]}
                </span>
              </div>

              {/* Keywords */}
              <div className="flex flex-wrap gap-2 mb-4">
                {scan.keywords?.slice(0, 5).map((kw, i) => (
                  <span key={i} className="text-xs px-2 py-1 bg-gray-100 rounded">
                    {kw}
                  </span>
                ))}
                {scan.keywords?.length > 5 && (
                  <span className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-500">
                    +{scan.keywords.length - 5} נוספים
                  </span>
                )}
              </div>

              {/* Progress - Live Status - hide when complete */}
              {scan.status === 'running' && scan.scanned_count < scan.total_urls && (
                <div className="mb-4 p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="flex items-center gap-2 text-green-700 font-medium">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                      </span>
                      🔍 סריקה פעילה מ-Apify
                    </span>
                    <span className="text-sm font-bold text-green-800">
                      {scan.scanned_count} / {scan.total_urls} URLs
                    </span>
                  </div>
                  <div className="w-full h-3 bg-green-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-green-500 to-green-600 rounded-full transition-all duration-500"
                      style={{ width: `${scan.total_urls ? (scan.scanned_count / scan.total_urls) * 100 : 0}%` }}
                    />
                  </div>
                  <div className="text-xs text-green-600 mt-2 text-center">
                    {Math.round(scan.total_urls ? (scan.scanned_count / scan.total_urls) * 100 : 0)}% הושלם
                  </div>
                </div>
              )}

              {/* Stats - Row 1: Main */}
              <div className="grid grid-cols-4 gap-4 mb-2">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{scan.total_urls}</div>
                  <div className="text-xs text-gray-500">URLs</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{scan.scanned_count}</div>
                  <div className="text-xs text-gray-500">נסרקו</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {scan.matched_count}
                    <span className="text-sm text-gray-400 font-normal">/{scan.total_urls}</span>
                  </div>
                  <div className="text-xs text-gray-500">התאמות</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{scan.contacted_count}</div>
                  <div className="text-xs text-gray-500">נוצר קשר</div>
                </div>
              </div>
              
              {/* Stats - Row 2: Extended */}
              <div className="grid grid-cols-5 gap-4 mb-4 pt-2 border-t border-gray-100">
                <div className="text-center">
                  <div className="text-lg font-semibold text-orange-600">
                    {scan.whois_contacts || 0}
                    <span className="text-sm text-gray-400 font-normal">/{scan.total_urls}</span>
                  </div>
                  <div className="text-xs text-gray-500">📧 פרטי קשר WHOIS</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-teal-600">
                    {scan.has_content || 0}
                    <span className="text-sm text-gray-400 font-normal">/{scan.total_urls}</span>
                  </div>
                  <div className="text-xs text-gray-500">📄 יש תוכן</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-indigo-600">
                    {scan.ai_analyzed || 0}
                    <span className="text-sm text-gray-400 font-normal">/{scan.total_urls}</span>
                  </div>
                  <div className="text-xs text-gray-500">🤖 נותחו AI</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-pink-600">
                    {scan.calc_matched || 0}
                    <span className="text-sm text-gray-400 font-normal">/{scan.has_content || 0}</span>
                  </div>
                  <div className="text-xs text-gray-500">🔢 שויכו (Ollama)</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-emerald-600">
                    {scan.gpt_calc_matched || 0}
                    <span className="text-sm text-gray-400 font-normal">/{scan.has_content || 0}</span>
                  </div>
                  <div className="text-xs text-gray-500">⚡ שויכו (GPT)</div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                {scan.status === 'pending' || scan.status === 'paused' ? (
                  <button
                    onClick={() => startScan(scan.id)}
                    disabled={runningScan === scan.id}
                    className={`btn flex items-center gap-1 ${
                      runningScan === scan.id 
                        ? 'btn-secondary cursor-not-allowed opacity-70' 
                        : 'btn-primary'
                    }`}
                  >
                    {runningScan === scan.id ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        מפעיל...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        התחל סריקה
                      </>
                    )}
                  </button>
                ) : scan.status === 'running' ? (
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      סורק... ({scan.scanned_count}/{scan.total_urls})
                    </span>
                    <button
                      onClick={() => pauseScan(scan.id)}
                      className="btn btn-warning flex items-center gap-1"
                    >
                      <Pause className="w-4 h-4" />
                      השהה
                    </button>
                  </div>
                ) : scan.status === 'completed' && scan.total_urls > scan.scanned_count ? (
                  <button
                    onClick={() => startAnalysis(scan)}
                    disabled={analyzing === scan.id || autoRefresh}
                    className={`btn flex items-center gap-1 ${
                      analyzing === scan.id || autoRefresh 
                        ? 'btn-secondary cursor-not-allowed opacity-70' 
                        : 'btn-primary'
                    }`}
                  >
                    {analyzing === scan.id || autoRefresh ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        מנתח... ({scan.scanned_count}/{scan.total_urls})
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        נתח אתרים
                      </>
                    )}
                  </button>
                ) : scan.status === 'completed' && scan.total_urls === scan.scanned_count ? (
                  <span className="text-green-600 text-sm flex items-center gap-1">
                    ✅ הניתוח הושלם
                  </span>
                ) : null}

                <button 
                  onClick={() => viewResults(scan)}
                  className="btn btn-secondary flex items-center gap-1"
                >
                  <Eye className="w-4 h-4" />
                  צפייה בתוצאות
                </button>

                {/* AI Classification Button - show when has URLs */}
                {scan.total_urls > 0 && (
                  <div className="flex items-center gap-1">
                    <button 
                      onClick={() => startAIAnalysis(scan)}
                      disabled={analyzingAI === scan.id || scanAIStats?.[scan.id]?.is_running}
                      className={`btn flex items-center gap-1 ${
                        analyzingAI === scan.id || scanAIStats?.[scan.id]?.is_running
                          ? 'btn-secondary cursor-not-allowed opacity-70' 
                          : 'bg-purple-600 hover:bg-purple-700 text-white'
                      }`}
                    >
                      {analyzingAI === scan.id || scanAIStats?.[scan.id]?.is_running ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          מסווג AI...
                        </>
                      ) : (
                        <>🤖 סיווג AI ({(scan.has_content || 0) - (scan.ai_analyzed || 0)})</>
                      )}
                    </button>
                    
                    {/* Stop AI button - only show when running */}
                    {scanAIStats?.[scan.id]?.is_running && (
                      <button 
                        onClick={() => stopAIAnalysis(scan.id)}
                        className="btn bg-red-500 hover:bg-red-600 text-white flex items-center gap-1"
                        title="עצור סיווג AI"
                      >
                        🛑
                      </button>
                    )}
                    
                    {/* Rescan sites without content */}
                    {(scan.total_urls - (scan.has_content || 0)) > 0 && (
                      <button 
                        onClick={() => rescanNoContent(scan.id)}
                        className="btn bg-orange-500 hover:bg-orange-600 text-white flex items-center gap-1"
                        title="סרוק מחדש אתרים ללא תוכן"
                      >
                        🔄 סרוק שוב ({scan.total_urls - (scan.has_content || 0)})
                      </button>
                    )}

                    {/* Rescan ALL - content + navigation + meta */}
                    {scan.status === 'completed' && (
                      <button 
                        onClick={() => rescanForNavigation(scan.id)}
                        disabled={scan.rescan_status === 'running'}
                        className={`btn flex items-center gap-1 ${
                          scan.rescan_status === 'running'
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-purple-500 hover:bg-purple-600'
                        } text-white`}
                        title="סריקה מלאה: תוכן + תפריטים + מטא לכל האתרים"
                      >
                        {scan.rescan_status === 'running' ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            סורק ({scan.rescan_processed}/{scan.rescan_total})
                          </>
                        ) : (
                          <>
                            🎯 סרוק הכל ({scan.total_urls})
                          </>
                        )}
                      </button>
                    )}

                    {/* Deep Scan button - only for completed scans with AI analyzed sites */}
                    {scan.status === 'completed' && (scan.ai_analyzed || 0) > 0 && (
                      <button 
                        onClick={() => startDeepScan(scan.id)}
                        disabled={scan.deep_scan_status === 'running'}
                        className={`btn flex items-center gap-1 ${
                          scan.deep_scan_status === 'running' 
                            ? 'bg-gray-400 cursor-not-allowed' 
                            : 'bg-teal-500 hover:bg-teal-600'
                        } text-white`}
                        title={scan.deep_scan_status === 'running' ? 'סריקה מעמיקה פעילה...' : 'סריקה מעמיקה של אתרים מתאימים'}
                      >
                        {scan.deep_scan_status === 'running' ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            סורק ({scan.deep_scan_processed}/{scan.deep_scan_total})
                          </>
                        ) : (
                          <>
                            🔬 סריקה מעמיקה
                          </>
                        )}
                      </button>
                    )}

                    {/* Match Calculators button - show after AI classification (no deep scan needed!) */}
                    {scan.status === 'completed' && (scan.ai_analyzed || 0) > 0 && (
                      <button 
                        onClick={() => startMatchCalculators(scan.id)}
                        disabled={scan.calc_match_status === 'running'}
                        className={`btn flex items-center gap-1 ${
                          scan.calc_match_status === 'running'
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-indigo-500 hover:bg-indigo-600'
                        } text-white`}
                        title={scan.calc_match_status === 'running' ? 'התאמת מחשבונים פעילה...' : 'התאם מחשבונים מדף הבית (מהיר!)'}
                      >
                        {scan.calc_match_status === 'running' ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            מתאים ({scan.calc_match_processed}/{scan.calc_match_total})
                          </>
                        ) : (
                          <>
                            🧮 התאם מחשבונים
                          </>
                        )}
                      </button>
                    )}

                    {/* GPT Match Calculators button */}
                    {scan.status === 'completed' && (scan.ai_analyzed || 0) > 0 && (
                      <button 
                        onClick={() => startMatchCalculatorsGPT(scan.id)}
                        disabled={scan.gpt_match_status === 'running' || gptMatchStatus[scan.id]?.is_running}
                        className={`btn flex items-center gap-1 ${
                          scan.gpt_match_status === 'running' || gptMatchStatus[scan.id]?.is_running
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-green-500 hover:bg-green-600'
                        } text-white`}
                        title={scan.gpt_match_status === 'running' ? 'התאמת GPT פעילה...' : 'התאם מחשבונים עם OpenAI GPT (מהיר!)'}
                      >
                        {scan.gpt_match_status === 'running' || gptMatchStatus[scan.id]?.is_running ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            GPT ({gptMatchStatus[scan.id]?.processed || scan.gpt_match_processed || 0}/{gptMatchStatus[scan.id]?.total || scan.gpt_match_total || 0})
                          </>
                        ) : (
                          <>
                            ⚡ שבץ GPT
                          </>
                        )}
                      </button>
                    )}

                    {/* Convert to Leads button - only if calc matched */}
                    {(scan.calc_matched || 0) > 0 && (
                      <button 
                        onClick={() => convertToLeads(scan.id)}
                        className="btn bg-green-500 hover:bg-green-600 text-white flex items-center gap-1"
                        title="המרה ללידים"
                      >
                        👥 צור לידים ({scan.calc_matched})
                      </button>
                    )}
                  </div>
                )}

                {/* AI Status - show when AI is analyzing this scan */}
                {scanAIStats?.[scan.id]?.is_running && (
                  <div className="flex items-center gap-2 text-sm text-purple-700 bg-purple-50 px-3 py-1 rounded-full">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>
                      {scanAIStats[scan.id]?.ai_current_domain || '...'} ({scanAIStats[scan.id]?.ai_processed || 0}/{scanAIStats[scan.id]?.ai_total || 0})
                    </span>
                  </div>
                )}

                {/* GPT Match Status Panel */}
                {gptMatchStatus[scan.id]?.is_running && (
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Loader2 className="w-4 h-4 animate-spin text-green-600" />
                      <span className="font-medium text-green-700">
                        ⚡ GPT Matching: {gptMatchStatus[scan.id]?.current_site || '...'}
                      </span>
                      <span className="text-sm text-green-600">
                        ({gptMatchStatus[scan.id]?.processed || 0}/{gptMatchStatus[scan.id]?.total || 0})
                      </span>
                    </div>
                    {gptMatchStatus[scan.id]?.logs?.length > 0 && (
                      <div className="max-h-32 overflow-y-auto text-xs space-y-1 font-mono bg-white p-2 rounded border">
                        {gptMatchStatus[scan.id]?.logs?.slice(-10).map((log: string, idx: number) => (
                          <div key={idx} className={log.startsWith('✅') ? 'text-green-600' : 'text-red-600'}>
                            {log}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Retry button for failed scans */}
                {scan.status === 'failed' && (
                  <button
                    onClick={() => retryScan(scan.id)}
                    disabled={runningScan === scan.id}
                    className={`btn flex items-center gap-1 ${
                      runningScan === scan.id 
                        ? 'bg-orange-300 cursor-not-allowed' 
                        : 'bg-orange-500 hover:bg-orange-600'
                    } text-white`}
                  >
                    {runningScan === scan.id ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        מפעיל...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4" />
                        נסה שוב
                      </>
                    )}
                  </button>
                )}

                <button
                  onClick={() => deleteScan(scan.id)}
                  className="btn btn-secondary text-danger-600 mr-auto"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Grouped by Owner Section */}
      <div className="card mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            👥 קיבוץ לפי בעלים
            <span className="text-sm font-normal text-gray-500">(בעלים עם מספר אתרים)</span>
          </h2>
          <button
            onClick={fetchGroupedOwners}
            disabled={loadingOwners}
            className="btn btn-primary text-sm flex items-center gap-1"
          >
            {loadingOwners ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            טען קיבוצים
          </button>
        </div>
        
        {groupedOwners && (
          <div className="space-y-4">
            {/* Stats */}
            <div className="flex gap-4 text-sm mb-4">
              <span className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full">
                👥 בעלים עם 2+ אתרים: {groupedOwners.multi_domain_count}
              </span>
              <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-full">
                👤 בעלים עם אתר אחד: {groupedOwners.single_domain_count}
              </span>
            </div>
            
            {/* Multi-domain owners */}
            {groupedOwners.multi_domain_owners.length > 0 ? (
              <div className="space-y-3">
                {groupedOwners.multi_domain_owners.map((owner: any, idx: number) => (
                  <div key={idx} className="border rounded-lg p-4 bg-purple-50 hover:bg-purple-100 transition">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold text-purple-800">
                            {owner.domain_count} אתרים
                          </span>
                          {owner.owner_name && (
                            <span className="text-gray-700">👤 {owner.owner_name}</span>
                          )}
                        </div>
                        {owner.owner_email && (
                          <div className="text-blue-600 text-sm mt-1">
                            ✉️ {owner.owner_email}
                          </div>
                        )}
                        {owner.owner_phone && (
                          <div className="text-green-600 text-sm">
                            📱 {owner.owner_phone}
                          </div>
                        )}
                      </div>
                      <button className="btn btn-sm bg-green-500 hover:bg-green-600 text-white">
                        📧 שלח הודעה משותפת
                      </button>
                    </div>
                    
                    {/* Domains list */}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {owner.domains.map((d: any) => (
                        <a
                          key={d.id}
                          href={d.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`text-xs px-2 py-1 rounded ${
                            d.business_type === 'lead_site' ? 'bg-green-100 text-green-700' :
                            d.business_type === 'small_business' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {d.domain}
                        </a>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                לא נמצאו בעלים עם מספר אתרים. נתח יותר אתרים כדי למצוא קיבוצים.
              </div>
            )}
          </div>
        )}
        
        {!groupedOwners && !loadingOwners && (
          <div className="text-center py-8 text-gray-500">
            לחץ "טען קיבוצים" כדי לראות בעלים עם מספר אתרים
          </div>
        )}
      </div>

      {/* Global Rescan Status */}
      {globalRescanStatus?.is_running && (
        <div className="card mt-8 bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-blue-800 flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              סריקה גלובלית פועלת - {globalRescanStatus.phase === 'rescan' ? 'שלב סריקת תוכן' : 'שלב התאמת מחשבונים'}
            </h3>
            <button
              onClick={stopGlobalRescan}
              className="btn btn-secondary text-sm bg-red-100 text-red-700 hover:bg-red-200"
            >
              עצור
            </button>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div className="bg-white rounded p-3">
              <div className="text-sm text-gray-600">סריקת תוכן</div>
              <div className="text-lg font-bold text-blue-700">
                {globalRescanStatus.rescan_processed}/{globalRescanStatus.rescan_total}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${globalRescanStatus.rescan_total > 0 ? (globalRescanStatus.rescan_processed / globalRescanStatus.rescan_total) * 100 : 0}%` }}
                />
              </div>
            </div>
            <div className="bg-white rounded p-3">
              <div className="text-sm text-gray-600">התאמת מחשבונים</div>
              <div className="text-lg font-bold text-green-700">
                {globalRescanStatus.match_processed}/{globalRescanStatus.match_total}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div 
                  className="bg-green-500 h-2 rounded-full transition-all"
                  style={{ width: `${globalRescanStatus.match_total > 0 ? (globalRescanStatus.match_processed / globalRescanStatus.match_total) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
          
          <div className="text-sm text-blue-700 mb-2">
            <strong>כרגע:</strong> {globalRescanStatus.current_site}
          </div>
          
          <div className="bg-gray-900 text-green-400 p-3 rounded text-xs font-mono max-h-32 overflow-y-auto">
            {globalRescanStatus.logs.slice(-10).map((log, idx) => (
              <div key={idx}>{log}</div>
            ))}
          </div>
        </div>
      )}

      {/* All Domains Section */}
      <div className="card mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            🌐 כל הדומיינים שנסרקו
            <span className="text-sm font-normal text-gray-500">({totalDomains} יוניקים)</span>
          </h2>
          <div className="flex items-center gap-3 flex-wrap">
            {/* Global Rescan Button */}
            <button
              onClick={startGlobalRescan}
              disabled={globalRescanStatus?.is_running}
              className="btn btn-primary text-sm bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
            >
              {globalRescanStatus?.is_running ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                  סורק...
                </>
              ) : (
                '🔄 סרוק ללא תוכן + התאם'
              )}
            </button>
            
            {/* Status Filter */}
            <select
              className="input w-40"
              value={statusFilter}
              onChange={(e) => { 
                setStatusFilter(e.target.value); 
                setDomainPage(0); 
                fetchAllDomains(0, e.target.value, contentFilter);
              }}
            >
              <option value="">כל הסטטוסים</option>
              <option value="matched">✅ התאמה</option>
              <option value="discarded">❌ נדחה</option>
              <option value="pending">⏳ ממתין</option>
            </select>
            
            {/* Content Filter */}
            <select
              className="input w-48"
              value={contentFilter}
              onChange={(e) => { 
                setContentFilter(e.target.value); 
                setDomainPage(0);
                fetchAllDomains(0, statusFilter, e.target.value);
              }}
            >
              <option value="">הכל</option>
              <option value="has_content">📄 עם תוכן</option>
              <option value="analyzed">🤖 נותח AI</option>
              <option value="lead_site">🎯 אתר לידים ✅</option>
              <option value="small_business">💼 עסק קטן ✅</option>
              <option value="blacklisted">🚫 נחסמו</option>
              <option value="bank">🏦 בנקים</option>
              <option value="insurance">🛡️ ביטוח</option>
              <option value="corporation">🏢 תאגידים</option>
              <option value="government">🏛️ ממשלה</option>
              <option value="news">📰 חדשות</option>
            </select>
            
            <input
              type="text"
              placeholder="חפש דומיין..."
              className="input w-48"
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
            />
            <button
              onClick={() => fetchAllDomains(domainPage, statusFilter, contentFilter)}
              className="btn btn-secondary text-sm"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {loadingDomains && allDomains.length === 0 ? (
          <div className="text-center py-8">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            טוען דומיינים...
          </div>
        ) : allDomains.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            לא נמצאו דומיינים. הפעל סריקה כדי להתחיל לאסוף דומיינים.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse min-w-[1600px]">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-64">דומיין</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-28">סטטוס</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-28">סוג עסק</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-44">WHOIS</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-20">תוכן</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-44">פרטי קשר</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700">סריקה</th>
                  <th className="text-right p-3 border-b font-medium text-gray-700 w-20">פעולות</th>
                </tr>
              </thead>
              <tbody>
                {allDomains
                  .filter(d => {
                    // Text filter
                    if (domainFilter && !d.domain.includes(domainFilter) && !d.title?.includes(domainFilter)) return false
                    // Status filter
                    if (statusFilter && d.status !== statusFilter) return false
                    // Content filter
                    if (contentFilter === 'has_content' && !d.has_content) return false
                    if (contentFilter === 'analyzed' && !d.business_type) return false
                    if (contentFilter === 'lead_site' && d.business_type !== 'lead_site') return false
                    if (contentFilter === 'small_business' && d.business_type !== 'small_business') return false
                    if (contentFilter === 'deep_scanned' && !d.deep_scanned) return false
                    if (contentFilter === 'blacklisted' && !d.is_blacklisted) return false
                    if (contentFilter === 'bank' && d.business_type !== 'bank') return false
                    if (contentFilter === 'insurance' && d.business_type !== 'insurance') return false
                    if (contentFilter === 'corporation' && d.business_type !== 'corporation') return false
                    if (contentFilter === 'government' && d.business_type !== 'government') return false
                    if (contentFilter === 'news' && d.business_type !== 'news') return false
                    return true
                  })
                  .map((domain, idx) => (
                  <tr key={idx} className={`hover:bg-gray-50 border-b ${domain.is_blacklisted ? 'bg-red-50 opacity-60' : ''}`}>
                    {/* Domain */}
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <img 
                          src={`https://www.google.com/s2/favicons?domain=${domain.domain}&sz=16`}
                          alt=""
                          className="w-4 h-4"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                        />
                        <div>
                          <a 
                            href={domain.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline font-medium"
                          >
                            {domain.domain}
                          </a>
                          {domain.is_blacklisted && <span className="text-xs text-red-500 mr-2">🚫 חסום</span>}
                          {domain.title && (
                            <div className="text-xs text-gray-400 truncate max-w-[200px]">
                              {domain.title}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    
                    {/* Status */}
                    <td className="p-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        domain.status === 'pending' ? 'bg-gray-100 text-gray-600' :
                        domain.status === 'matched' ? 'bg-green-100 text-green-700' :
                        domain.status === 'discarded' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {domain.status === 'pending' && 'ממתין'}
                        {domain.status === 'matched' && '✅ התאמה'}
                        {domain.status === 'discarded' && '❌ נדחה'}
                        {domain.status === 'analyzing' && '🔄 מנתח'}
                      </span>
                    </td>
                    
                    {/* Business Type */}
                    <td className="p-3">
                      {domain.business_type ? (
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          domain.business_type === 'lead_site' ? 'bg-emerald-100 text-emerald-700' :
                          domain.business_type === 'small_business' ? 'bg-green-100 text-green-700' :
                          domain.business_type === 'bank' ? 'bg-blue-100 text-blue-700' :
                          domain.business_type === 'insurance' ? 'bg-orange-100 text-orange-700' :
                          domain.business_type === 'corporation' ? 'bg-red-100 text-red-700' :
                          domain.business_type === 'fintech' ? 'bg-purple-100 text-purple-700' :
                          'bg-gray-100 text-gray-600'
                        }`} title={domain.business_type_reason || ''}>
                          {domain.business_type === 'lead_site' && '🎯 לידים'}
                          {domain.business_type === 'small_business' && '💼 עסק קטן'}
                          {domain.business_type === 'bank' && '🏦 בנק'}
                          {domain.business_type === 'insurance' && '🛡️ ביטוח'}
                          {domain.business_type === 'corporation' && '🏢 תאגיד'}
                          {domain.business_type === 'fintech' && '🚀 פינטק'}
                          {domain.business_type === 'content_site' && '📰 תוכן'}
                          {domain.business_type === 'unknown' && '❓'}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    
                    {/* WHOIS */}
                    <td className="p-3">
                      {domain.whois_is_private ? (
                        <span className="text-xs text-gray-400">🔒 פרטי</span>
                      ) : domain.owner_email || domain.owner_name ? (
                        <div className="text-xs space-y-0.5">
                          {domain.owner_name && <div className="truncate max-w-[150px]">👤 {domain.owner_name}</div>}
                          {domain.owner_email && <div className="text-blue-600 truncate max-w-[150px]">✉️ {domain.owner_email}</div>}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    
                    {/* Content */}
                    <td className="p-3 text-center">
                      {domain.html_text ? (
                        <button
                          onClick={() => setViewingContent({
                            domain: domain.domain,
                            content: domain.html_text || ''
                          })}
                          className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-600 px-2 py-1 rounded"
                        >
                          📄 צפה
                        </button>
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                    
                    {/* Contact Info */}
                    <td className="p-3">
                      {domain.description ? (
                        <div className="text-xs text-gray-600 truncate max-w-[180px]" title={domain.description}>
                          {domain.description}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    
                    {/* Campaign */}
                    <td className="p-3">
                      <span className="text-sm text-gray-600">{domain.campaign_name}</span>
                    </td>
                    
                    {/* Actions */}
                    <td className="p-3">
                      {!domain.is_blacklisted ? (
                        <button
                          onClick={() => blacklistDomain(domain.id)}
                          className="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-2 py-1 rounded"
                          title="הוסף לרשימה שחורה"
                        >
                          🚫
                        </button>
                      ) : (
                        <button
                          onClick={() => unblacklistDomain(domain.id)}
                          className="text-xs bg-green-50 hover:bg-green-100 text-green-600 px-2 py-1 rounded"
                          title="הסר מהרשימה השחורה"
                        >
                          ✅
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {/* Pagination */}
            {totalDomains > DOMAINS_PER_PAGE && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="text-sm text-gray-500">
                  מציג {domainPage * DOMAINS_PER_PAGE + 1} - {Math.min((domainPage + 1) * DOMAINS_PER_PAGE, totalDomains)} מתוך {totalDomains}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDomainPageChange(domainPage - 1)}
                    disabled={domainPage === 0 || loadingDomains}
                    className="btn btn-secondary text-sm disabled:opacity-50"
                  >
                    ← הקודם
                  </button>
                  <span className="flex items-center px-3 text-sm">
                    עמוד {domainPage + 1} מתוך {Math.ceil(totalDomains / DOMAINS_PER_PAGE)}
                  </span>
                  <button
                    onClick={() => handleDomainPageChange(domainPage + 1)}
                    disabled={(domainPage + 1) * DOMAINS_PER_PAGE >= totalDomains || loadingDomains}
                    className="btn btn-secondary text-sm disabled:opacity-50"
                  >
                    הבא →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <ScanModal
          onClose={() => setShowModal(false)}
          onCreated={fetchScans}
        />
      )}

      {/* Results Modal with Live Status */}
      {selectedScan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2">
          <div className="bg-white rounded-lg w-full max-w-[95vw] max-h-[95vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b flex justify-between items-center shrink-0">
              <div>
                <h2 className="text-xl font-bold">
                  תוצאות: {selectedScan.name}
                </h2>
                <div className="text-sm text-gray-500 mt-1 flex gap-4">
                  <span>סה"כ: {scanResults.length}</span>
                  <span className="text-yellow-600">⏳ ממתין: {scanResults.filter(r => r.status === 'pending').length}</span>
                  <span className="text-blue-600">🔄 מנתח: {scanResults.filter(r => r.status === 'analyzing').length}</span>
                  <span className="text-green-600">✅ נמצא: {scanResults.filter(r => r.status === 'matched').length}</span>
                  <span className="text-red-600">❌ נדחה: {scanResults.filter(r => r.status === 'discarded').length}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* AI Analysis Buttons */}
                <div className="flex items-center gap-2 border-l pl-3 ml-2">
                  <button 
                    onClick={() => startAIAnalysis(selectedScan)}
                    disabled={analyzingAI === selectedScan.id}
                    className={`btn text-sm flex items-center gap-1 ${
                      analyzingAI === selectedScan.id 
                        ? 'btn-secondary cursor-not-allowed opacity-70' 
                        : 'bg-purple-600 hover:bg-purple-700 text-white'
                    }`}
                  >
                    {analyzingAI === selectedScan.id ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        מנתח...
                      </>
                    ) : (
                      <>🤖 סווג הכל</>
                    )}
                  </button>
                  
                  <button 
                    onClick={startAIAnalysisSelected}
                    disabled={analyzingAI === selectedScan.id || selectedResults.size === 0}
                    className={`btn text-sm flex items-center gap-1 ${
                      selectedResults.size === 0
                        ? 'btn-secondary cursor-not-allowed opacity-50' 
                        : 'bg-purple-500 hover:bg-purple-600 text-white'
                    }`}
                  >
                    {selectedAlreadyAnalyzed > 0 ? (
                      <>🔄 נתח מחדש ({selectedAlreadyAnalyzed}) + חדשים ({selectedNotAnalyzed})</>
                    ) : (
                      <>🎯 סווג נבחרים ({selectedResults.size})</>
                    )}
                  </button>
                </div>
                <button 
                  onClick={() => viewResults(selectedScan)}
                  className="btn btn-secondary text-sm flex items-center gap-1"
                >
                  <RefreshCw className="w-4 h-4" />
                  רענן
                </button>
                <button 
                  onClick={() => setSelectedScan(null)}
                  className="text-gray-500 hover:text-gray-700 text-2xl px-2"
                >
                  ×
                </button>
              </div>
            </div>
            
            {/* AI Stats Bar */}
            {aiStats && (
              <div className="px-4 py-2 bg-purple-50 border-b">
                {/* Real-time progress */}
                {aiStats.is_running && (
                  <div className="flex items-center gap-3 mb-2 pb-2 border-b border-purple-200">
                    <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                    <span className="font-medium text-purple-800">
                      🤖 מנתח [{aiStats.ai_processed}/{aiStats.ai_total}]:
                    </span>
                    <span className="text-purple-600 font-mono">
                      {aiStats.ai_current_domain}
                    </span>
                    <div className="flex-1 bg-purple-200 rounded-full h-2 ml-2">
                      <div 
                        className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                        style={{width: `${aiStats.ai_total ? (aiStats.ai_processed! / aiStats.ai_total) * 100 : 0}%`}}
                      />
                    </div>
                  </div>
                )}
                
                {/* Stats */}
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="font-medium text-purple-800">📊 סיכום:</span>
                  <span className="text-emerald-600 font-bold">🎯 לידים: {aiStats.type_counts?.lead_site || 0}</span>
                  <span className="text-green-600 font-bold">💼 עסק קטן: {aiStats.type_counts?.small_business || 0}</span>
                  <span className="text-teal-600">📰 תוכן: {aiStats.type_counts?.content_site || 0}</span>
                  <span className="text-gray-400">|</span>
                  <span className="text-blue-500">🏦 בנק: {aiStats.type_counts?.bank || 0}</span>
                  <span className="text-orange-500">🛡️ ביטוח: {aiStats.type_counts?.insurance || 0}</span>
                  <span className="text-red-500">🏢 תאגיד: {aiStats.type_counts?.corporation || 0}</span>
                  <span className="text-purple-500">🚀 פינטק: {aiStats.type_counts?.fintech || 0}</span>
                  <span className="text-gray-400">|</span>
                  <span className="text-gray-500">❓ ממתין: {aiStats.not_analyzed || 0}</span>
                </div>
              </div>
            )}
            
            <div className="flex-1 overflow-y-auto p-4">
              {loadingResults ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-primary-600" />
                  טוען תוצאות...
                </div>
              ) : scanResults.length === 0 ? (
                <div className="text-center py-8 text-gray-500">לא נמצאו תוצאות</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse min-w-[1400px]">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="p-3 border-b w-10">
                          <input 
                            type="checkbox"
                            checked={selectAll}
                            onChange={toggleSelectAll}
                            className="w-4 h-4 rounded border-gray-300"
                            title="בחר הכל (שלא נותחו)"
                          />
                        </th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 w-16">תצוגה</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700">אתר</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 w-24">סטטוס</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 w-28">סוג עסק</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 w-44">WHOIS</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 w-20">תוכן</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 w-32">סריקה מעמיקה</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 min-w-[280px]">🧮 Ollama</th>
                        <th className="text-right p-3 border-b font-medium text-green-700 min-w-[280px] bg-green-50">⚡ GPT</th>
                        <th className="text-right p-3 border-b font-medium text-gray-700 min-w-[200px]">פרטי קשר</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scanResults.map((result) => (
                        <tr key={result.id} className={`hover:bg-gray-50 border-b ${selectedResults.has(result.id) ? 'bg-purple-50' : ''}`}>
                          {/* Checkbox */}
                          <td className="p-3 text-center">
                            {result.has_content ? (
                              <input 
                                type="checkbox"
                                checked={selectedResults.has(result.id)}
                                onChange={() => toggleResultSelection(result.id)}
                                className={`w-4 h-4 rounded border-gray-300 ${result.business_type ? 'accent-orange-500' : ''}`}
                                title={result.business_type ? 'סמן לניתוח מחדש' : 'סמן לניתוח'}
                              />
                            ) : (
                              <span title="אין תוכן לניתוח" className="text-gray-300">⛔</span>
                            )}
                          </td>
                          {/* Thumbnail Preview */}
                          <td className="p-2">
                            <div className="w-12 h-12 bg-gray-100 rounded overflow-hidden flex items-center justify-center">
                              {result.status === 'analyzing' ? (
                                <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                              ) : result.status === 'matched' || result.status === 'discarded' ? (
                                <img 
                                  src={`https://www.google.com/s2/favicons?domain=${new URL(result.url).hostname}&sz=32`}
                                  alt=""
                                  className="w-8 h-8"
                                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                                />
                              ) : (
                                <div className="text-gray-300 text-xs">⏳</div>
                              )}
                            </div>
                          </td>
                          
                          {/* Site Info */}
                          <td className="p-3">
                            <a 
                              href={result.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline font-medium block truncate max-w-md"
                            >
                              {result.title || new URL(result.url).hostname}
                            </a>
                            <div className="text-xs text-gray-400 truncate max-w-md mt-1">
                              {result.url}
                            </div>
                          </td>
                          
                          {/* Status */}
                          <td className="p-3">
                            <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full font-medium ${
                              result.status === 'pending' ? 'bg-gray-100 text-gray-600' :
                              result.status === 'analyzing' ? 'bg-blue-100 text-blue-700' :
                              result.status === 'matched' ? 'bg-green-100 text-green-700' :
                              result.status === 'discarded' ? 'bg-red-100 text-red-700' :
                              result.status === 'error' ? 'bg-orange-100 text-orange-700' :
                              'bg-gray-100'
                            }`}>
                              {result.status === 'pending' && '⏳ ממתין'}
                              {result.status === 'analyzing' && <><Loader2 className="w-3 h-3 animate-spin" /> מנתח</>}
                              {result.status === 'matched' && '✅ נמצא'}
                              {result.status === 'discarded' && '❌ נדחה'}
                              {result.status === 'error' && '⚠️ שגיאה'}
                            </span>
                          </td>
                          
                          {/* Business Type (AI) */}
                          <td className="p-3">
                            {result.business_type ? (
                              <div className="flex flex-col gap-1">
                                <span className={`text-xs px-2 py-1 rounded-full font-medium inline-block w-fit ${
                                  result.business_type === 'lead_site' ? 'bg-emerald-100 text-emerald-700 ring-2 ring-emerald-300' :
                                  result.business_type === 'small_business' ? 'bg-green-100 text-green-700 ring-2 ring-green-300' :
                                  result.business_type === 'content_site' ? 'bg-teal-100 text-teal-700' :
                                  result.business_type === 'private' ? 'bg-green-100 text-green-700' :
                                  result.business_type === 'bank' ? 'bg-blue-100 text-blue-700' :
                                  result.business_type === 'insurance' ? 'bg-orange-100 text-orange-700' :
                                  result.business_type === 'corporation' ? 'bg-red-100 text-red-700' :
                                  result.business_type === 'fintech' ? 'bg-purple-100 text-purple-700' :
                                  'bg-gray-100 text-gray-600'
                                }`}>
                                  {result.business_type === 'lead_site' && '🎯 אתר לידים'}
                                  {result.business_type === 'small_business' && '💼 עסק קטן'}
                                  {result.business_type === 'content_site' && '📰 תוכן'}
                                  {result.business_type === 'private' && '🏪 פרטי'}
                                  {result.business_type === 'bank' && '🏦 בנק'}
                                  {result.business_type === 'insurance' && '🛡️ ביטוח'}
                                  {result.business_type === 'corporation' && '🏢 תאגיד'}
                                  {result.business_type === 'fintech' && '🚀 פינטק'}
                                  {result.business_type === 'unknown' && '❓ לא ידוע'}
                                  {result.business_type === 'error' && '⚠️ שגיאה'}
                                </span>
                                {result.business_type_reason && (
                                  <span className="text-xs text-gray-500 truncate max-w-[180px]" title={result.business_type_reason}>
                                    {result.business_type_reason.split('"reason"')[1]?.split('"')[1] || result.business_type_reason.slice(0, 50)}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-xs text-gray-400">לא נותח</span>
                            )}
                          </td>
                          
                          {/* WHOIS Info */}
                          <td className="p-3">
                            {result.whois_is_private ? (
                              <span className="text-xs text-gray-400">🔒 פרטי</span>
                            ) : result.owner_email || result.owner_name ? (
                              <div className="text-xs space-y-0.5">
                                {result.owner_name && (
                                  <div className="text-gray-700 truncate max-w-[150px]" title={result.owner_name}>
                                    👤 {result.owner_name}
                                  </div>
                                )}
                                {result.owner_org && (
                                  <div className="text-gray-500 truncate max-w-[150px]" title={result.owner_org}>
                                    🏢 {result.owner_org}
                                  </div>
                                )}
                                {result.owner_email && (
                                  <div className="text-blue-600 truncate max-w-[150px]" title={result.owner_email}>
                                    ✉️ {result.owner_email}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="text-xs text-gray-400">אין נתונים</span>
                            )}
                          </td>
                          
                          {/* Page Content Preview */}
                          <td className="p-3 text-center">
                            {result.html_text ? (
                              <button
                                onClick={() => setViewingContent({
                                  domain: new URL(result.url).hostname,
                                  content: result.html_text || ''
                                })}
                                className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-600 px-2 py-1 rounded transition-colors"
                                title={`${result.html_text.length} תווים`}
                              >
                                📄 צפה
                              </button>
                            ) : (
                              <span className="text-xs text-gray-300">—</span>
                            )}
                          </td>

                          {/* Deep Scan - Scanned Pages */}
                          <td className="p-3">
                            {result.deep_scan_status === 'completed' && result.scanned_pages && result.scanned_pages.length > 0 ? (
                              <div className="text-xs space-y-1">
                                <div className="flex items-center gap-1 mb-1">
                                  <span className="text-teal-600">🔬</span>
                                  <span className="font-medium text-gray-700">{result.scanned_pages.length} עמודים</span>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                  {result.scanned_pages.slice(0, 5).map((page, idx) => (
                                    <span 
                                      key={idx}
                                      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                        page.page_type === 'home' ? 'bg-blue-100 text-blue-700' :
                                        page.page_type === 'about' ? 'bg-purple-100 text-purple-700' :
                                        page.page_type === 'services' ? 'bg-green-100 text-green-700' :
                                        page.page_type === 'contact' ? 'bg-orange-100 text-orange-700' :
                                        page.page_type === 'pricing' ? 'bg-yellow-100 text-yellow-700' :
                                        'bg-gray-100 text-gray-600'
                                      }`}
                                      title={page.url}
                                    >
                                      {page.page_type === 'home' && '🏠'}
                                      {page.page_type === 'about' && 'ℹ️'}
                                      {page.page_type === 'services' && '⚙️'}
                                      {page.page_type === 'contact' && '📞'}
                                      {page.page_type === 'pricing' && '💰'}
                                      {page.page_type === 'blog' && '📝'}
                                      {!['home','about','services','contact','pricing','blog'].includes(page.page_type) && '📄'}
                                      {page.has_contact_form && ' 📋'}
                                    </span>
                                  ))}
                                  {result.scanned_pages.length > 5 && (
                                    <span className="text-[10px] text-gray-400">+{result.scanned_pages.length - 5}</span>
                                  )}
                                </div>
                              </div>
                            ) : result.deep_scan_status === 'running' ? (
                              <div className="flex items-center gap-1 text-xs text-teal-600">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                <span>סורק...</span>
                              </div>
                            ) : result.pages_scanned > 0 ? (
                              <span className="text-xs text-gray-500">📄 {result.pages_scanned} עמודים</span>
                            ) : (
                              <span className="text-xs text-gray-300">—</span>
                            )}
                          </td>

                          {/* Recommended Calculator */}
                          <td className="p-3 min-w-[280px]">
                            {result.all_recommended_calcs && result.all_recommended_calcs.length > 0 ? (
                              <div className="text-xs space-y-2">
                                {result.all_recommended_calcs.map((calc, idx) => (
                                  <div key={idx} className={`${idx > 0 ? 'pt-2 border-t border-gray-200' : ''}`}>
                                    <div className="flex items-center gap-2">
                                      <span className={idx === 0 ? 'text-green-600' : 'text-gray-400'}>{idx === 0 ? '🧮' : '📊'}</span>
                                      <span className={`font-medium ${idx === 0 ? 'text-gray-700' : 'text-gray-500'}`}>
                                        {calc.calc_name || `מחשבון #${calc.calc_id}`}
                                      </span>
                                      <span className={`px-1.5 py-0.5 rounded text-white text-[10px] ${
                                        calc.score >= 0.7 ? 'bg-green-500' :
                                        calc.score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                      }`}>
                                        {Math.round(calc.score * 100)}%
                                      </span>
                                    </div>
                                    {calc.reason && (
                                      <div className="text-gray-500 mt-1 pr-6 leading-relaxed">
                                        {calc.reason}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : result.recommended_calc_id ? (
                              <div className="text-xs space-y-1">
                                <div className="flex items-center gap-1">
                                  <span className="text-green-600">🧮</span>
                                  <span className="font-medium text-gray-700 truncate max-w-[120px]" title={result.recommended_calc_name || ''}>
                                    {result.recommended_calc_name || `מחשבון #${result.recommended_calc_id}`}
                                  </span>
                                </div>
                                {result.recommended_calc_score !== null && (
                                  <div className="flex items-center gap-1">
                                    <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full ${
                                          result.recommended_calc_score >= 0.7 ? 'bg-green-500' :
                                          result.recommended_calc_score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                        }`}
                                        style={{ width: `${result.recommended_calc_score * 100}%` }}
                                      />
                                    </div>
                                    <span className="text-gray-500">{Math.round(result.recommended_calc_score * 100)}%</span>
                                  </div>
                                )}
                              </div>
                            ) : result.deep_scan_status === 'completed' ? (
                              <span className="text-xs text-yellow-600">ממתין להתאמה</span>
                            ) : result.pages_scanned > 0 ? (
                              <span className="text-xs text-blue-600">📄 {result.pages_scanned} עמודים</span>
                            ) : (
                              <span className="text-xs text-gray-300">—</span>
                            )}
                          </td>

                          {/* GPT Recommended Calculator */}
                          <td className="p-3 min-w-[280px] bg-green-50/30">
                            {result.gpt_all_recommended_calcs && result.gpt_all_recommended_calcs.length > 0 ? (
                              <div className="text-xs space-y-2">
                                <div className="flex items-center gap-1 text-green-600 font-medium mb-1">
                                  ⚡ GPT
                                  {result.gpt_match_duration_seconds && (
                                    <span className="text-gray-400 font-normal">({result.gpt_match_duration_seconds.toFixed(1)}s)</span>
                                  )}
                                </div>
                                {result.gpt_all_recommended_calcs.map((calc, idx) => (
                                  <div key={idx} className={`${idx > 0 ? 'pt-2 border-t border-green-200' : ''}`}>
                                    <div className="flex items-center gap-2">
                                      <span className={idx === 0 ? 'text-green-600' : 'text-gray-400'}>{idx === 0 ? '🧮' : '📊'}</span>
                                      <span className={`font-medium ${idx === 0 ? 'text-gray-700' : 'text-gray-500'}`}>
                                        {calc.calc_name || `מחשבון #${calc.calc_id}`}
                                      </span>
                                      <span className={`px-1.5 py-0.5 rounded text-white text-[10px] ${
                                        calc.score >= 0.7 ? 'bg-green-500' :
                                        calc.score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                      }`}>
                                        {Math.round(calc.score * 100)}%
                                      </span>
                                    </div>
                                    {calc.reason && (
                                      <div className="text-gray-500 mt-1 pr-6 leading-relaxed">
                                        {calc.reason}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : result.gpt_recommended_calc_id ? (
                              <div className="text-xs space-y-1">
                                <div className="flex items-center gap-1 text-green-600 font-medium mb-1">
                                  ⚡ GPT
                                  {result.gpt_match_duration_seconds && (
                                    <span className="text-gray-400 font-normal">({result.gpt_match_duration_seconds.toFixed(1)}s)</span>
                                  )}
                                </div>
                                <div className="flex items-center gap-1">
                                  <span className="text-green-600">🧮</span>
                                  <span className="font-medium text-gray-700">
                                    {result.gpt_recommended_calc_name || `מחשבון #${result.gpt_recommended_calc_id}`}
                                  </span>
                                </div>
                                {result.gpt_recommended_calc_score !== null && (
                                  <div className="flex items-center gap-1">
                                    <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                      <div 
                                        className={`h-full rounded-full ${
                                          (result.gpt_recommended_calc_score || 0) >= 0.7 ? 'bg-green-500' :
                                          (result.gpt_recommended_calc_score || 0) >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                                        }`}
                                        style={{ width: `${(result.gpt_recommended_calc_score || 0) * 100}%` }}
                                      />
                                    </div>
                                    <span className="text-gray-500">{Math.round((result.gpt_recommended_calc_score || 0) * 100)}%</span>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span className="text-xs text-gray-300">—</span>
                            )}
                          </td>
                          
                          {/* Contact Info from Page */}
                          <td className="p-3">
                            {result.status === 'matched' && result.description && (
                              <div className="text-xs space-y-1">
                                {result.description.split('\n').map((line, i) => (
                                  <div key={i} className={line.startsWith('Emails') || line.startsWith('WHOIS') ? 'text-blue-600' : 'text-green-600'}>
                                    {line}
                                  </div>
                                ))}
                              </div>
                            )}
                            {result.status === 'discarded' && (
                              <span className="text-xs text-gray-400">אין פרטי קשר</span>
                            )}
                            {result.status === 'error' && result.error_message && (
                              <span className="text-xs text-orange-600">{result.error_message}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Content Viewer Modal */}
      {viewingContent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b flex justify-between items-center shrink-0 bg-gray-50">
              <div>
                <h2 className="text-lg font-bold">📄 תוכן העמוד</h2>
                <p className="text-sm text-gray-500">{viewingContent.domain} • {viewingContent.content.length.toLocaleString()} תווים</p>
              </div>
              <button 
                onClick={() => setViewingContent(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl px-2"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <div className="text-sm leading-relaxed text-gray-700 bg-gray-50 p-4 rounded-lg space-y-3">
                {viewingContent.content.split('\n').filter(line => line.trim()).map((line, i) => {
                  const trimmed = line.trim()
                  // Detect headers/titles (short lines, usually menu items or section titles)
                  const isShort = trimmed.length < 60
                  const hasNumbers = /\d{2,}/.test(trimmed) // Phone/numbers
                  const isEmail = /@/.test(trimmed)
                  const isUrl = /https?:\/\//.test(trimmed)
                  
                  if (isEmail) {
                    return <div key={i} className="text-blue-600">✉️ {trimmed}</div>
                  }
                  if (hasNumbers && trimmed.length < 100) {
                    return <div key={i} className="text-green-600">📞 {trimmed}</div>
                  }
                  if (isUrl) {
                    return <div key={i} className="text-purple-600 text-xs break-all">🔗 {trimmed}</div>
                  }
                  if (isShort && !hasNumbers) {
                    return <div key={i} className="font-semibold text-gray-800 mt-2">{trimmed}</div>
                  }
                  return <p key={i} className="text-gray-600">{trimmed}</p>
                })}
              </div>
            </div>
            <div className="p-3 border-t bg-gray-50 flex justify-between items-center">
              <span className="text-xs text-gray-500">
                💡 זה התוכן שנשלח ל-AI לניתוח סוג העסק
              </span>
              <button 
                onClick={() => {
                  navigator.clipboard.writeText(viewingContent.content)
                  alert('התוכן הועתק!')
                }}
                className="btn btn-secondary text-sm"
              >
                📋 העתק
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ScanModal({
  onClose,
  onCreated
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [form, setForm] = useState({
    name: '',
    keywords: '',
    results_per_keyword: 100,
    auto_start: true
  })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const response = await fetch('/api/scans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          keywords: form.keywords.split('\n').map(k => k.trim()).filter(Boolean),
          results_per_keyword: form.results_per_keyword,
          auto_start: form.auto_start
        })
      })

      if (response.ok) {
        onCreated()
        onClose()
      }
    } catch (error) {
      console.error('Failed to create scan:', error)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-lg p-6">
        <h2 className="text-xl font-bold mb-4">סריקה חדשה</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">שם הסריקה</label>
            <input
              type="text"
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="סריקת אתרי פיננסים"
              required
            />
          </div>

          <div>
            <label className="label">מילות חיפוש (שאילתה אחת בכל שורה)</label>
            <textarea
              className="input h-32"
              value={form.keywords}
              onChange={(e) => setForm({ ...form, keywords: e.target.value })}
              placeholder="מחשבון משכנתא&#10;חישוב הלוואה&#10;מחשבון ביטוח"
              required
            />
          </div>

          <div>
            <label className="label">תוצאות לכל שאילתה</label>
            <select
              className="input"
              value={form.results_per_keyword}
              onChange={(e) => setForm({ ...form, results_per_keyword: parseInt(e.target.value) })}
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={150}>150</option>
              <option value={200}>200</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto_start"
              checked={form.auto_start}
              onChange={(e) => setForm({ ...form, auto_start: e.target.checked })}
              className="w-4 h-4"
            />
            <label htmlFor="auto_start">התחל סריקה מיד</label>
          </div>

          <div className="flex gap-2 pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary flex-1">
              ביטול
            </button>
            <button type="submit" disabled={submitting} className="btn btn-primary flex-1">
              {submitting ? 'יוצר...' : 'צור סריקה'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
