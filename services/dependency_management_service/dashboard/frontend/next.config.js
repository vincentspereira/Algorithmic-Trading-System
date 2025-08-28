/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    appDir: true
  },
  env: {
    DASHBOARD_API_URL: process.env.DASHBOARD_API_URL || 'http://localhost:8080/api',
    GRAFANA_URL: process.env.GRAFANA_URL || 'http://localhost:3000',
    PROMETHEUS_URL: process.env.PROMETHEUS_URL || 'http://localhost:9090'
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.DASHBOARD_API_URL || 'http://localhost:8080/api'}/:path*`
      }
    ]
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          {
            key: 'Access-Control-Allow-Origin',
            value: '*'
          },
          {
            key: 'Access-Control-Allow-Methods',
            value: 'GET, POST, PUT, DELETE, OPTIONS'
          },
          {
            key: 'Access-Control-Allow-Headers',
            value: 'Content-Type, Authorization'
          }
        ]
      }
    ]
  }
}

module.exports = nextConfig