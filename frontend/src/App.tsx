import { useEffect, useState } from 'react'

type UserSession = {
  id: string
  full_name: string
  email: string
  role: string
  is_active: boolean
}

type AuthMode = 'login' | 'register'

function getAuthSubmitLabel(isSubmitting: boolean, authMode: AuthMode): string {
  if (isSubmitting) return authMode === 'login' ? 'Signing in...' : 'Creating account...'
  return authMode === 'login' ? 'Sign in' : 'Create account'
}

function getLearningPathButtonLabel(isGenerating: boolean, hasLearningPath: boolean): string {
  if (isGenerating) return 'Generating...'
  return hasLearningPath ? 'Regenerate' : 'Generate roadmap'
}

type FormState = {
  full_name: string
  email: string
  password: string
}

type LearnerSkill = {
  skill_name: string
  self_rating: number
  target_rating: number
  gap_score: number
}

type LearnerProfile = {
  target_role: string
  preferred_location: string | null
  skills: LearnerSkill[]
}

type LearningPathItem = {
  id: string
  title: string
  module_type: string
  estimated_hours: number | null
  order_index: number
  resource_url: string | null
  resource_label: string | null
  status: 'not_started' | 'in_progress' | 'completed'
}

type LearningPath = {
  id: string
  title: string
  status: string
  priority_score: number | null
  items: LearningPathItem[]
}

type OpportunityMatch = {
  id: string
  company_name: string
  title: string
  location: string | null
  employment_type: string | null
  match_score: number
}

type Application = {
  id: string
  opportunity_id: string
  company_name: string
  opportunity_title: string
  learner_name: string
  learner_email: string
  status: string
  applied_at: string
  placement_date: string | null
}

type InstitutionAnalytics = {
  institution_name: string
  learner_count: number
  assessed_learner_count: number
  application_count: number
  applicants_count: number
  placement_count: number
  active_opportunity_count: number
  application_rate_percent: number
  placement_rate_percent: number
}

type InstitutionOption = {
  id: string
  name: string
}

type InstitutionLearner = {
  id: string
  full_name: string
  email: string
}

type InstitutionCohort = {
  id: string
  name: string
  program: string
  capacity: number
  status: string
  learner_count: number
  assessed_learner_count: number
  application_count: number
  placement_count: number
  learners: { user_id: string; full_name: string; email: string; status: string }[]
}

type InstitutionCohortForm = {
  name: string
  program: string
  capacity: number
}

type AdminProvisionForm = {
  full_name: string
  email: string
  password: string
  role: 'learner' | 'employer' | 'institution'
  institution_id: string
}

type NewInstitutionForm = {
  name: string
  sector: string
  location: string
}

type EmployerOpportunity = {
  id: string
  company_name: string
  title: string
  location: string | null
  employment_type: string | null
  salary_band: string | null
  description: string | null
  status: 'active' | 'closed'
  required_skills: { skill_name: string; required_level: number; weight: number }[]
}

type EmployerOpportunityForm = {
  company_name: string
  title: string
  location: string
  employment_type: string
  required_skills: string
}

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const targetRoleOptions = ['data analyst', 'software engineer', 'product manager']
const emptyOpportunityForm: EmployerOpportunityForm = {
  company_name: '',
  title: '',
  location: '',
  employment_type: 'full-time',
  required_skills: '',
}
const emptyAdminForm: AdminProvisionForm = {
  full_name: '',
  email: '',
  password: '',
  role: 'learner',
  institution_id: '',
}
const emptyInstitutionForm: NewInstitutionForm = { name: '', sector: '', location: '' }
const emptyCohortForm: InstitutionCohortForm = { name: '', program: '', capacity: 30 }

const featureCards = [
  {
    title: 'Skill gap intelligence',
    description:
      'Compare learner profiles against market demand, training outcomes, and curricular benchmarks to identify the most important gaps.',
    tag: 'Assessment',
  },
  {
    title: 'Personalized learning paths',
    description:
      'Recommend the next best learning module, project, and assessment based on current capability and target job clusters.',
    tag: 'Learning',
  },
  {
    title: 'Opportunity matching',
    description:
      'Align learners with internships, jobs, and apprenticeships that match their skill maturity and regional demand.',
    tag: 'Placement',
  },
  {
    title: 'Outcome tracking',
    description:
      'Track progress from enrollment to job readiness with a single governance layer for institutions and training partners.',
    tag: 'Impact',
  },
]

const emptyForm: FormState = {
  full_name: '',
  email: '',
  password: '',
}

