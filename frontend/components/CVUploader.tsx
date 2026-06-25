import React, { useRef, useState } from 'react'
import { ResumeSummary } from '../types'

interface CVUploaderProps {
  onUpload: (file: File, preferences: string) => Promise<void>
  currentResume?: ResumeSummary
}

export default function CVUploader({ onUpload, currentResume }: CVUploaderProps) {
  const [file, setFile] = useState<File | null>(null)
  const [preferences, setPreferences] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateAndSetFile = (selectedFile: File) => {
    setError(null)
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (validTypes.includes(selectedFile.type)) {
      setFile(selectedFile)
      return
    }
    setError('Only PDF or DOCX files are supported.')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Please choose a resume file to continue.')
      return
    }

    setIsUploading(true)
    setError(null)
    try {
      await onUpload(file, preferences)
    } catch (err: any) {
      setError(err.message || 'Failed to upload your resume')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="glass-card animate-fade-in-up delay-100" style={{ padding: '28px' }}>
      <div style={{ marginBottom: '16px' }}>
        <p className="eyebrow">Step 2</p>
        <h3 style={{ marginBottom: '6px' }}>{currentResume ? 'Replace your resume (optional)' : 'Upload your resume'}</h3>
        <p style={{ color: 'var(--text-secondary)' }}>
          {currentResume
            ? 'Upload a new resume when your experience changes. We will refresh your job recommendations automatically.'
            : 'We extract your skills and experience, then match you with relevant open roles.'}
        </p>
      </div>

      {currentResume && !file && (
        <div className="glass-surface" style={{ padding: '12px 14px', marginBottom: '16px' }}>
          <p style={{ fontWeight: 700 }}>Current resume: {currentResume.original_filename}</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.86rem' }}>
            Version {currentResume.version} • Updated {new Date(currentResume.uploaded_at).toLocaleString()}
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '18px' }}>
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={(e) => {
            e.preventDefault()
            setIsDragging(false)
          }}
          onDrop={(e) => {
            e.preventDefault()
            setIsDragging(false)
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
              validateAndSetFile(e.dataTransfer.files[0])
            }
          }}
          style={{
            border: `2px dashed ${isDragging ? 'var(--clover-500)' : 'var(--border-accent)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: '32px 20px',
            cursor: 'pointer',
            background: isDragging ? 'var(--bg-glass)' : 'var(--bg-secondary)',
            transition: 'all var(--duration-fast)',
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                validateAndSetFile(e.target.files[0])
              }
            }}
            accept=".pdf,.docx"
            style={{ display: 'none' }}
          />

          {!file ? (
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontWeight: 700, marginBottom: '6px' }}>Drop your resume here or click to browse</p>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>PDF or DOCX, up to 5MB</p>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '14px', flexWrap: 'wrap' }}>
              <div>
                <p style={{ fontWeight: 700 }}>{file.name}</p>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button className="btn btn-secondary btn-sm" type="button" onClick={() => fileInputRef.current?.click()}>
                Choose another file
              </button>
            </div>
          )}
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600, fontSize: '0.92rem' }}>
            Extra context (optional)
          </label>
          <textarea
            className="input"
            placeholder="Example: Looking for backend or ML roles in Dublin, open to remote teams in EU time zones."
            value={preferences}
            onChange={(e) => setPreferences(e.target.value)}
          />
        </div>

        {error && <p style={{ color: '#b42318', fontSize: '0.9rem' }}>{error}</p>}

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={isUploading || !file}
          style={{ width: '100%' }}
        >
          {isUploading ? (
            <>
              <span className="spinner" style={{ width: '18px', height: '18px', borderWidth: '2px' }} />
              Saving your resume and refreshing matches...
            </>
          ) : (
            currentResume ? 'Update Resume and Refresh Matches' : 'Analyze Resume and Find Matching Jobs'
          )}
        </button>
      </form>
    </div>
  )
}
