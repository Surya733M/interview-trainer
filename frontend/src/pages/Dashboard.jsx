// pages/Dashboard.jsx — Main Dashboard
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { reportService } from '../services/reportService'
import toast from 'react-hot-toast'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    reportService.getDashboardStats()
      .then(({ data }) => setStats(data))
      .catch(() => toast.error('Could not load stats'))
      .finally(() => setLoading(false))
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  // Score colour helper
  const scoreColor = (score) => {
    if (score >= 80) return 'text-green-600 bg-green-50'
    if (score >= 60) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-ibm-blue rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">IT</span>
          </div>
          <span className="font-semibold text-gray-900">Interview Trainer</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            {user?.full_name || user?.email}
          </span>
          <button onClick={handleLogout} className="text-sm text-red-600 hover:text-red-700 font-medium">
            Logout
          </button>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user?.full_name?.split(' ')[0] || 'there'}!
          </h1>
          <p className="text-gray-500 mt-1">Ready to ace your next interview?</p>
        </div>

        {/* Stats Cards */}
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card animate-pulse h-24 bg-gray-100" />
            ))}
          </div>
        ) : stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="card text-center">
              <div className="text-3xl font-bold text-ibm-blue">{stats.total_interviews}</div>
              <div className="text-sm text-gray-500 mt-1">Total Interviews</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-green-600">{stats.completed_interviews}</div>
              <div className="text-sm text-gray-500 mt-1">Completed</div>
            </div>
            <div className="card text-center">
              <div className={`text-3xl font-bold ${stats.average_score >= 60 ? 'text-green-600' : 'text-red-500'}`}>
                {stats.average_score}%
              </div>
              <div className="text-sm text-gray-500 mt-1">Avg Score</div>
            </div>
            <div className="card text-center">
              <div className="text-3xl font-bold text-purple-600">{stats.readiness_percentage}%</div>
              <div className="text-sm text-gray-500 mt-1">Readiness</div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <Link to="/upload" className="card hover:border-ibm-blue hover:shadow-md transition-all cursor-pointer block">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-ibm-blue text-xl">
                📄
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Upload Resume</h3>
                <p className="text-sm text-gray-500 mt-1">Upload your PDF and get AI-powered analysis</p>
              </div>
            </div>
          </Link>
          <div className="card opacity-60 cursor-not-allowed">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center text-purple-600 text-xl">
                🎯
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Start Interview</h3>
                <p className="text-sm text-gray-500 mt-1">Upload a resume first to start a mock interview</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Interviews */}
        {stats?.recent_interviews?.length > 0 && (
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Interviews</h2>
            <div className="space-y-3">
              {stats.recent_interviews.map((iv) => (
                <div key={iv.id} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="font-medium text-gray-900">{iv.job_title}</p>
                    <p className="text-sm text-gray-500">
                      {new Date(iv.created_at).toLocaleDateString()} · {iv.status}
                    </p>
                  </div>
                  {iv.score != null && (
                    <span className={`score-badge text-sm ${scoreColor(iv.score)}`}>
                      {iv.score}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