function App() {
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [token, setToken] = useState<string | null>(null)
  const [currentUser, setCurrentUser] = useState<UserSession | null>(null)
  const [formData, setFormData] = useState<FormState>(emptyForm)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [learnerProfile, setLearnerProfile] = useState<LearnerProfile | null>(null)
  const [isLoadingLearnerProfile, setIsLoadingLearnerProfile] = useState(false)
  const [isSavingAssessment, setIsSavingAssessment] = useState(false)
  const [assessmentMessage, setAssessmentMessage] = useState('')
  const [assessmentError, setAssessmentError] = useState('')
  const [learningPath, setLearningPath] = useState<LearningPath | null>(null)
  const [isLoadingLearningPath, setIsLoadingLearningPath] = useState(false)
  const [isGeneratingLearningPath, setIsGeneratingLearningPath] = useState(false)
  const [learningPathError, setLearningPathError] = useState('')
  const [opportunityMatches, setOpportunityMatches] = useState<OpportunityMatch[]>([])
  const [isLoadingMatches, setIsLoadingMatches] = useState(false)
  const [matchesError, setMatchesError] = useState('')
  const [learnerApplications, setLearnerApplications] = useState<Application[]>([])
  const [applicationMessage, setApplicationMessage] = useState('')
  const [applicationError, setApplicationError] = useState('')
  const [applyingOpportunityId, setApplyingOpportunityId] = useState<string | null>(null)
  const [institutionAnalytics, setInstitutionAnalytics] = useState<InstitutionAnalytics | null>(null)
  const [isLoadingInstitutionAnalytics, setIsLoadingInstitutionAnalytics] = useState(false)
  const [institutionAnalyticsError, setInstitutionAnalyticsError] = useState('')
  const [institutionCohorts, setInstitutionCohorts] = useState<InstitutionCohort[]>([])
  const [institutionLearners, setInstitutionLearners] = useState<InstitutionLearner[]>([])
  const [cohortForm, setCohortForm] = useState<InstitutionCohortForm>(emptyCohortForm)
  const [selectedCohortLearners, setSelectedCohortLearners] = useState<Record<string, string>>({})
  const [isLoadingCohorts, setIsLoadingCohorts] = useState(false)
  const [isSavingCohort, setIsSavingCohort] = useState(false)
  const [cohortError, setCohortError] = useState('')
  const [cohortMessage, setCohortMessage] = useState('')
  const [employerOpportunities, setEmployerOpportunities] = useState<EmployerOpportunity[]>([])
  const [employerApplications, setEmployerApplications] = useState<Record<string, Application[]>>({})
  const [isLoadingEmployerOpportunities, setIsLoadingEmployerOpportunities] = useState(false)
  const [isSavingOpportunity, setIsSavingOpportunity] = useState(false)
  const [employerOpportunityError, setEmployerOpportunityError] = useState('')
  const [employerOpportunityMessage, setEmployerOpportunityMessage] = useState('')
  const [opportunityForm, setOpportunityForm] = useState<EmployerOpportunityForm>(emptyOpportunityForm)
  const [institutions, setInstitutions] = useState<InstitutionOption[]>([])
  const [adminProvisionForm, setAdminProvisionForm] = useState<AdminProvisionForm>(emptyAdminForm)
  const [newInstitutionForm, setNewInstitutionForm] = useState<NewInstitutionForm>(emptyInstitutionForm)
  const [adminSetupError, setAdminSetupError] = useState('')
  const [adminSetupMessage, setAdminSetupMessage] = useState('')
  const [isAdminSetupBusy, setIsAdminSetupBusy] = useState(false)

  useEffect(() => {
    if (!token || currentUser?.role !== 'learner') {
      setLearnerProfile(null)
      return
    }

    const loadLearnerProfile = async () => {
      setIsLoadingLearnerProfile(true)
      setAssessmentError('')
      try {
        const response = await fetch(`${API_BASE}/api/v1/learners/me/profile`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail ?? 'Unable to load learner profile.')
        }
        setLearnerProfile(data as LearnerProfile)
      } catch (loadError) {
        setAssessmentError(
          loadError instanceof Error ? loadError.message : 'Unable to load learner profile.',
        )
      } finally {
        setIsLoadingLearnerProfile(false)
      }
    }

    loadLearnerProfile().catch(() => setAssessmentError('Unable to load learner profile.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'institution') {
      setInstitutionAnalytics(null)
      setInstitutionCohorts([])
      setInstitutionLearners([])
      return
    }

    const loadInstitutionAnalytics = async () => {
      setIsLoadingInstitutionAnalytics(true)
      setInstitutionAnalyticsError('')
      try {
        const response = await fetch(`${API_BASE}/api/v1/institutions/me/analytics`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail ?? 'Unable to load institution analytics.')
        }
        setInstitutionAnalytics(data as InstitutionAnalytics)
      } catch (loadError) {
        setInstitutionAnalyticsError(
          loadError instanceof Error ? loadError.message : 'Unable to load institution analytics.',
        )
      } finally {
        setIsLoadingInstitutionAnalytics(false)
      }
    }

    loadInstitutionAnalytics().catch(() => setInstitutionAnalyticsError('Unable to load institution analytics.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'institution') return

    const loadCohortsAndLearners = async () => {
      setIsLoadingCohorts(true)
      setCohortError('')
      try {
        const headers = { Authorization: `Bearer ${token}` }
        const [cohortsResponse, learnersResponse] = await Promise.all([
          fetch(`${API_BASE}/api/v1/institutions/me/cohorts`, { headers }),
          fetch(`${API_BASE}/api/v1/institutions/me/learners`, { headers }),
        ])
        const cohortsData = await cohortsResponse.json()
        const learnersData = await learnersResponse.json()
        if (!cohortsResponse.ok) throw new Error(cohortsData.detail ?? 'Unable to load cohorts.')
        if (!learnersResponse.ok) throw new Error(learnersData.detail ?? 'Unable to load institution learners.')
        setInstitutionCohorts(cohortsData as InstitutionCohort[])
        setInstitutionLearners(learnersData as InstitutionLearner[])
      } catch (loadError) {
        setCohortError(loadError instanceof Error ? loadError.message : 'Unable to load cohorts.')
      } finally {
        setIsLoadingCohorts(false)
      }
    }

    loadCohortsAndLearners().catch(() => setCohortError('Unable to load cohorts.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'admin') {
      setInstitutions([])
      return
    }

    const loadInstitutions = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/admin/institutions`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail ?? 'Unable to load institutions.')
        setInstitutions(data as InstitutionOption[])
      } catch (loadError) {
        setAdminSetupError(loadError instanceof Error ? loadError.message : 'Unable to load institutions.')
      }
    }

    loadInstitutions().catch(() => setAdminSetupError('Unable to load institutions.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'learner') {
      setLearnerApplications([])
      return
    }

    const loadApplications = async () => {
      setApplicationError('')
      try {
        const response = await fetch(`${API_BASE}/api/v1/learners/me/applications`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail ?? 'Unable to load applications.')
        }
        setLearnerApplications(data as Application[])
      } catch (loadError) {
        setApplicationError(loadError instanceof Error ? loadError.message : 'Unable to load applications.')
      }
    }

    loadApplications().catch(() => setApplicationError('Unable to load applications.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'employer') {
      setEmployerOpportunities([])
      return
    }

    const loadEmployerOpportunities = async () => {
      setIsLoadingEmployerOpportunities(true)
      setEmployerOpportunityError('')
      try {
        const response = await fetch(`${API_BASE}/api/v1/employers/me/opportunities`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail ?? 'Unable to load employer listings.')
        }
        setEmployerOpportunities(data as EmployerOpportunity[])
        const applicantResults = await Promise.all(
          (data as EmployerOpportunity[]).map(async (opportunity) => {
            const applicantsResponse = await fetch(
              `${API_BASE}/api/v1/employers/me/opportunities/${opportunity.id}/applications`,
              { headers: { Authorization: `Bearer ${token}` } },
            )
            if (!applicantsResponse.ok) return [opportunity.id, []] as const
            return [opportunity.id, (await applicantsResponse.json()) as Application[]] as const
          }),
        )
        setEmployerApplications(Object.fromEntries(applicantResults))
      } catch (loadError) {
        setEmployerOpportunityError(
          loadError instanceof Error ? loadError.message : 'Unable to load employer listings.',
        )
      } finally {
        setIsLoadingEmployerOpportunities(false)
      }
    }

    loadEmployerOpportunities().catch(() => setEmployerOpportunityError('Unable to load employer listings.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'learner') {
      setOpportunityMatches([])
      return
    }

    const loadOpportunityMatches = async () => {
      setIsLoadingMatches(true)
      setMatchesError('')
      try {
        const response = await fetch(
          `${API_BASE}/api/v1/learners/me/opportunity-matches`,
          { headers: { Authorization: `Bearer ${token}` } },
        )
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail ?? 'Unable to load opportunity matches.')
        }
        setOpportunityMatches(data.matches as OpportunityMatch[])
      } catch (loadError) {
        setMatchesError(
          loadError instanceof Error ? loadError.message : 'Unable to load opportunity matches.',
        )
      } finally {
        setIsLoadingMatches(false)
      }
    }

    loadOpportunityMatches().catch(() => setMatchesError('Unable to load opportunity matches.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token || currentUser?.role !== 'learner') {
      setLearningPath(null)
      return
    }

    const loadLearningPath = async () => {
      setIsLoadingLearningPath(true)
      setLearningPathError('')
      try {
        const response = await fetch(
          `${API_BASE}/api/v1/learners/me/learning-paths/current`,
          { headers: { Authorization: `Bearer ${token}` } },
        )
        if (response.status === 404) {
          setLearningPath(null)
          return
        }
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail ?? 'Unable to load your learning roadmap.')
        }
        setLearningPath(data as LearningPath)
      } catch (loadError) {
        setLearningPathError(
          loadError instanceof Error ? loadError.message : 'Unable to load your learning roadmap.',
        )
      } finally {
        setIsLoadingLearningPath(false)
      }
    }

    loadLearningPath().catch(() => setLearningPathError('Unable to load your learning roadmap.'))
  }, [token, currentUser?.role])

  useEffect(() => {
    if (!token) {
      setCurrentUser(null)
      return
    }

    const fetchCurrentUser = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (!response.ok) {
          setToken(null)
          setCurrentUser(null)
          return
        }

        const data = (await response.json()) as UserSession
        setCurrentUser(data)
      } catch {
        setToken(null)
        setCurrentUser(null)
      }
    }

    fetchCurrentUser().catch(() => {
      setToken(null)
      setCurrentUser(null)
    })
  }, [token])

  const handleInputChange = (field: keyof FormState, value: string) => {
    setFormData((previous) => ({ ...previous, [field]: value }))
  }

  const handleSubmit = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)
    setError('')

    try {
      const endpoint = authMode === 'login' ? '/api/v1/auth/login' : '/api/v1/auth/register'
      const payload =
        authMode === 'login'
          ? { email: formData.email, password: formData.password }
          : formData

      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail ?? 'Authentication failed.')
      }

      if (authMode === 'register') {
        setAuthMode('login')
        setFormData({ ...emptyForm, email: formData.email })
        setError('Registration successful. Please log in to continue.')
        return
      }

      const nextToken = data.access_token as string
      setToken(nextToken)
      setFormData(emptyForm)
      setError('')
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : 'Something went wrong while authenticating.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleLogout = async () => {
    if (!token) return

    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    } catch {
      // Ignore transient network issues while ending the session.
    } finally {
      setToken(null)
      setCurrentUser(null)
    }
  }

  const handleSaveAssessment = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || !learnerProfile) return

    setIsSavingAssessment(true)
    setAssessmentMessage('')
    setAssessmentError('')
    try {
      const profileResponse = await fetch(`${API_BASE}/api/v1/learners/me/profile`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_role: learnerProfile.target_role,
          preferred_location: learnerProfile.preferred_location,
        }),
      })
      const profileData = await profileResponse.json()
      if (!profileResponse.ok) {
        throw new Error(profileData.detail ?? 'Unable to save learner profile.')
      }
      const updatedProfile = profileData as LearnerProfile

      const ratingsResponse = await fetch(`${API_BASE}/api/v1/learners/me/skills`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ratings: updatedProfile.skills.map(({ skill_name, self_rating }) => ({
            skill_name,
            self_rating,
          })),
        }),
      })
      const ratingsData = await ratingsResponse.json()
      if (!ratingsResponse.ok) {
        throw new Error(ratingsData.detail ?? 'Unable to save skill ratings.')
      }

      setLearnerProfile(ratingsData as LearnerProfile)
      setAssessmentMessage('Profile and skill assessment saved.')
      const matchesResponse = await fetch(
        `${API_BASE}/api/v1/learners/me/opportunity-matches`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
      if (matchesResponse.ok) {
        const matchesData = await matchesResponse.json()
        setOpportunityMatches(matchesData.matches as OpportunityMatch[])
      }
    } catch (saveError) {
      setAssessmentError(
        saveError instanceof Error ? saveError.message : 'Unable to save skill assessment.',
      )
    } finally {
      setIsSavingAssessment(false)
    }
  }

  const handleGenerateLearningPath = async () => {
    if (!token) return
    setIsGeneratingLearningPath(true)
    setLearningPathError('')
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/learners/me/learning-paths/generate`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        },
      )
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail ?? 'Unable to generate your learning roadmap.')
      }
      setLearningPath(data as LearningPath)
    } catch (generateError) {
      setLearningPathError(
        generateError instanceof Error
          ? generateError.message
          : 'Unable to generate your learning roadmap.',
      )
    } finally {
      setIsGeneratingLearningPath(false)
    }
  }

  const handleLearningItemStatus = async (item: LearningPathItem, status: LearningPathItem['status']) => {
    if (!token || !learningPath) return
    setLearningPathError('')
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/learners/me/learning-path-items/${item.id}`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status }),
        },
      )
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail ?? 'Unable to update roadmap progress.')
      }
      const updatedItem = data as LearningPathItem
      const updatedItems = learningPath.items.map((pathItem) =>
        pathItem.id === updatedItem.id ? updatedItem : pathItem,
      )
      setLearningPath({
        ...learningPath,
        items: updatedItems,
        status: updatedItems.every((pathItem) => pathItem.status === 'completed')
          ? 'completed'
          : 'active',
      })
    } catch (updateError) {
      setLearningPathError(
        updateError instanceof Error ? updateError.message : 'Unable to update roadmap progress.',
      )
    }
  }

  const scrollToSection = (sectionId: string) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const handleCreateOpportunity = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token) return
    setIsSavingOpportunity(true)
    setEmployerOpportunityError('')
    setEmployerOpportunityMessage('')
    try {
      const response = await fetch(`${API_BASE}/api/v1/opportunities`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: opportunityForm.company_name,
          title: opportunityForm.title,
          location: opportunityForm.location || null,
          employment_type: opportunityForm.employment_type || null,
          required_skills: opportunityForm.required_skills
            .split(',')
            .map((skill_name) => skill_name.trim())
            .filter(Boolean)
            .map((skill_name) => ({ skill_name, required_level: 3, weight: 1 })),
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail ?? 'Unable to create opportunity.')
      }
      setOpportunityForm(emptyOpportunityForm)
      setEmployerOpportunityMessage('Opportunity published.')
      const listingsResponse = await fetch(`${API_BASE}/api/v1/employers/me/opportunities`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (listingsResponse.ok) {
        setEmployerOpportunities((await listingsResponse.json()) as EmployerOpportunity[])
      }
    } catch (createError) {
      setEmployerOpportunityError(
        createError instanceof Error ? createError.message : 'Unable to create opportunity.',
      )
    } finally {
      setIsSavingOpportunity(false)
    }
  }

  const handleOpportunityStatus = async (opportunity: EmployerOpportunity) => {
    if (!token) return
    setEmployerOpportunityError('')
    setEmployerOpportunityMessage('')
    const nextStatus = opportunity.status === 'active' ? 'closed' : 'active'
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/employers/me/opportunities/${opportunity.id}`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status: nextStatus }),
        },
      )
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail ?? 'Unable to update opportunity status.')
      }
      const updated = data as EmployerOpportunity
      setEmployerOpportunities((listings) =>
        listings.map((listing) => (listing.id === updated.id ? updated : listing)),
      )
    } catch (updateError) {
      setEmployerOpportunityError(
        updateError instanceof Error ? updateError.message : 'Unable to update opportunity status.',
      )
    }
  }

  const handleApplyToOpportunity = async (opportunity: OpportunityMatch) => {
    if (!token) return
    setApplyingOpportunityId(opportunity.id)
    setApplicationError('')
    setApplicationMessage('')
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/learners/me/opportunities/${opportunity.id}/applications`,
        { method: 'POST', headers: { Authorization: `Bearer ${token}` } },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? 'Unable to submit application.')
      setLearnerApplications((applications) => [data as Application, ...applications])
      setApplicationMessage(`Application submitted for ${opportunity.title}.`)
    } catch (applyError) {
      setApplicationError(applyError instanceof Error ? applyError.message : 'Unable to submit application.')
    } finally {
      setApplyingOpportunityId(null)
    }
  }

  const handleApplicationStatus = async (application: Application, nextStatus: string) => {
    if (!token) return
    setEmployerOpportunityError('')
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/employers/me/applications/${application.id}`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status: nextStatus }),
        },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? 'Unable to update application status.')
      const updated = data as Application
      setEmployerApplications((applications) => ({
        ...applications,
        [updated.opportunity_id]: (applications[updated.opportunity_id] ?? []).map((item) =>
          item.id === updated.id ? updated : item,
        ),
      }))
    } catch (updateError) {
      setEmployerOpportunityError(
        updateError instanceof Error ? updateError.message : 'Unable to update applicant status.',
      )
    }
  }

  const handleCreateInstitution = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token) return
    setIsAdminSetupBusy(true)
    setAdminSetupError('')
    setAdminSetupMessage('')
    try {
      const response = await fetch(`${API_BASE}/api/v1/admin/institutions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newInstitutionForm,
          location: newInstitutionForm.location || null,
        }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? 'Unable to create institution.')
      const institution = data as InstitutionOption
      setInstitutions((items) => [...items, institution].sort((left, right) => left.name.localeCompare(right.name)))
      setAdminProvisionForm((form) => ({ ...form, institution_id: institution.id, role: 'institution' }))
      setNewInstitutionForm(emptyInstitutionForm)
      setAdminSetupMessage('Institution created.')
    } catch (createError) {
      setAdminSetupError(createError instanceof Error ? createError.message : 'Unable to create institution.')
    } finally {
      setIsAdminSetupBusy(false)
    }
  }

  const handleProvisionAccount = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token) return
    setIsAdminSetupBusy(true)
    setAdminSetupError('')
    setAdminSetupMessage('')
    try {
      const response = await fetch(`${API_BASE}/api/v1/admin/users`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: adminProvisionForm.full_name,
          email: adminProvisionForm.email,
          password: adminProvisionForm.password,
          role: adminProvisionForm.role,
          institution_id: adminProvisionForm.role !== 'employer'
            ? adminProvisionForm.institution_id
            : null,
        }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? 'Unable to provision account.')
      setAdminProvisionForm({ ...emptyAdminForm, institution_id: adminProvisionForm.institution_id })
      setAdminSetupMessage(`${data.role} account created for ${data.email}.`)
    } catch (provisionError) {
      setAdminSetupError(
        provisionError instanceof Error ? provisionError.message : 'Unable to provision account.',
      )
    } finally {
      setIsAdminSetupBusy(false)
    }
  }

  const handleCreateCohort = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token) return
    setIsSavingCohort(true)
    setCohortError('')
    setCohortMessage('')
    try {
      const response = await fetch(`${API_BASE}/api/v1/institutions/me/cohorts`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cohortForm),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? 'Unable to create cohort.')
      setInstitutionCohorts((cohorts) => [data as InstitutionCohort, ...cohorts])
      setCohortForm(emptyCohortForm)
      setCohortMessage('Cohort created.')
    } catch (createError) {
      setCohortError(createError instanceof Error ? createError.message : 'Unable to create cohort.')
    } finally {
      setIsSavingCohort(false)
    }
  }

  const handleEnrollCohortLearner = async (cohort: InstitutionCohort) => {
    if (!token) return
    const learnerUserId = selectedCohortLearners[cohort.id]
    if (!learnerUserId) return
    setCohortError('')
    setCohortMessage('')
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/institutions/me/cohorts/${cohort.id}/learners`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ learner_user_id: learnerUserId }),
        },
      )
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail ?? 'Unable to enroll learner.')
      setInstitutionCohorts((cohorts) => cohorts.map((current) => {
        if (current.id !== cohort.id) return current
        return {
          ...current,
          learner_count: current.learner_count + 1,
          learners: [...current.learners, { ...data, user_id: data.user_id }],
        }
      }))
      setSelectedCohortLearners((selected) => ({ ...selected, [cohort.id]: '' }))
      setCohortMessage(`${data.full_name} enrolled in ${cohort.name}.`)
    } catch (enrollError) {
      setCohortError(enrollError instanceof Error ? enrollError.message : 'Unable to enroll learner.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-400 text-sm font-black text-slate-950">
              SB
            </div>
            <div>
              <p className="text-lg font-semibold tracking-tight text-white">SkillBridge AI</p>
            </div>
          </div>

          <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
            <button type="button" onClick={() => scrollToSection('platform')} className="transition hover:text-white">Platform</button>
            <button type="button" onClick={() => scrollToSection('features')} className="transition hover:text-white">Features</button>
            <button type="button" onClick={() => scrollToSection('dashboard')} className="transition hover:text-white">Dashboard</button>
            <button type="button" onClick={() => scrollToSection('impact')} className="transition hover:text-white">Impact</button>
          </nav>

          <div className="flex items-center gap-3">
            {currentUser ? (
              <>
                <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 sm:inline-flex">
                  {currentUser.role}
                </span>
                <button
                  onClick={handleLogout}
                  className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:border-amber-400 hover:text-white"
                >
                  Sign out
                </button>
              </>
            ) : (
              <button
                onClick={() => setAuthMode('login')}
                className="hidden rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:border-amber-400 hover:text-white sm:inline-flex"
              >
                Sign in
              </button>
            )}
            <button
              type="button"
              onClick={() => scrollToSection('platform')}
              className="rounded-full bg-amber-400 px-5 py-2.5 text-sm font-semibold text-slate-950 shadow-lg shadow-amber-500/20 transition hover:bg-amber-300"
            >
              Explore platform
            </button>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-7xl px-6 pb-20 pt-14 lg:px-8 lg:pb-28 lg:pt-20">
          <div className="grid items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
            <div>
              <span className="pill">Smart India Hackathon • SIH26134 & SIH26135</span>
              <h1 className="mt-6 max-w-xl text-4xl font-black tracking-tight text-white md:text-5xl lg:text-6xl">
                Align skills with demand and prove employment impact.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
                SkillBridge AI helps institutions, employers, and learners connect skill demand to measurable outcomes with data-backed recommendations, cohort planning, and placement tracking.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={() => scrollToSection('platform')}
                  className="rounded-full bg-amber-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-amber-300"
                >
                  Explore platform
                </button>
                <button
                  onClick={() => setAuthMode('login')}
                  className="rounded-full border border-slate-700 px-6 py-3 font-semibold text-slate-100 transition hover:border-slate-500 hover:bg-slate-900"
                >
                  Sign in
                </button>
              </div>

              {currentUser?.role === 'institution' && institutionAnalytics && (
                <div className="mt-10 grid max-w-xl gap-5 sm:grid-cols-3">
                  {[
                    { label: 'Learners', value: institutionAnalytics.learner_count },
                    { label: 'Applicants', value: institutionAnalytics.applicants_count },
                    { label: 'Placements', value: institutionAnalytics.placement_count },
                  ].map((item) => (
                    <div key={item.label} className="panel-surface p-4">
                      <div className="text-2xl font-black text-white">{item.value}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">{item.label}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="panel-surface p-4 sm:p-6">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5">
                {currentUser ? (
                  <div>
                    <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Signed in</p>
                        <h2 className="mt-2 text-2xl font-bold text-white">{currentUser.full_name}</h2>
                      </div>
                      <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-300">
                        {currentUser.role}
                      </span>
                    </div>

                    <div className="mt-5 space-y-3 text-sm text-slate-300">
                      <p>Email: {currentUser.email}</p>
                      <p>Session: authenticated and role-aware</p>
                      <p>Token storage: browser memory for this active session</p>
                    </div>

                    {currentUser.role === 'admin' && (
                      <div className="mt-6 border-t border-slate-800 pt-5">
                        <h3 className="text-lg font-semibold text-white">Account setup</h3>
                        <form onSubmit={handleCreateInstitution} className="mt-4 space-y-3">
                          <h4 className="text-sm font-medium text-slate-200">Create institution</h4>
                          <label className="block text-sm text-slate-300">
                            <span>Institution name</span>
                            <input
                              required
                              minLength={2}
                              value={newInstitutionForm.name}
                              onChange={(event) => setNewInstitutionForm({ ...newInstitutionForm, name: event.target.value })}
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          <div className="grid grid-cols-2 gap-3">
                            <label className="block text-sm text-slate-300">
                              <span>Sector</span>
                              <input
                                required
                                minLength={2}
                                value={newInstitutionForm.sector}
                                onChange={(event) => setNewInstitutionForm({ ...newInstitutionForm, sector: event.target.value })}
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                              />
                            </label>
                            <label className="block text-sm text-slate-300">
                              <span>Location</span>
                              <input
                                value={newInstitutionForm.location}
                                onChange={(event) => setNewInstitutionForm({ ...newInstitutionForm, location: event.target.value })}
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                              />
                            </label>
                          </div>
                          <button
                            type="submit"
                            disabled={isAdminSetupBusy}
                            className="w-full rounded-lg border border-amber-400/50 px-4 py-2.5 text-sm font-semibold text-amber-200 hover:bg-amber-400/10 disabled:opacity-50"
                          >
                            Create institution
                          </button>
                        </form>

                        <form onSubmit={handleProvisionAccount} className="mt-6 space-y-3 border-t border-slate-800 pt-5">
                          <h4 className="text-sm font-medium text-slate-200">Provision account</h4>
                          <label className="block text-sm text-slate-300">
                            <span>Account role</span>
                            <select
                              value={adminProvisionForm.role}
                              onChange={(event) =>
                                setAdminProvisionForm({
                                  ...adminProvisionForm,
                                  role: event.target.value as AdminProvisionForm['role'],
                                })
                              }
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            >
                              <option value="learner">Learner</option>
                              <option value="employer">Employer</option>
                              <option value="institution">Institution</option>
                            </select>
                          </label>
                          {adminProvisionForm.role !== 'employer' && (
                            <label className="block text-sm text-slate-300">
                              <span>Institution</span>
                              <select
                                required
                                value={adminProvisionForm.institution_id}
                                onChange={(event) => setAdminProvisionForm({ ...adminProvisionForm, institution_id: event.target.value })}
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                              >
                                <option value="">Select institution</option>
                                {institutions.map((institution) => (
                                  <option key={institution.id} value={institution.id}>{institution.name}</option>
                                ))}
                              </select>
                            </label>
                          )}
                          <label className="block text-sm text-slate-300">
                            <span>Full name</span>
                            <input
                              required
                              minLength={2}
                              value={adminProvisionForm.full_name}
                              onChange={(event) => setAdminProvisionForm({ ...adminProvisionForm, full_name: event.target.value })}
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          <label className="block text-sm text-slate-300">
                            <span>Email</span>
                            <input
                              type="email"
                              required
                              value={adminProvisionForm.email}
                              onChange={(event) => setAdminProvisionForm({ ...adminProvisionForm, email: event.target.value })}
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          <label className="block text-sm text-slate-300">
                            <span>Temporary password</span>
                            <input
                              type="password"
                              required
                              minLength={8}
                              maxLength={72}
                              value={adminProvisionForm.password}
                              onChange={(event) => setAdminProvisionForm({ ...adminProvisionForm, password: event.target.value })}
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          <button
                            type="submit"
                            disabled={isAdminSetupBusy || (adminProvisionForm.role !== 'employer' && institutions.length === 0)}
                            className="w-full rounded-lg bg-amber-400 px-4 py-2.5 font-semibold text-slate-950 hover:bg-amber-300 disabled:opacity-50"
                          >
                            Create account
                          </button>
                        </form>
                        {adminSetupError && <p role="alert" className="mt-3 text-sm text-red-300">{adminSetupError}</p>}
                        {adminSetupMessage && <output className="mt-3 block text-sm text-emerald-300">{adminSetupMessage}</output>}
                      </div>
                    )}

                    {currentUser.role === 'learner' && (
                      <div className="mt-6 border-t border-slate-800 pt-5">
                        <h3 className="text-lg font-semibold text-white">Career profile</h3>
                        {isLoadingLearnerProfile && (
                          <p className="mt-3 text-sm text-slate-400">Loading your assessment...</p>
                        )}
                        {learnerProfile && (
                          <form onSubmit={handleSaveAssessment} className="mt-4 space-y-4">
                            <label className="block text-sm text-slate-300">
                              <span>Target role</span>
                              <select
                                value={learnerProfile.target_role}
                                onChange={(event) =>
                                  setLearnerProfile({
                                    ...learnerProfile,
                                    target_role: event.target.value,
                                  })
                                }
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                              >
                                {targetRoleOptions.map((role) => (
                                  <option key={role} value={role}>
                                    {role.replace(/\b\w/g, (letter) => letter.toUpperCase())}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label className="block text-sm text-slate-300">
                              <span>Preferred location</span>
                              <input
                                value={learnerProfile.preferred_location ?? ''}
                                onChange={(event) =>
                                  setLearnerProfile({
                                    ...learnerProfile,
                                    preferred_location: event.target.value || null,
                                  })
                                }
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                                placeholder="City or region"
                              />
                            </label>
                            <div className="space-y-4">
                              {learnerProfile.skills.map((skill) => (
                                <label key={skill.skill_name} className="block text-sm text-slate-300">
                                  <span className="flex items-center justify-between gap-3">
                                    <span>{skill.skill_name}</span>
                                    <span className="tabular-nums text-slate-400">
                                      {skill.self_rating.toFixed(1)} / 5
                                    </span>
                                  </span>
                                  <input
                                    type="range"
                                    min="0"
                                    max="5"
                                    step="0.5"
                                    value={skill.self_rating}
                                    onChange={(event) => {
                                      const rating = Number(event.target.value)
                                      setLearnerProfile({
                                        ...learnerProfile,
                                        skills: learnerProfile.skills.map((candidate) =>
                                          candidate.skill_name === skill.skill_name
                                            ? { ...candidate, self_rating: rating }
                                            : candidate,
                                        ),
                                      })
                                    }}
                                    className="mt-2 w-full accent-amber-400"
                                  />
                                  <span className="mt-1 block text-xs text-slate-500">
                                    Gap to target: {Math.max(0, skill.target_rating - skill.self_rating).toFixed(1)}
                                  </span>
                                </label>
                              ))}
                            </div>
                            {assessmentError && (
                              <p role="alert" className="text-sm text-red-300">{assessmentError}</p>
                            )}
                            {assessmentMessage && (
                              <output className="block text-sm text-emerald-300">{assessmentMessage}</output>
                            )}
                            <button
                              type="submit"
                              disabled={isSavingAssessment || isLoadingLearnerProfile}
                              className="w-full rounded-lg bg-amber-400 px-4 py-2.5 font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {isSavingAssessment ? 'Saving assessment...' : 'Save assessment'}
                            </button>
                          </form>
                        )}
                        {assessmentError && !learnerProfile && (
                          <p role="alert" className="mt-3 text-sm text-red-300">{assessmentError}</p>
                        )}
                      </div>
                    )}

                    {currentUser.role === 'learner' && (
                      <div className="mt-6 border-t border-slate-800 pt-5">
                        <div className="flex items-center justify-between gap-3">
                          <h3 className="text-lg font-semibold text-white">Learning roadmap</h3>
                          <button
                            type="button"
                            onClick={handleGenerateLearningPath}
                            disabled={isGeneratingLearningPath || isLoadingLearnerProfile || !learnerProfile}
                            className="rounded-lg border border-amber-400/50 px-3 py-2 text-xs font-semibold text-amber-200 hover:bg-amber-400/10 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {getLearningPathButtonLabel(isGeneratingLearningPath, Boolean(learningPath))}
                          </button>
                        </div>
                        {isLoadingLearningPath && (
                          <p className="mt-3 text-sm text-slate-400">Loading your roadmap...</p>
                        )}
                        {learningPathError && (
                          <p role="alert" className="mt-3 text-sm text-red-300">{learningPathError}</p>
                        )}
                        {!isLoadingLearningPath && !learningPath && !learningPathError && (
                          <p className="mt-3 text-sm text-slate-400">
                            Generate a roadmap from your current skill gaps.
                          </p>
                        )}
                        {learningPath && (
                          <div className="mt-4">
                            <p className="text-sm text-slate-300">{learningPath.title}</p>
                            <ol className="mt-3 space-y-2">
                              {learningPath.items.map((item) => (
                                <li
                                  key={item.id}
                                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/70 p-3"
                                >
                                  <div className="min-w-0">
                                    <p className="text-sm text-slate-200">{item.order_index + 1}. {item.title}</p>
                                    <p className="mt-1 text-xs capitalize text-slate-500">
                                      {item.module_type} · {item.estimated_hours ?? 'Flexible'} hours
                                    </p>
                                    {item.resource_url ? (
                                      <a
                                        href={item.resource_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="mt-2 inline-block text-xs font-medium text-amber-300 underline decoration-amber-300/40 underline-offset-2 hover:text-amber-200"
                                      >
                                        {item.resource_label ?? 'Open learning resource'}
                                      </a>
                                    ) : (
                                      <p className="mt-2 text-xs text-slate-500">Curated resource coming soon</p>
                                    )}
                                  </div>
                                  <select
                                    aria-label={`Progress for ${item.title}`}
                                    value={item.status}
                                    onChange={(event) =>
                                      handleLearningItemStatus(
                                        item,
                                        event.target.value as LearningPathItem['status'],
                                      )
                                    }
                                    className="w-32 shrink-0 rounded-md border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-200"
                                  >
                                    <option value="not_started">Not started</option>
                                    <option value="in_progress">In progress</option>
                                    <option value="completed">Completed</option>
                                  </select>
                                </li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    )}

                    {currentUser.role === 'employer' && (
                      <div className="mt-6 border-t border-slate-800 pt-5">
                        <h3 className="text-lg font-semibold text-white">Employer listings</h3>
                        <form onSubmit={handleCreateOpportunity} className="mt-4 space-y-3">
                          <label className="block text-sm text-slate-300">
                            <span>Company name</span>
                            <input
                              required
                              value={opportunityForm.company_name}
                              onChange={(event) =>
                                setOpportunityForm({ ...opportunityForm, company_name: event.target.value })
                              }
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          <label className="block text-sm text-slate-300">
                            <span>Role title</span>
                            <input
                              required
                              value={opportunityForm.title}
                              onChange={(event) =>
                                setOpportunityForm({ ...opportunityForm, title: event.target.value })
                              }
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          <div className="grid grid-cols-2 gap-3">
                            <label className="block text-sm text-slate-300">
                              <span>Location</span>
                              <input
                                value={opportunityForm.location}
                                onChange={(event) =>
                                  setOpportunityForm({ ...opportunityForm, location: event.target.value })
                                }
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                              />
                            </label>
                            <label className="block text-sm text-slate-300">
                              <span>Employment</span>
                              <select
                                value={opportunityForm.employment_type}
                                onChange={(event) =>
                                  setOpportunityForm({ ...opportunityForm, employment_type: event.target.value })
                                }
                                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                              >
                                <option value="full-time">Full-time</option>
                                <option value="part-time">Part-time</option>
                                <option value="internship">Internship</option>
                                <option value="apprenticeship">Apprenticeship</option>
                              </select>
                            </label>
                          </div>
                          <label className="block text-sm text-slate-300">
                            <span>Required skills</span>
                            <input
                              value={opportunityForm.required_skills}
                              onChange={(event) =>
                                setOpportunityForm({ ...opportunityForm, required_skills: event.target.value })
                              }
                              placeholder="Python, SQL, communication"
                              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none focus:border-amber-400"
                            />
                          </label>
                          {employerOpportunityError && (
                            <p role="alert" className="text-sm text-red-300">{employerOpportunityError}</p>
                          )}
                          {employerOpportunityMessage && (
                            <output className="block text-sm text-emerald-300">{employerOpportunityMessage}</output>
                          )}
                          <button
                            type="submit"
                            disabled={isSavingOpportunity}
                            className="w-full rounded-lg bg-amber-400 px-4 py-2.5 font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {isSavingOpportunity ? 'Publishing...' : 'Publish opportunity'}
                          </button>
                        </form>

                        <div className="mt-6">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-semibold text-slate-200">Your opportunities</h4>
                            <span className="text-xs text-slate-500">{employerOpportunities.length} total</span>
                          </div>
                          {isLoadingEmployerOpportunities && (
                            <p className="mt-3 text-sm text-slate-400">Loading listings...</p>
                          )}
                          {!isLoadingEmployerOpportunities && employerOpportunities.length === 0 && !employerOpportunityError && (
                            <p className="mt-3 text-sm text-slate-400">You have not published any opportunities.</p>
                          )}
                          <ul className="mt-3 space-y-2">
                            {employerOpportunities.map((opportunity) => (
                              <li
                                key={opportunity.id}
                                className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/70 p-3"
                              >
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-medium text-slate-100">{opportunity.title}</p>
                                  <p className="mt-1 text-xs text-slate-400">{opportunity.company_name}</p>
                                  <p className="mt-1 text-xs capitalize text-slate-500">{opportunity.status}</p>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleOpportunityStatus(opportunity)}
                                  className="shrink-0 rounded-md border border-slate-700 px-2.5 py-2 text-xs text-slate-200 hover:border-amber-400"
                                >
                                  {opportunity.status === 'active' ? 'Close' : 'Reopen'}
                                </button>
                                <span className="shrink-0 text-xs text-slate-400">
                                  {(employerApplications[opportunity.id] ?? []).length} applicants
                                </span>
                              </li>
                            ))}
                          </ul>
                          {Object.entries(employerApplications).some(([, applications]) => applications.length > 0) && (
                            <div className="mt-5 space-y-4">
                              {employerOpportunities.map((opportunity) => {
                                const applicants = employerApplications[opportunity.id] ?? []
                                if (applicants.length === 0) return null
                                return (
                                  <section key={opportunity.id}>
                                    <h5 className="text-sm font-semibold text-slate-200">Applicants: {opportunity.title}</h5>
                                    <ul className="mt-2 space-y-2">
                                      {applicants.map((application) => (
                                        <li key={application.id} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                                          <div className="flex items-center justify-between gap-3">
                                            <div className="min-w-0">
                                              <p className="truncate text-sm text-slate-100">{application.learner_name}</p>
                                              <p className="truncate text-xs text-slate-400">{application.learner_email}</p>
                                            </div>
                                            <select
                                              aria-label={`Status for ${application.learner_name}`}
                                              value={application.status}
                                              onChange={(event) => handleApplicationStatus(application, event.target.value)}
                                              className="w-32 shrink-0 rounded-md border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-200"
                                            >
                                              <option value="applied">Applied</option>
                                              <option value="reviewing">Reviewing</option>
                                              <option value="interview">Interview</option>
                                              <option value="offered">Offered</option>
                                              <option value="hired">Hired</option>
                                              <option value="rejected">Rejected</option>
                                            </select>
                                          </div>
                                          {application.placement_date && (
                                            <p className="mt-2 text-xs text-emerald-300">
                                              Placed {new Date(application.placement_date).toLocaleDateString()}
                                            </p>
                                          )}
                                        </li>
                                      ))}
                                    </ul>
                                  </section>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="flex rounded-full border border-slate-700 bg-slate-900 p-1">
                      <button
                        type="button"
                        onClick={() => setAuthMode('login')}
                        className={`flex-1 rounded-full px-3 py-2 text-sm font-medium transition ${
                          authMode === 'login' ? 'bg-amber-400 text-slate-950' : 'text-slate-300'
                        }`}
                      >
                        Login
                      </button>
                      <button
                        type="button"
                        onClick={() => setAuthMode('register')}
                        className={`flex-1 rounded-full px-3 py-2 text-sm font-medium transition ${
                          authMode === 'register' ? 'bg-amber-400 text-slate-950' : 'text-slate-300'
                        }`}
                      >
                        Register
                      </button>
                    </div>

                    {authMode === 'register' && (
                      <label className="block text-sm text-slate-300">
                        <span>Full name</span>
                        <input
                          value={formData.full_name}
                          onChange={(event) => handleInputChange('full_name', event.target.value)}
                          className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-amber-400"
                          placeholder="Your full name"
                          required
                        />
                      </label>
                    )}

                    <label className="block text-sm text-slate-300">
                      <span>Email</span>
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(event) => handleInputChange('email', event.target.value)}
                        className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-amber-400"
                        placeholder="name@example.com"
                        required
                      />
                    </label>

                    <label className="block text-sm text-slate-300">
                      <span>Password</span>
                      <input
                        type="password"
                        value={formData.password}
                        onChange={(event) => handleInputChange('password', event.target.value)}
                        className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-white outline-none transition focus:border-amber-400"
                        placeholder="Minimum 8 characters"
                        required
                      />
                    </label>

                    {error && (
                      <p className="rounded-xl border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                        {error}
                      </p>
                    )}

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full rounded-xl bg-amber-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-70"
                    >
                      {getAuthSubmitLabel(isSubmitting, authMode)}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-6 py-8 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <span className="pill">Platform capabilities</span>
            <h2 className="mt-5 text-3xl font-black tracking-tight text-white md:text-4xl">
              A single operating layer for learning, jobs, and outcomes.
            </h2>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {featureCards.map((feature) => (
              <article key={feature.title} className="panel-surface p-6">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-300">
                  {feature.tag}
                </span>
                <h3 className="mt-4 text-xl font-bold text-white">{feature.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-300">{feature.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="dashboard" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="panel-surface p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Operational insight</p>
                  <h3 className="mt-2 text-2xl font-bold text-white">Cohort readiness overview</h3>
                </div>
                <button className="rounded-full border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500">
                  Export brief
                </button>
              </div>

              {currentUser?.role === 'institution' ? (
                <div className="mt-8">
                  {isLoadingInstitutionAnalytics && (
                    <p className="text-sm text-slate-400">Loading institution analytics...</p>
                  )}
                  {institutionAnalyticsError && (
                    <p role="alert" className="text-sm text-red-300">{institutionAnalyticsError}</p>
                  )}
                  {institutionAnalytics && (
                    <div className="space-y-5">
                      {[
                        { label: 'Learners assessed', value: institutionAnalytics.assessed_learner_count, total: institutionAnalytics.learner_count },
                        { label: 'Learners with applications', value: institutionAnalytics.applicants_count, total: institutionAnalytics.learner_count },
                        { label: 'Learners placed', value: institutionAnalytics.placement_count, total: institutionAnalytics.learner_count },
                      ].map((metric) => {
                        const percentage = metric.total
                          ? Math.round((metric.value / metric.total) * 100)
                          : 0
                        return (
                          <div key={metric.label}>
                            <div className="mb-2 flex items-center justify-between gap-3 text-sm text-slate-300">
                              <span>{metric.label}</span>
                              <span>{metric.value} / {metric.total} ({percentage}%)</span>
                            </div>
                            <div className="h-2.5 rounded-full bg-slate-800">
                              <div
                                className="h-2.5 rounded-full bg-gradient-to-r from-amber-300 via-yellow-400 to-orange-400"
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                          </div>
                        )
                      })}
                      <p className="text-xs text-slate-500">
                        {institutionAnalytics.active_opportunity_count} active institution opportunities · {institutionAnalytics.application_count} applications
                      </p>
                    </div>
                  )}
                  {!isLoadingInstitutionAnalytics && !institutionAnalytics && !institutionAnalyticsError && (
                    <p className="text-sm text-slate-400">No institution analytics are available.</p>
                  )}

                  <div className="mt-8 border-t border-slate-800 pt-6">
                    <div className="flex items-center justify-between gap-3">
                      <h4 className="text-lg font-semibold text-white">Training cohorts</h4>
                      <span className="text-xs text-slate-500">{institutionCohorts.length} total</span>
                    </div>
                    <form onSubmit={handleCreateCohort} className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_110px_auto]">
                      <input
                        required
                        minLength={2}
                        aria-label="Cohort name"
                        placeholder="Cohort name"
                        value={cohortForm.name}
                        onChange={(event) => setCohortForm({ ...cohortForm, name: event.target.value })}
                        className="min-w-0 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-amber-400"
                      />
                      <input
                        required
                        minLength={2}
                        aria-label="Program"
                        placeholder="Program"
                        value={cohortForm.program}
                        onChange={(event) => setCohortForm({ ...cohortForm, program: event.target.value })}
                        className="min-w-0 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-amber-400"
                      />
                      <input
                        required
                        type="number"
                        min="1"
                        max="5000"
                        aria-label="Cohort capacity"
                        value={cohortForm.capacity}
                        onChange={(event) => setCohortForm({ ...cohortForm, capacity: Number(event.target.value) })}
                        className="min-w-0 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none focus:border-amber-400"
                      />
                      <button
                        type="submit"
                        disabled={isSavingCohort}
                        className="rounded-lg bg-amber-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-300 disabled:opacity-50"
                      >
                        {isSavingCohort ? 'Creating...' : 'Create cohort'}
                      </button>
                    </form>
                    {cohortError && <p role="alert" className="mt-3 text-sm text-red-300">{cohortError}</p>}
                    {cohortMessage && <output className="mt-3 block text-sm text-emerald-300">{cohortMessage}</output>}
                    {isLoadingCohorts && <p className="mt-4 text-sm text-slate-400">Loading cohorts...</p>}
                    {!isLoadingCohorts && institutionCohorts.length === 0 && (
                      <p className="mt-4 text-sm text-slate-400">No training cohorts yet.</p>
                    )}
                    <div className="mt-4 space-y-3">
                      {institutionCohorts.map((cohort) => {
                        const enrolledIds = new Set(cohort.learners.map((learner) => learner.user_id))
                        const eligibleLearners = institutionLearners.filter((learner) => !enrolledIds.has(learner.id))
                        return (
                          <article key={cohort.id} className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <h5 className="font-semibold text-slate-100">{cohort.name}</h5>
                                <p className="mt-1 text-sm text-slate-400">{cohort.program}</p>
                              </div>
                              <span className="text-xs tabular-nums text-slate-400">
                                {cohort.learner_count} / {cohort.capacity} learners
                              </span>
                            </div>
                            <div className="mt-4 grid grid-cols-3 gap-3 border-y border-slate-800 py-3">
                              <div>
                                <p className="text-lg font-semibold tabular-nums text-slate-100">{cohort.assessed_learner_count}</p>
                                <p className="text-xs text-slate-500">Assessed</p>
                              </div>
                              <div>
                                <p className="text-lg font-semibold tabular-nums text-slate-100">{cohort.application_count}</p>
                                <p className="text-xs text-slate-500">Applications</p>
                              </div>
                              <div>
                                <p className="text-lg font-semibold tabular-nums text-emerald-300">{cohort.placement_count}</p>
                                <p className="text-xs text-slate-500">Placements</p>
                              </div>
                            </div>
                            {cohort.learner_count < cohort.capacity && eligibleLearners.length > 0 && (
                              <div className="mt-4 flex flex-wrap gap-2">
                                <select
                                  aria-label={`Select learner for ${cohort.name}`}
                                  value={selectedCohortLearners[cohort.id] ?? ''}
                                  onChange={(event) => setSelectedCohortLearners({ ...selectedCohortLearners, [cohort.id]: event.target.value })}
                                  className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                                >
                                  <option value="">Select institution learner</option>
                                  {eligibleLearners.map((learner) => (
                                    <option key={learner.id} value={learner.id}>{learner.full_name} · {learner.email}</option>
                                  ))}
                                </select>
                                <button
                                  type="button"
                                  disabled={!selectedCohortLearners[cohort.id]}
                                  onClick={() => handleEnrollCohortLearner(cohort)}
                                  className="rounded-md border border-amber-400/50 px-3 py-2 text-sm text-amber-200 hover:bg-amber-400/10 disabled:opacity-40"
                                >
                                  Enroll learner
                                </button>
                              </div>
                            )}
                            {cohort.learners.length > 0 && (
                              <ul className="mt-4 divide-y divide-slate-800">
                                {cohort.learners.map((learner) => (
                                  <li key={learner.user_id} className="flex flex-wrap justify-between gap-2 py-2 text-sm">
                                    <span className="text-slate-200">{learner.full_name}</span>
                                    <span className="text-slate-500">{learner.email}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </article>
                        )
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-8 text-sm text-slate-400">
                  Sign in with an institution account to view learner assessment, cohort, application, and placement metrics.
                </p>
              )}
            </div>

            <div id="impact" className="panel-surface p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Opportunity pipeline</p>
              <h3 className="mt-2 text-2xl font-bold text-white">Best-fit openings</h3>

              {!currentUser && (
                <p className="mt-5 text-sm text-slate-400">Sign in as a learner to see skill-based matches.</p>
              )}
              {currentUser && currentUser.role !== 'learner' && (
                <p className="mt-5 text-sm text-slate-400">Opportunity matches are available in learner accounts.</p>
              )}
              {currentUser?.role === 'learner' && isLoadingMatches && (
                <p className="mt-5 text-sm text-slate-400">Finding active opportunities...</p>
              )}
              {currentUser?.role === 'learner' && matchesError && (
                <p role="alert" className="mt-5 text-sm text-red-300">{matchesError}</p>
              )}
              {currentUser?.role === 'learner' && applicationError && (
                <p role="alert" className="mt-3 text-sm text-red-300">{applicationError}</p>
              )}
              {currentUser?.role === 'learner' && applicationMessage && (
                <output className="mt-3 block text-sm text-emerald-300">{applicationMessage}</output>
              )}
              {currentUser?.role === 'learner' && !isLoadingMatches && !matchesError && opportunityMatches.length === 0 && (
                <p className="mt-5 text-sm text-slate-400">No active opportunities match your profile yet.</p>
              )}
              {currentUser?.role === 'learner' && opportunityMatches.length > 0 && (
                <ul className="mt-6 space-y-3">
                  {opportunityMatches.map((match) => (
                    <li key={match.id} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <p className="font-medium text-slate-100">{match.title}</p>
                          <p className="mt-1 text-sm text-slate-400">{match.company_name}</p>
                          <p className="mt-1 text-xs capitalize text-slate-500">
                            {[match.location, match.employment_type].filter(Boolean).join(' · ') || 'Details not provided'}
                          </p>
                        </div>
                        <span className="shrink-0 text-sm font-semibold tabular-nums text-amber-300">
                          {match.match_score.toFixed(0)}% match
                        </span>
                      </div>
                      {(() => {
                        const application = learnerApplications.find(
                          (item) => item.opportunity_id === match.id,
                        )
                        return application ? (
                          <p className="mt-3 text-xs capitalize text-emerald-300">
                            Application: {application.status}
                            {application.placement_date && ` · Placed ${new Date(application.placement_date).toLocaleDateString()}`}
                          </p>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleApplyToOpportunity(match)}
                            disabled={applyingOpportunityId === match.id}
                            className="mt-3 rounded-md border border-amber-400/50 px-3 py-2 text-xs font-semibold text-amber-200 hover:bg-amber-400/10 disabled:opacity-50"
                          >
                            {applyingOpportunityId === match.id ? 'Applying...' : 'Apply'}
                          </button>
                        )
                      })()}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
