/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Enable standalone output for Docker production
  output: 'standalone',
  
  // API Proxy to Backend
  // In Docker: backend container name
  // In dev: localhost:8000
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/static/:path*',
        destination: `${backendUrl}/static/:path*`,
      },
    ]
  },
  
  // RTL support
  i18n: {
    locales: ['he'],
    defaultLocale: 'he',
  },
}

module.exports = nextConfig
