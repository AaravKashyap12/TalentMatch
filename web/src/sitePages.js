export const SITE_PAGES = [
  {
    path: '/privacy',
    label: 'Privacy',
    kicker: 'Privacy',
    title: 'How TalentMatch handles candidate data',
    intro: 'TalentMatch stores only the information needed to parse resumes, score candidates, and preserve hiring decisions for your workspace.',
    sections: [
      {
        title: 'What we store',
        body: 'Uploaded resumes, extracted skills, scoring results, and scan history are stored so hiring teams can reopen prior assessments and compare candidates over time.',
      },
      {
        title: 'How we use data',
        body: 'Candidate data is used only to produce ranking, explanations, ATS checks, and recruiter-facing summaries inside your workspace.',
      },
      {
        title: 'Access controls',
        body: 'Authenticated users can only access their own scans. Admin analytics are protected behind a separate secret and never exposed to regular candidate-review flows.',
      },
    ],
  },
  {
    path: '/terms',
    label: 'Terms',
    kicker: 'Terms',
    title: 'Usage terms for the TalentMatch workspace',
    intro: 'TalentMatch is intended for professional recruiting workflows. Users are responsible for the resumes they upload and the hiring decisions they make with the platform.',
    sections: [
      {
        title: 'Acceptable use',
        body: 'Do not upload data you do not have permission to process. Do not attempt to bypass scan limits, auth controls, or rate limits.',
      },
      {
        title: 'Scoring guidance',
        body: 'Rankings are decision support, not automatic hiring outcomes. Recruiters should review candidate evidence, experience, and legal obligations before acting.',
      },
      {
        title: 'Availability',
        body: 'We aim for stable service, but scan capacity, third-party auth, and AI-generated summaries can occasionally be degraded by upstream providers.',
      },
    ],
  },
  {
    path: '/docs',
    label: 'Docs',
    kicker: 'Docs',
    title: 'Using TalentMatch end to end',
    intro: 'TalentMatch is built for quick setup: define the role, add the job description, upload resumes, and review a ranked slate with explanations.',
    sections: [
      {
        title: 'Job description input',
        body: 'You can paste a JD directly or upload a plain text JD file. Text JDs are limited to 10,000 characters, and JD files are limited to 256 KB.',
      },
      {
        title: 'Resume uploads',
        body: 'Each scan accepts up to 20 PDF resumes. Individual PDFs are limited to 20 MB and must contain extractable text.',
      },
      {
        title: 'Workspace flow',
        body: 'Use Dashboard for recent activity, New Scan for fresh assessments, History for past scans, and Compare for side-by-side candidate review.',
      },
    ],
  },
  {
    path: '/status',
    label: 'Status',
    kicker: 'Status',
    title: 'Current platform status',
    intro: 'Core services are operating normally when authentication, resume parsing, scoring, and scan history are available without elevated error rates.',
    sections: [
      {
        title: 'Auth and sessions',
        body: 'Supabase sign-in is required for production workspaces. OAuth, email sign-in, and protected scan routes are expected to be available.',
      },
      {
        title: 'Scanning pipeline',
        body: 'Resume parsing, structured scoring, and candidate overview generation are monitored together because scan quality depends on all three staying healthy.',
      },
      {
        title: 'Operational limits',
        body: 'Rate limits and upload limits are enforced to protect the workspace from abuse and to keep shared scanning capacity responsive.',
      },
    ],
  },
]
