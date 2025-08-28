'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { useQuery } from 'react-query'
import toast from 'react-hot-toast'

// Types
interface Dependency {
  name: string
  tier: 'tier1' | 'tier2' | 'tier3' | 'tier4'
  version: string
  latestVersion: string
  status: 'healthy' | 'warning' | 'critical' | 'updating'
  lastUpdated: string
  vulnerabilities: number
  customizations: string[]
  repository: string
  fork: string
}

interface DashboardStats {
  totalDependencies: number
  healthyCount: number
  warningCount: number
  criticalCount: number
  updatingCount: number
  totalVulnerabilities: number
}

// API Functions
const fetchDependencies = async (): Promise<Dependency[]> => {
  const response = await fetch('/api/v1/dependencies')
  if (!response.ok) throw new Error('Failed to fetch dependencies')
  return response.json()
}

const fetchDashboardStats = async (): Promise<DashboardStats> => {
  const response = await fetch('/api/v1/dashboard/stats')
  if (!response.ok) throw new Error('Failed to fetch stats')
  return response.json()
}

// Components
const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  const iconProps = { className: "h-5 w-5" }
  
  switch (status) {
    case 'healthy':
      return <CheckCircleIcon {...iconProps} className="h-5 w-5 text-green-500" />
    case 'warning':
      return <ExclamationTriangleIcon {...iconProps} className="h-5 w-5 text-yellow-500" />
    case 'critical':
      return <XCircleIcon {...iconProps} className="h-5 w-5 text-red-500" />
    case 'updating':
      return <ArrowPathIcon {...iconProps} className="h-5 w-5 text-blue-500 animate-spin" />
    default:
      return <ClockIcon {...iconProps} className="h-5 w-5 text-gray-500" />
  }
}

const TierBadge: React.FC<{ tier: string }> = ({ tier }) => {
  const colors = {
    tier1: 'bg-red-100 text-red-800 border-red-200',
    tier2: 'bg-orange-100 text-orange-800 border-orange-200',
    tier3: 'bg-blue-100 text-blue-800 border-blue-200',
    tier4: 'bg-gray-100 text-gray-800 border-gray-200'
  }
  
  const labels = {
    tier1: 'Critical',
    tier2: 'Important', 
    tier3: 'Supporting',
    tier4: 'Infrastructure'
  }
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[tier as keyof typeof colors]}`}>
      {labels[tier as keyof typeof labels]}
    </span>
  )
}

const StatCard: React.FC<{ 
  title: string
  value: number
  icon: React.ReactNode
  color: string
  trend?: number
}> = ({ title, value, icon, color, trend }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-white overflow-hidden shadow-lg rounded-lg"
  >
    <div className="p-5">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <div className={`p-3 rounded-md ${color}`}>
            {icon}
          </div>
        </div>
        <div className="ml-5 w-0 flex-1">
          <dl>
            <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
            <dd className="flex items-baseline">
              <div className="text-2xl font-semibold text-gray-900">{value}</div>
              {trend !== undefined && (
                <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                  trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'
                }`}>
                  {trend > 0 ? '+' : ''}{trend}%
                </div>
              )}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </motion.div>
)

