// main.jsx — React Application Entry Point
// =========================================
// This is the very first file React executes.
// It mounts the <App /> component into the <div id="root"> in index.html.
// StrictMode helps find bugs by double-rendering in development.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'   // ← Tailwind styles loaded here
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
