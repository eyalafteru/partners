'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Calculator, 
  Users, 
  Search, 
  MessageSquare,
  Settings,
  Bot,
  Database,
  Key,
  BarChart2,
  Mail,
  FileText,
  Zap,
  Bell,
  Facebook
} from 'lucide-react'

const navigation = [
  { name: 'דאשבורד', href: '/dashboard', icon: LayoutDashboard },
  { name: 'מחשבונים', href: '/calculators', icon: Calculator },
  { name: 'לידים ו-Outreach', href: '/leads', icon: Users },
  { name: 'סריקות', href: '/scans', icon: Search },
  { divider: true, name: 'תקשורת' },
  { name: 'Facebook Marketing', href: '/facebook-marketing', icon: Facebook },
  { name: 'תבניות מייל', href: '/emails/templates', icon: FileText },
  { divider: true, name: 'ניהול' },
  { name: 'פרומפטים', href: '/admin/prompts', icon: Bot },
  { name: 'תרחישי תשובות', href: '/admin/scenarios', icon: Zap },
  { name: 'מענה אוטומטי', href: '/settings/auto-reply', icon: Settings },
  { name: 'התראות WhatsApp', href: '/admin/notifications', icon: Bell },
  { name: 'API Keys', href: '/admin/api-keys', icon: Key },
  { name: 'Database', href: '/admin/database', icon: Database },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <Calculator className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg">PartnerCalc</h1>
            <p className="text-xs text-gray-400">מערכת שותפויות</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-auto">
        {navigation.map((item, index) => {
          if ('divider' in item && item.divider) {
            return (
              <div key={index} className="pt-4 pb-2">
                <p className="px-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {item.name}
                </p>
              </div>
            )
          }

          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href || '#'}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive 
                  ? 'bg-primary-600 text-white' 
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              {Icon && <Icon className="w-5 h-5" />}
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-3 text-sm text-gray-400">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span>Ollama: DictaLM מחובר</span>
        </div>
      </div>
    </div>
  )
}
