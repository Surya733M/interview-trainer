// context/AuthContext.jsx — Global Authentication State
// ======================================================
// React Context lets any component anywhere in the app access the
// current user and auth functions without "prop drilling".
//
// How it works:
//   1. AuthProvider wraps the entire app
//   2. On load, it checks localStorage for a saved token
//   3. Any component can call useAuth() to get user, login, logout

import { createContext, useContext, useState, useEffect } from 'react'
import { authService } from '../services/authService'

// Create the context object — the "channel" all components share
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)   // true while checking localStorage

  // On app load: restore session from localStorage
  useEffect(() => {
    const savedUser  = localStorage.getItem('user')
    const savedToken = localStorage.getItem('access_token')
    if (savedUser && savedToken) {
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  // Called after successful login or register
  const login = (userData, token) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  // Called on logout — wipe everything from memory and storage
  const logout = async () => {
    try { await authService.logout() } catch (_) {}
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
  }

  const value = { user, login, logout, loading, isAuthenticated: !!user }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// Custom hook — any component imports this instead of useContext directly
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
