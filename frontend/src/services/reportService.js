// services/reportService.js — Report API Calls
import api from './api'

export const reportService = {
  // Get final report for an interview
  get: (interviewId) => api.get(`/report/${interviewId}`),

  // Get dashboard stats
  getDashboardStats: () => api.get('/dashboard/stats'),

  // Download PDF (returns a blob)
  downloadPdf: (interviewId) =>
    api.get(`/report/${interviewId}/pdf`, { responseType: 'blob' }),
}
