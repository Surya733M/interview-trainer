// pages/Interview.jsx — Mock Interview Page
import { useState, useLocation, useParams, useEffect } from 'react'
import { useNavigate, useLocation as useRouterLocation } from 'react-router-dom'
import { interviewService } from '../services/interviewService'
import toast from 'react-hot-toast'

export default function Interview() {
  const { id } = useParams()
  const location = useRouterLocation()
  const navigate = useNavigate()

  // Interview data passed from ResumeUpload via navigate state
  const initialData = location.state?.interviewData

  const [currentQuestion, setCurrentQuestion] = useState(
    initialData?.first_question || null
  )
  const [questionIndex, setQuestionIndex] = useState(0)
  const [totalQuestions, setTotalQuestions] = useState(
    initialData?.total_questions || 0
  )
  const [answer, setAnswer]       = useState('')
  const [feedback, setFeedback]   = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [isComplete, setIsComplete] = useState(false)

  // Fetch interview if not loaded from state
  useEffect(() => {
    if (!initialData && id) {
      interviewService.get(id).then(({ data }) => {
        setTotalQuestions(data.total_questions)
        setQuestionIndex(data.current_question)
      })
    }
  }, [id])

  const handleSubmitAnswer = async () => {
    if (!answer.trim()) { toast.error('Please write an answer before submitting'); return }
    setSubmitting(true)
    try {
      const { data } = await interviewService.answer({
        interview_id: parseInt(id),
        question_index: questionIndex,
        answer_text: answer,
      })
      setFeedback(data)
      setAnswer('')
      if (data.is_complete) {
        setIsComplete(true)
        toast.success('Interview complete! Generating your report...')
      } else {
        setCurrentQuestion(data.next_question)
        setQuestionIndex(questionIndex + 1)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit answer')
    } finally {
      setSubmitting(false)
    }
  }

  const handleNextQuestion = () => {
    setFeedback(null)
    if (isComplete) navigate(`/report/${id}`)
  }

  const difficultyColor = (d) => ({
    easy: 'bg-green-100 text-green-700',
    medium: 'bg-yellow-100 text-yellow-700',
    hard: 'bg-red-100 text-red-700',
  }[d] || 'bg-gray-100 text-gray-700')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with progress */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex justify-between items-center mb-2">
            <span className="font-semibold text-gray-900">Mock Interview</span>
            <span className="text-sm text-gray-500">
              Question {questionIndex + 1} of {totalQuestions}
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-ibm-blue h-2 rounded-full transition-all duration-500"
              style={{ width: `${((questionIndex) / totalQuestions) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* Question Card */}
        {currentQuestion && !isComplete && (
          <div className="card">
            <div className="flex gap-2 mb-4">
              <span className="px-2 py-1 bg-blue-100 text-ibm-blue text-xs rounded font-medium uppercase">
                {currentQuestion.type}
              </span>
              <span className={`px-2 py-1 text-xs rounded font-medium capitalize ${difficultyColor(currentQuestion.difficulty)}`}>
                {currentQuestion.difficulty}
              </span>
              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded font-medium">
                {currentQuestion.topic}
              </span>
            </div>
            <p className="text-lg font-medium text-gray-900 leading-relaxed">
              {currentQuestion.question}
            </p>
            {currentQuestion.hint && (
              <p className="text-sm text-gray-400 mt-3 italic">
                Hint: {currentQuestion.hint}
              </p>
            )}
          </div>
        )}

        {/* Answer Input */}
        {!feedback && !isComplete && (
          <div className="card">
            <label className="block text-sm font-medium text-gray-700 mb-2">Your Answer</label>
            <textarea
              rows={6}
              placeholder="Type your answer here. For behavioral questions, use the STAR method: Situation, Task, Action, Result..."
              className="input-field resize-none"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
            <div className="flex justify-between items-center mt-4">
              <span className="text-xs text-gray-400">{answer.split(' ').filter(Boolean).length} words</span>
              <button
                onClick={handleSubmitAnswer}
                disabled={submitting}
                className="btn-primary"
              >
                {submitting ? 'Evaluating...' : 'Submit Answer'}
              </button>
            </div>
          </div>
        )}

        {/* Feedback Card */}
        {feedback && (
          <div className="card border-l-4 border-ibm-blue">
            <h3 className="font-bold text-gray-900 mb-4">AI Feedback</h3>

            {/* Scores */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              {Object.entries(feedback.scores).map(([key, val]) => (
                <div key={key} className="text-center bg-gray-50 rounded-lg p-3">
                  <div className={`text-xl font-bold ${val >= 7 ? 'text-green-600' : val >= 5 ? 'text-yellow-600' : 'text-red-500'}`}>
                    {val}/10
                  </div>
                  <div className="text-xs text-gray-500 mt-1 capitalize">{key.replace('_', ' ')}</div>
                </div>
              ))}
            </div>

            {/* Overall */}
            <div className="text-center bg-ibm-blue rounded-lg p-4 text-white mb-4">
              <div className="text-3xl font-bold">{feedback.overall_score}/10</div>
              <div className="text-sm opacity-80">Overall Score</div>
            </div>

            {/* Strengths & Improvements */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm font-semibold text-green-700 mb-2">Strengths</p>
                {feedback.strengths.map((s, i) => (
                  <p key={i} className="text-sm text-gray-700 flex gap-1">
                    <span className="text-green-500">+</span> {s}
                  </p>
                ))}
              </div>
              <div>
                <p className="text-sm font-semibold text-orange-700 mb-2">Improvements</p>
                {feedback.improvements.map((s, i) => (
                  <p key={i} className="text-sm text-gray-700 flex gap-1">
                    <span className="text-orange-400">!</span> {s}
                  </p>
                ))}
              </div>
            </div>

            {/* Model Answer */}
            <div className="bg-blue-50 rounded-lg p-4 mb-4">
              <p className="text-xs font-semibold text-ibm-blue mb-1">Model Answer</p>
              <p className="text-sm text-gray-700">{feedback.model_answer}</p>
            </div>

            <button onClick={handleNextQuestion} className="btn-primary w-full">
              {isComplete ? 'View Final Report' : 'Next Question'}
            </button>
          </div>
        )}

        {/* Complete State */}
        {isComplete && !feedback && (
          <div className="card text-center py-12">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Interview Complete!</h2>
            <p className="text-gray-500 mb-6">Your report is ready. See how you performed.</p>
            <button onClick={() => navigate(`/report/${id}`)} className="btn-primary px-8 py-3 text-base">
              View My Report
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
