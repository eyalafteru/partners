'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Redirect to unified leads page
 * הדף הזה מופנה אוטומטית לדף הלידים המאוחד
 */
export default function EmailsRedirect() {
  const router = useRouter()
  
  useEffect(() => {
    router.replace('/leads')
  }, [router])
  
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-gray-500">מעביר למרכז הלידים...</p>
      </div>
    </div>
  )
}
