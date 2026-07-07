// pages/ResumeUpload.jsx — Resume Upload Page
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { resumeService } from '../services/resumeService'
import { interviewService } from '../services/interviewService'
import toast from 'react-hot-toast'

export default function ResumeUpload() {
  const navigate = useNavigate()
  const [file, setFile]         = useState(null)
  const [jobTitle, setJobTitle] = useState('')
  const [expLevel, setExpLevel] = useState('fresher')
  const [analysis, setAnalysis] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [starting, setStarting]   = useState(false)

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f && !f.name.endsWith('.pdf')) {
      toast.error('Only PDF files are accepted')
      return
    }
    setFile(f)
    setAnalysis(null)
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) { toast.error('Please select a PDF file'); return }
    if (!jobTitle.trim()) { toast.error('Please enter a job title'); return }

    setUploading(true)
    try {
      const { data } = await resumeService.upload(file, jobTitle)
      setAnalysis(data)
      toast.success('Resume analysed successfully!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleStartInterview = async () => {
    if (!analysis) return
    setStarting(true)
    try {
      const { data } = await interviewService.start({
        resume_id: analysis.resume_id,
        job_title: jobTitle,
        experience_level: expLevel,
        num_technical: 5,
        num_behavioral: 3,
        num_hr: 2,
      })
      toast.success('Interview started!')
      navigate(`/interview/${data.interview_id}`, { state: { interviewData: data } })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not start interview')
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
        <Link to="/dashboard" className="flex items-center gap-2 text-ibm-blue hover:underline text-sm font-medium">
          &larr; Dashboard
        </Link>
        <span className="font-semibold text-gray-900">Resume Upload</span>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Upload Form */}
        <div className="card mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-1">Upload Your Resume</h2>
          <p className="text-sm text-gray-500 mb-6">PDF only · Max 10 MB · AI will extract your skills automatically</p>

          <form onSubmit={handleUpload} className="space-y-4">
            {/* File Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition
                ${file ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-ibm-blue'}`}
              onClick={() => document.getElementById('resume-input').click()}
            >
              <input
                id="resume-input" type="file" accept=".pdf"
                className="hidden" onChange={handleFileChange}
              />
              {file ? (
                <div>
                  <p className="text-green-700 font-medium">{file.name}</p>
                  <p className="text-sm text-green-600 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              ) : (
                <div>
                  <p className="text-4xl mb-2">📄</p>
                  <p className="text-gray-600 font-medium">Click to select your PDF resume</p>
                  <p className="text-sm text-gray-400 mt-1">or drag and drop here</p>
                </div>
              )}
            </div>

            {/* Job Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Job Title</label>
              <input
                type="text" required
                placeholder="e.g. Full Stack Developer, Data Scientist"
                className="input-field"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
              />
            </div>

            {/* Experience Level */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Experience Level</label>
              <select
                className="input-field bg-white"
                value={expLevel}
                onChange={(e) => setExpLevel(e.target.value)}
              >
                <option value="fresher">Fresher (0-1 years)</option>
                <option value="junior">Junior (1-3 years)</option>
                <option value="mid">Mid-Level (3-5 years)</option>
                <option value="senior">Senior (5-8 years)</option>
                <option value="expert">Expert (8+ years)</option>
              </select>
            </div>

            <button type="submit" disabled={uploading} className="btn-primary w-full">
              {uploading ? 'Analysing Resume...' : 'Upload & Analyse'}
            </button>
          </form>
        </div>

        {/* Analysis Results */}
        {analysis && (
          <div className="card">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Resume Analysis</h3>

            {/* Skills */}
            <div className="mb-4">
              <p className="text-sm font-semibold text-gray-700 mb-2">Detected Skills</p>
              <div className="flex flex-wrap gap-2">
                {analysis.skills.map((s) => (
                  <span key={s} className="px-3 py-1 bg-blue-100 text-ibm-blue text-sm rounded-full font-medium">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Missing Skills */}
            {analysis.missing_skills?.length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Skills to Improve</p>
                <div className="flex flex-wrap gap-2">
                  {analysis.missing_skills.map((s) => (
                    <span key={s} className="px-3 py-1 bg-red-100 text-red-600 text-sm rounded-full font-medium">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Summary Row */}
            <div className="flex gap-4 text-sm mb-6">
              <div className="bg-gray-50 rounded-lg px-4 py-3">
                <p className="text-gray-500">Level</p>
                <p className="font-semibold capitalize">{analysis.experience_level}</p>
              </div>
              {analysis.suggested_role && (
                <div className="bg-gray-50 rounded-lg px-4 py-3">
                  <p className="text-gray-500">Suggested Role</p>
                  <p className="font-semibold">{analysis.suggested_role}</p>
                </div>
              )}
            </div>

            {/* Start Interview CTA */}
            <button
              onClick={handleStartInterview}
              disabled={starting}
              className="btn-primary w-full text-base py-3"
            >
              {starting ? 'Preparing Interview...' : 'Start Mock Interview'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
