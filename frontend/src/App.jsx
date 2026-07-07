// App.jsx — Root Component with Routing
// =======================================
// React Router controls which page component renders based on the URL.
// Protected routes redirect to /login if the user is not authenticated.

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'

// Pages
import Login        from './pages/Login'
import Register     from './pages/Register'
import Dashboard    from './pages/Dashboard'
import ResumeUpload from './pages/ResumeUpload'
import Interview    from './pages/Interview'
import Report       from './pages/Report'

// ── Protected Route wrapper ───────────────────────────────────────────────────
// If the user is not logged in, redirect to /login.
// The `replace` prop replaces the current history entry instead of pushing,
// so the back button doesn't loop back to the protected page.
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-gray-400 text-sm">Loading...</div>
    </div>
  )

  return isAuthenticated ? children : <Navigate to="/login" replace />
}

// ── App with Router ───────────────────────────────────────────────────────────
function AppRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <>
      {/* react-hot-toast notification container */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: { fontFamily: 'IBM Plex Sans, sans-serif', fontSize: '14px' },
          success: { iconTheme: { primary: '#0f62fe', secondary: '#fff' } },
        }}
      />

      <Routes>
        {/* Public routes */}
        <Route path="/login"    element={isAuthenticated ? <Navigate to="/dashboard" /> : <Login />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register />} />

        {/* Protected routes — require authentication */}
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/upload"    element={<ProtectedRoute><ResumeUpload /></ProtectedRoute>} />
        <Route path="/interview/:id" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
        <Route path="/report/:id"    element={<ProtectedRoute><Report /></ProtectedRoute>} />

        {/* Default redirect */}
        <Route path="/"  element={<Navigate to="/dashboard" replace />} />
        <Route path="*"  element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      {/* AuthProvider wraps everything so all pages can access auth state */}
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