const DependencyTable: React.FC<{ 
  dependencies: Dependency[]
  onRefresh: (name: string) => void
}> = ({ dependencies, onRefresh }) => {
  const [filter, setFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('name')
  
  const filteredDeps = dependencies.filter(dep => 
    filter === 'all' || dep.tier === filter || dep.status === filter
  )
  
  return (
    <div className="bg-white shadow-lg rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Dependencies</h3>
          <div className="flex space-x-2">
            <select 
              value={filter} 
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-md border-gray-300 text-sm"
            >
              <option value="all">All Dependencies</option>
              <option value="tier1">Tier 1 - Critical</option>
              <option value="tier2">Tier 2 - Important</option>
              <option value="tier3">Tier 3 - Supporting</option>
              <option value="tier4">Tier 4 - Infrastructure</option>
              <option value="critical">Critical Status</option>
              <option value="warning">Warning Status</option>
              <option value="healthy">Healthy Status</option>
            </select>
          </div>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tier
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Version
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Vulnerabilities
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Updated
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredDeps.map((dep, index) => (
              <motion.tr
                key={dep.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="hover:bg-gray-50"
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-8 w-8">
                      <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center">
                        <span className="text-xs font-medium text-gray-600">
                          {dep.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">{dep.name}</div>
                      <div className="text-sm text-gray-500">{dep.repository}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <TierBadge tier={dep.tier} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <StatusIcon status={dep.status} />
                    <span className="ml-2 text-sm text-gray-900 capitalize">{dep.status}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{dep.version}</div>
                  {dep.version !== dep.latestVersion && (
                    <div className="text-xs text-blue-600">→ {dep.latestVersion}</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {dep.vulnerabilities > 0 ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      {dep.vulnerabilities} CVE{dep.vulnerabilities > 1 ? 's' : ''}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Clean
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(dep.lastUpdated).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => onRefresh(dep.name)}
                    className="text-blue-600 hover:text-blue-900 mr-3"
                  >
                    Refresh
                  </button>
                  <a
                    href={dep.fork}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-600 hover:text-gray-900"
                  >
                    View Fork
                  </a>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Main Dashboard Component
export default function DashboardPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  
  const { data: dependencies = [], isLoading: depsLoading, error: depsError } = useQuery(
    ['dependencies', refreshTrigger],
    fetchDependencies,
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      onError: (error) => {
        toast.error('Failed to fetch dependencies')
        console.error('Dependencies fetch error:', error)
      }
    }
  )
  
  const { data: stats, isLoading: statsLoading } = useQuery(
    ['dashboard-stats', refreshTrigger],
    fetchDashboardStats,
    {
      refetchInterval: 30000,
      onError: (error) => {
        toast.error('Failed to fetch dashboard stats')
        console.error('Stats fetch error:', error)
      }
    }
  )
  
  const handleRefreshDependency = async (name: string) => {
    try {
      toast.loading(`Refreshing ${name}...`, { id: name })
      
      const response = await fetch(`/api/v1/dependencies/${name}/refresh`, {
        method: 'POST'
      })
      
      if (!response.ok) throw new Error('Refresh failed')
      
      toast.success(`${name} refreshed successfully`, { id: name })
      setRefreshTrigger(prev => prev + 1)
    } catch (error) {
      toast.error(`Failed to refresh ${name}`, { id: name })
      console.error('Refresh error:', error)
    }
  }
  
  if (depsLoading || statsLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <ArrowPathIcon className="mx-auto h-12 w-12 text-gray-400 animate-spin" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Loading Dashboard...</h3>
        </div>
      </div>
    )
  }
  
  if (depsError) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <XCircleIcon className="mx-auto h-12 w-12 text-red-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Dashboard Error</h3>
          <p className="mt-1 text-sm text-gray-500">Failed to load dependency data</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dependency Health Dashboard</h1>
              <p className="mt-1 text-sm text-gray-500">
                Real-time monitoring of {dependencies.length} dependencies across 4 tiers
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                Last updated: {new Date().toLocaleTimeString()}
              </span>
              <button
                onClick={() => setRefreshTrigger(prev => prev + 1)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <ArrowPathIcon className="h-4 w-4 mr-2" />
                Refresh All
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <StatCard
            title="Total Dependencies"
            value={stats?.totalDependencies || 0}
            icon={<ClockIcon className="h-6 w-6 text-white" />}
            color="bg-blue-500"
          />
          <StatCard
            title="Healthy"
            value={stats?.healthyCount || 0}
            icon={<CheckCircleIcon className="h-6 w-6 text-white" />}
            color="bg-green-500"
          />
          <StatCard
            title="Warnings"
            value={stats?.warningCount || 0}
            icon={<ExclamationTriangleIcon className="h-6 w-6 text-white" />}
            color="bg-yellow-500"
          />
          <StatCard
            title="Critical"
            value={stats?.criticalCount || 0}
            icon={<XCircleIcon className="h-6 w-6 text-white" />}
            color="bg-red-500"
          />
          <StatCard
            title="Vulnerabilities"
            value={stats?.totalVulnerabilities || 0}
            icon={<ExclamationTriangleIcon className="h-6 w-6 text-white" />}
            color="bg-purple-500"
          />
        </div>
        
        {/* Dependencies Table */}
        <DependencyTable 
          dependencies={dependencies} 
          onRefresh={handleRefreshDependency}
        />
      </div>
    </div>
  )
}