import { createClient } from '@supabase/supabase-js'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL  || 'http://localhost',
  import.meta.env.VITE_SUPABASE_ANON_KEY || 'anon',
)

// ── Session helpers ───────────────────────────────────────────────────────────

export async function getSession() {
  if (import.meta.env.DEV) {
    try {
      const { data, error } = await supabase.auth.getSession()
      if (data?.session) return data.session
    } catch {}

    // ✅ ALWAYS fallback in dev
    return {
      access_token: 'mock-token',
      user: { email: 'dev@local', id: 'dev-id' }
    }
  }

  // production
  const { data, error } = await supabase.auth.getSession()
  if (error) throw new Error(error.message)
  return data.session
}

export async function getCurrentUser() {
  if (import.meta.env.DEV) {
    if (!import.meta.env.VITE_SUPABASE_URL || import.meta.env.VITE_SUPABASE_URL === 'http://localhost') {
      return { email: 'dev@local', id: 'dev-id', user_metadata: { name: 'Local Developer' } }
    }
  }
  try {
    const { data, error } = await supabase.auth.getUser()
    if (error) throw new Error(error.message)
    return data.user
  } catch (err) {
    if (import.meta.env.DEV) {
      return { email: 'dev@local', id: 'dev-id', user_metadata: { name: 'Local Developer' } }
    }
    throw err
  }
}

export async function getAccessToken() {
  const session = await getSession()
  if (!session) throw new Error('No active session')
  return session.access_token
}

export async function signupWithEmail(email, password, name) {
  const { data, error } = await supabase.auth.signUp({
    email, password,
    options: { data: { name } },
  })
  if (error) throw new Error(error.message)

  // Create profile in backend — FIX: this endpoint now exists
  if (data.user) {
    const session = await getSession()
    if (session) {
      try {
        await fetch(`${BASE_URL}/profiles`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, name }),
        })
      } catch (err) {
        console.warn('Profile creation failed:', err)
      }
    }
  }
  return data
}

export async function loginWithEmail(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw new Error(error.message)
  return data
}

export async function loginWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/callback` },
  })
  if (error) throw new Error(error.message)
  return data
}

export async function logout() {
  const { error } = await supabase.auth.signOut()
  if (error) throw new Error(error.message)
}

export async function loginAsDev() {
  if (!import.meta.env.DEV) throw new Error('Dev login only available in development')
  return {
    user: { email: 'dev@local', id: 'dev-id', user_metadata: { name: 'Local Developer' } },
  }
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = await getAccessToken()
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  })
  if (res.status === 204) return null
  if (!res.ok) {
    if (res.status === 401) throw new Error('Session expired. Please sign in again.')
    let detail = `Request failed (${res.status})`
    try { const err = await res.json(); detail = err.detail || detail } catch {}
    throw new Error(detail)
  }
  return res.json()
}

// ── Scan endpoints ────────────────────────────────────────────────────────────

export async function scanResumes({
  roleTitle, jobDescription, files, priorities,
  requiredSkills = [], preferredSkills = [],
  minYearsExperience = null, requiredDegree = null,
  experienceCapYears = 15,
}) {
  const token = await getAccessToken()
  const form = new FormData()
  form.append('job_description', jobDescription)
  if (roleTitle) form.append('role_title', roleTitle)
  form.append('required_skills',      JSON.stringify(requiredSkills))
  form.append('preferred_skills',     JSON.stringify(preferredSkills))
  form.append('min_years_experience', JSON.stringify(minYearsExperience))
  form.append('required_degree',      JSON.stringify(requiredDegree))
  form.append('experience_cap_years', String(experienceCapYears))
  form.append('skills_priority',      priorities.skills)
  form.append('experience_priority',  priorities.experience)
  form.append('education_priority',   priorities.education)
  form.append('relevance_priority',   priorities.relevance)
  files.forEach(f => form.append('files', f))

  const res = await fetch(`${BASE_URL}/scan/pdf`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: form,
  })
  if (!res.ok) {
    if (res.status === 401) throw new Error('Session expired. Please sign in again.')
    let detail = `Scan failed (${res.status})`
    try { const err = await res.json(); detail = err.detail || detail } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export function listScans()          { return apiFetch('/scans') }
export function getScanDetail(id)    { return apiFetch(`/scans/${id}`) }
export function deleteScan(id)       { return apiFetch(`/scans/${id}`, { method: 'DELETE' }) }
export function getUsage()           { return apiFetch('/usage') }

export async function getAdminAnalytics(secret) {
  const res = await fetch(`${BASE_URL}/admin/analytics`, {
    headers: { 'X-Admin-Secret': secret },
  })
  if (!res.ok) {
    let detail = `Admin analytics failed (${res.status})`
    try { const err = await res.json(); detail = err.detail || detail } catch {}
    throw new Error(detail)
  }
  return res.json()
}
