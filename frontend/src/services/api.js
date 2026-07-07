// services/api.js — Axios Instance with Auth Interceptor
// ========================================================
// Creates a configured Axios instance that:
//   1. Points to our FastAPI backend via the Vite proxy
//   2. Automatically attaches the JWT token to every request
//   3. Redirects to /login on 401 Unauthorized responses

import axios from 'axios'

// Base URL uses Vite proxy: /api → http://localhost:8000
// In production, set VITE_API_URL in frontend/.env
const BASE_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,   // 30 second timeout for Granite API calls
})

// ── Request Interceptor ───────────────────────────────────────────────────────
// Runs before every request. Reads the JWT from localStorage and adds it
// to the Authorization header: "Bearer eyJhbGci..."
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response Interceptor ──────────────────────────────────────────────────────
// Runs after every response. On 401 (token expired/invalid),
// clear storage and redirect to login page.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
