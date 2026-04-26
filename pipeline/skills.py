import re

# ── Skills Database (moved from ml.matcher to avoid circular imports) ────────

SKILLS_SEED = {
    # Languages
    "python","java","c++","c#","javascript","typescript","go","rust","swift",
    "kotlin","php","ruby","scala","r","matlab","perl","bash","shell","dart",
    "elixir","haskell","lua","groovy","assembly","sql","html","css",
    # Web
    "react","angular","vue","svelte","next.js","nuxt","gatsby","remix",
    "tailwind","tailwindcss","bootstrap","sass","scss","webpack","vite","jquery",
    # Backend
    "node.js","express","nestjs","django","flask","fastapi","spring boot",
    "spring","rails","laravel","asp.net","graphql","grpc","websocket","trpc",
    "rest api","restful api","api design","backend framework",
    # Databases
    "mongodb","postgresql","mysql","sqlite","redis","cassandra","dynamodb","nosql database",
    "firebase","supabase","neo4j","oracle","snowflake","bigquery","dbt",
    "prisma","typeorm","sequelize","mongoose","drizzle","sqlalchemy",
    # Cloud / DevOps
    "aws","azure","gcp","cloud platform","docker","containerization","kubernetes","k8s","terraform","ansible",
    "jenkins","github actions","gitlab ci","ci/cd","linux","nginx","apache",
    "cloudformation","helm","prometheus","grafana","datadog","elasticsearch",
    "kafka","rabbitmq","celery","sqs","pubsub","messaging system","vercel","netlify","render",
    "neon","upstash","planetscale",
    # ML / AI
    "tensorflow","pytorch","keras","scikit-learn","pandas","numpy","scipy",
    "matplotlib","seaborn","xgboost","lightgbm","hugging face","huggingface",
    "transformers","langchain","openai","llm","rag","embeddings","mlflow",
    "airflow","spark","hadoop","data processing","event streaming","tableau","power bi","streamlit","jupyter",
    "groq","ollama","pinecone","weaviate","qdrant","chroma",
    # Mobile
    "android","ios","react native","flutter",
    # Testing
    "pytest","jest","selenium","cypress","playwright","vitest",
    # CS fundamentals
    "data structures","algorithms","data structures and algorithms","system design","oop","object oriented",
    "design patterns","microservices","distributed systems",
    # Security
    "oauth","jwt","ssl","tls",
    # Misc modern
    "socket.io","zod","zustand","redux","stripe","razorpay",
    "cashfree","twilio","sendgrid","resend","clerk","auth0","nextauth",
    "git","github","gitlab","jira","agile","scrum","kanban",
}

SKILL_ALIASES = {
    "k8s": "kubernetes",
    "reactjs": "react",
    "react.js": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "nextjs": "next.js",
    "next.js": "next.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "golang": "go",
    "t-sql": "sql",
    "rest apis": "rest api",
    "restful apis": "rest api",
    "api design principles": "api design",
    "backend frameworks": "backend framework",
    "similar backend frameworks": "backend framework",
    "version control": "git",
    "version control systems": "git",
    "cloud platforms": "cloud platform",
    "cloud provider": "cloud platform",
    "cloud providers": "cloud platform",
    "containers": "containerization",
    "container orchestration": "containerization",
    "linux environment": "linux",
    "linux environments": "linux",
    "microservices architecture": "microservices",
    "microservices-based architecture": "microservices",
    "microservices based architecture": "microservices",
    "distributed system": "distributed systems",
    "data structures and algorithms": "data structures",
    "dsa": "data structures",
    "database systems": "sql",
    "messaging systems": "messaging system",
    "messaging queues": "messaging system",
    "message queues": "messaging system",
    "event-driven systems": "messaging system",
    "event driven systems": "messaging system",
    "nosql databases": "nosql database",
}

# ── Skill Synonyms (Normalization) ─────────────────────────────

SKILL_SYNONYMS = {
    "javascript": ["js", "node", "nodejs"],
    "python": ["py"],
    "machine learning": ["ml", "deep learning"],
    "react": ["reactjs"],
    "c++": ["cpp"],
    "html": ["html5"],
    "css": ["css3"],
    "rest api": ["rest apis", "restful api", "restful apis", "api development"],
    "api design": ["api design principles"],
    "git": ["version control", "version control systems"],
    "cloud platform": ["cloud platforms", "cloud provider", "cloud providers"],
    "docker": ["containerization", "containers"],
    "backend framework": ["backend frameworks", "backend frameworks"],
    "linux": ["linux environment", "linux environments"],
    "microservices": ["microservices architecture", "microservices-based architecture"],
    "distributed systems": ["distributed system"],
    "data structures": ["data structures and algorithms", "dsa"],
    "messaging system": ["messaging systems", "messaging queue", "messaging queues", "message queue", "message queues"],
    "nosql database": ["nosql databases"],
}

SKILL_GROUPS = {
    "backend framework": {
        "fastapi", "flask", "django", "express", "nestjs", "spring boot",
        "spring", "rails", "laravel", "asp.net", "node.js",
    },
    "rest api": {
        "rest api", "api design", "fastapi", "flask", "django", "express",
        "nestjs", "spring boot", "rails", "laravel", "node.js",
    },
    "api design": {
        "api design", "rest api", "fastapi", "flask", "django", "express",
        "nestjs", "spring boot", "rails", "laravel", "node.js",
    },
    "git": {"git", "github", "gitlab", "github actions", "gitlab ci"},
    "cloud platform": {"cloud platform", "aws", "gcp", "azure"},
    "containerization": {"containerization", "docker", "kubernetes"},
    "microservices": {"microservices", "distributed systems", "kafka", "event streaming"},
    "messaging system": {"messaging system", "kafka", "rabbitmq", "celery", "sqs", "pubsub", "event streaming"},
    "nosql database": {"nosql database", "mongodb", "cassandra", "dynamodb", "redis", "firebase"},
    "data structures": {"data structures", "algorithms"},
    "data processing": {
        "data processing", "spark", "hadoop", "pandas", "airflow",
        "kafka", "event streaming", "distributed systems", "redis",
    },
}

# ── Blacklist: Garbage skills that should NOT be extracted from JD ─────────

INVALID_SKILLS = {
    "ai/ml jd",
    "vertexflow labs",
    "edge",
    "ui",
    # Add more as needed
}

# ── Skill Inference Graph ─────────────────────────────────────
#
# Format: "skill_on_resume": { "skill_implied": confidence_weight }
#
# Rules:
#   1.0 = near-certain implication (e.g. react → javascript)
#   0.9 = very strong (e.g. react → html, css)
#   0.8 = strong
#   0.7 = likely but not guaranteed
#
# Each entry means: "if the candidate has KEY, they almost certainly know VALUE."

SKILL_INFERENCE = {
    # ── Frontend frameworks → web fundamentals ──────────────────────────────
    "react":        {"javascript": 1.0, "html": 0.9, "css": 0.9},
    "next.js":      {"react": 1.0, "javascript": 1.0, "html": 0.9, "css": 0.9},
    "angular":      {"javascript": 1.0, "typescript": 0.9, "html": 0.9, "css": 0.9},
    "vue":          {"javascript": 1.0, "html": 0.9, "css": 0.9},
    "svelte":       {"javascript": 1.0, "html": 0.9, "css": 0.9},
    "nuxt":         {"vue": 1.0, "javascript": 1.0, "html": 0.9, "css": 0.9},
    "gatsby":       {"react": 1.0, "javascript": 1.0, "html": 0.9, "css": 0.9},
    "remix":        {"react": 1.0, "javascript": 1.0, "html": 0.9, "css": 0.9},

    # ── CSS tooling → css ────────────────────────────────────────────────────
    "tailwind":     {"css": 0.9, "html": 0.8},
    "tailwindcss":  {"css": 0.9, "html": 0.8},
    "bootstrap":    {"css": 0.9, "html": 0.8},
    "sass":         {"css": 1.0},
    "scss":         {"css": 1.0, "sass": 0.9},
    "jquery":       {"javascript": 1.0, "html": 0.9, "css": 0.8},

    # ── TypeScript → JavaScript ──────────────────────────────────────────────
    "typescript":   {"javascript": 1.0},

    # ── Node / Backend JS → JavaScript ──────────────────────────────────────
    "node.js":      {"javascript": 1.0},
    "express":      {"node.js": 1.0, "javascript": 1.0},
    "express":      {"node.js": 1.0, "javascript": 1.0, "rest api": 0.9, "backend framework": 0.8},
    "nestjs":       {"node.js": 1.0, "typescript": 0.9, "javascript": 1.0},
    "trpc":         {"typescript": 0.9, "javascript": 1.0},

    # ── Python frameworks → Python ────────────────────────────────────────────
    "django":       {"python": 1.0, "sql": 0.8, "rest api": 0.9, "backend framework": 1.0},
    "flask":        {"python": 1.0, "rest api": 0.9, "backend framework": 1.0},
    "fastapi":      {"python": 1.0, "rest api": 1.0, "backend framework": 1.0},

    # ── JVM / JDK adjacent ───────────────────────────────────────────────────
    "spring boot":  {"java": 1.0, "spring": 1.0},
    "spring":       {"java": 1.0},

    # ── Ruby on Rails → Ruby ─────────────────────────────────────────────────
    "rails":        {"ruby": 1.0, "sql": 0.8},

    # ── PHP frameworks → PHP ─────────────────────────────────────────────────
    "laravel":      {"php": 1.0},

    # ── Mobile ───────────────────────────────────────────────────────────────
    "react native": {"react": 0.9, "javascript": 1.0},
    "flutter":      {"dart": 1.0},

    # ── ORM / DB clients → SQL ────────────────────────────────────────────────
    "postgresql":   {"sql": 1.0},
    "mysql":        {"sql": 1.0},
    "sqlite":       {"sql": 1.0},
    "prisma":       {"sql": 0.8, "node.js": 0.7},
    "typeorm":      {"sql": 0.9, "typescript": 0.8},
    "sequelize":    {"sql": 0.9, "node.js": 0.8},
    "sqlalchemy":   {"sql": 0.9, "python": 1.0},
    "mongoose":     {"mongodb": 1.0, "node.js": 0.8},

    # ── Cloud providers → related tools ──────────────────────────────────────
    "aws":          {"linux": 0.7},
    "gcp":          {"linux": 0.7, "cloud platform": 1.0},
    "azure":        {"linux": 0.7, "cloud platform": 1.0},
    "aws":          {"linux": 0.7, "cloud platform": 1.0},

    # ── Container orchestration ───────────────────────────────────────────────
    "kubernetes":   {"docker": 0.9},
    "docker":       {"containerization": 1.0},
    "helm":         {"kubernetes": 1.0, "docker": 0.9},

    # ── Data / ML stack ───────────────────────────────────────────────────────
    "pytorch":      {"python": 1.0, "numpy": 0.9},
    "tensorflow":   {"python": 1.0, "numpy": 0.9},
    "keras":        {"python": 1.0, "tensorflow": 0.8},
    "scikit-learn": {"python": 1.0, "numpy": 0.9, "pandas": 0.9},
    "pandas":       {"python": 1.0, "numpy": 0.9},
    "spark":        {"data processing": 1.0, "distributed systems": 0.8},
    "hadoop":       {"data processing": 1.0, "distributed systems": 0.8},
    "kafka":        {"event streaming": 1.0, "distributed systems": 0.9, "microservices": 0.85, "data processing": 0.6},
    "redis":        {"distributed systems": 0.6, "microservices": 0.55, "data processing": 0.45},
    "event streaming": {"data processing": 0.6, "distributed systems": 0.75},
    "distributed systems": {"microservices": 0.85, "data processing": 0.6},
    "microservices": {"distributed systems": 0.75},
    "numpy":        {"python": 1.0},
    "langchain":    {"python": 1.0, "llm": 0.9},

    # ── Testing frameworks → language ─────────────────────────────────────────
    "pytest":       {"python": 1.0},
    "jest":         {"javascript": 1.0},
    "vitest":       {"javascript": 1.0},
    "cypress":      {"javascript": 1.0},
    "playwright":   {"javascript": 0.9},

    # ── Auth / API tools ──────────────────────────────────────────────────────
    "nextauth":     {"next.js": 1.0, "javascript": 1.0},
    "clerk":        {"javascript": 0.8},
    "github":       {"git": 1.0},
    "gitlab":       {"git": 1.0},
    "github actions": {"git": 1.0, "ci/cd": 1.0},
    "gitlab ci":    {"git": 1.0, "ci/cd": 1.0},
}


# ── Normalization ─────────────────────────────────────────────

def normalize_skill(skill):
    skill = skill.lower().strip()
    skill = SKILL_ALIASES.get(skill, skill)

    for main, variants in SKILL_SYNONYMS.items():
        if skill == main or skill in variants:
            return main

    return skill


def extract_skills(skill_list):
    return list(set(normalize_skill(s) for s in skill_list))


# ── JD Skill Extraction ───────────────────────────────────────
#
# PRIMARY:  Match against SKILLS_SEED (curated, precision-first).
# FALLBACK: If a word/phrase in the JD looks like a skill but isn't in the
#           seed, capture it as an "unknown skill" so it isn't silently
#           dropped.  This handles brand-new frameworks, niche tools, etc.

_UNKNOWN_SKILL_BLOCKLIST = {
    "years", "experience", "team", "strong", "good", "ability", "knowledge",
    "understanding", "minimum", "required", "preferred", "familiarity",
    "excellent", "proficient", "bonus", "plus", "candidate", "role",
    "position", "hire", "hiring", "communication", "problem", "solving",
    "collaborative", "analytical", "detail", "oriented", "motivated",
    "opportunity", "responsibilities", "requirements", "qualifications",
    "we", "you", "our", "their", "this", "that", "with", "and", "the",
    "for", "in", "of", "to", "a", "an", "is", "are", "be", "have", "has",
    "will", "can", "may", "must", "should", "work", "working", "use",
    "using", "build", "building", "design", "develop", "developing",
    "implement", "write", "written", "manage", "managing", "support",
    "maintain", "maintaining",
}

def _looks_like_skill_token(original_token: str) -> bool:
    """
    Heuristic: does this JD token look like a skill name we don't know yet?

    IMPORTANT: pass the *original* casing — we use the lowercase only for
    blocklist checks, but rely on the original form to detect CamelCase /
    mixed-case patterns (e.g. "SvelteKit", "SolidJS", "TanStack").
    """
    t_lower = original_token.lower().strip()
    t_orig  = original_token.strip()

    if len(t_lower) < 2 or len(t_lower) > 40:
        return False
    if t_lower in _UNKNOWN_SKILL_BLOCKLIST:
        return False
    if t_lower in INVALID_SKILLS:
        return False
    if not t_lower[0].isalpha():
        return False

    # If the original token has any uppercase, digit, dot, or hyphen it's
    # almost certainly a proper name / tool identifier, not common English.
    has_structure = bool(re.search(r"[A-Z0-9.\-]", t_orig))
    if has_structure:
        return True

    # Pure lowercase: likely an English word unless it's a short acronym.
    return len(t_lower) <= 5


def extract_jd_skills(jd_text: str):
    """
    Extract skills from JD text.

    Strategy
    --------
    1. Seed matching  — scan SKILLS_SEED with word-boundary regex (high precision).
    2. Synonym matching — also catch synonym variants that map to a seed skill.
    3. Unknown-skill detection — tokenise the JD and flag CamelCase / acronym /
       hyphenated identifiers that weren't matched in step 1/2.  These are
       returned with an "unknown:" prefix so callers can treat them differently
       (e.g. surface a warning in the UI, add them to the seed for future runs).

    Returns a sorted list where:
      • Normal skills  → plain string, e.g. "react"
      • Unknown skills → prefixed string, e.g. "unknown:SomeCoolFramework"
    """
    jd_lower = jd_text.lower()
    found = set()

    # ── Step 1: seed matching ──────────────────────────────────
    for skill in SKILLS_SEED:
        skill_lower = skill.lower()
        if re.search(r'\b' + re.escape(skill_lower) + r'\b', jd_lower):
            found.add(skill_lower)

    # ── Step 2: synonym matching ───────────────────────────────
    for main, variants in SKILL_SYNONYMS.items():
        if main in found:
            continue
        if re.search(r'\b' + re.escape(main.lower()) + r'\b', jd_lower):
            found.add(main.lower())
            continue
        for v in variants:
            if re.search(r'\b' + re.escape(v.lower()) + r'\b', jd_lower):
                found.add(main.lower())
                break

    # ── Step 3: filter garbage ────────────────────────────────
    # Collapse example lists into requirement concepts. In "backend frameworks
    # (e.g., Flask, Django, FastAPI)", any one framework satisfies the need.
    if re.search(r"\bbackend\s+frameworks?\b", jd_lower):
        found.difference_update(SKILL_GROUPS["backend framework"])
        found.add("backend framework")
    if re.search(r"\brest(?:ful)?\s+apis?\b", jd_lower):
        found.add("rest api")
    if re.search(r"\bversion\s+control(?:\s+systems?)?\b", jd_lower):
        found.add("git")
    if re.search(r"\bcloud\s+(?:platforms?|providers?)\b", jd_lower):
        found.difference_update({"aws", "gcp", "azure"})
        found.add("cloud platform")
    if re.search(r"\bnosql\s+databases?\b", jd_lower):
        found.difference_update({"mongodb", "cassandra", "dynamodb", "firebase"})
        found.add("nosql database")
    if re.search(r"\bmessaging\s+(?:systems?|queues?)\b", jd_lower):
        found.difference_update({"kafka", "rabbitmq", "celery", "sqs", "pubsub"})
        found.add("messaging system")
    if re.search(r"\bdata\s+processing\b", jd_lower):
        found.add("data processing")

    found = {s for s in found if s not in INVALID_SKILLS}

    # ── Step 4: unknown skill detection ──────────────────────
    unknown = set()
    token_pattern = re.compile(
        r'\b('
        r'[A-Z][a-zA-Z0-9]*(?:[.\-][a-zA-Z0-9]+)+'   # dotted/hyphenated: Node.js, scikit-learn
        r'|[A-Z]{2,6}'                                  # acronyms: SQL, AWS, API
        r'|[A-Z][a-z]+[A-Z][a-zA-Z0-9]*'               # CamelCase: GraphQL, GitHub
        r'|[a-zA-Z][a-zA-Z0-9]*\d[a-zA-Z0-9]*'         # has digit: ES6, H2
        r')\b'
    )
    for m in token_pattern.finditer(jd_text):
        token = m.group(1)
        token_lower = token.lower()
        normalized_token = normalize_skill(token_lower)
        if token_lower in found:
            continue
        if normalized_token in found:
            continue
        if any(normalized_token in group for group in SKILL_GROUPS.values()):
            continue
        if token_lower in {"api", "apis", "rest", "ci", "cd"}:
            continue
        resolved = SKILL_ALIASES.get(token_lower)
        if resolved:
            found.add(resolved)
            continue
        if _looks_like_skill_token(token):  # pass original casing
            unknown.add(f"unknown:{token}")

    result = sorted(found) + sorted(unknown)
    return result


# ── Skill Matching with Inference ─────────────────────────────

def _strip_noise_sections(text: str) -> str:
    return re.split(
        r"(?im)^\s*(?:#+\s*)?(?:hidden\s+testing\s+angles|testing\s+angles|important)\b.*$",
        text,
        maxsplit=1,
    )[0]


def _extract_section(text: str, start_patterns: list[str], stop_patterns: list[str]) -> str:
    start_re = "|".join(start_patterns)
    stop_re = "|".join(stop_patterns)
    heading_prefix = r"\s*(?:#+\s*)?(?:[*-]\s*)?(?:[^\w\r\n]{0,8}\s*)?"
    match = re.search(rf"(?im)^{heading_prefix}(?:{start_re})\s*:?\s*$", text)
    if not match:
        return ""
    rest = text[match.end():]
    stop = re.search(rf"(?im)^{heading_prefix}(?:{stop_re})\s*:?\s*$", rest)
    return rest[:stop.start()] if stop else rest


def extract_jd_skill_tiers(
    jd_text: str,
    explicit_required: list[str] | None = None,
    explicit_preferred: list[str] | None = None,
) -> dict[str, list[str]]:
    """
    Extract JD skills into tiers so preferred examples do not become hard gaps.

    Explicit UI tags are honored. If absent, common headings such as
    "Required Skills" and "Preferred / Good-to-Have" drive classification.
    Responsibilities/role context are implicit signal only.
    """
    clean = _strip_noise_sections(jd_text)

    required_text = _extract_section(
        clean,
        [
            r"required(?:\s+skills)?",
            r"must[-\s]*have(?:\s+skills)?",
            r"requirements",
            r"core\s+skills",
        ],
        [
            r"preferred.*",
            r"good[-\s]*to[-\s]*have.*",
            r"nice[-\s]*to[-\s]*have.*",
            r"qualifications?",
            r"responsibilities",
            r"hidden.*",
        ],
    )
    preferred_text = _extract_section(
        clean,
        [
            r"preferred.*",
            r"good[-\s]*to[-\s]*have.*",
            r"nice[-\s]*to[-\s]*have.*",
        ],
        [
            r"qualifications?",
            r"responsibilities",
            r"required.*",
            r"hidden.*",
        ],
    )
    responsibilities_text = _extract_section(
        clean,
        [r"responsibilities", r"about\s+the\s+role"],
        [
            r"required.*",
            r"preferred.*",
            r"good[-\s]*to[-\s]*have.*",
            r"qualifications?",
            r"hidden.*",
        ],
    )

    explicit_req = {normalize_skill(s) for s in (explicit_required or []) if s}
    explicit_pref = {normalize_skill(s) for s in (explicit_preferred or []) if s}

    required = set(extract_jd_skills(required_text if required_text else clean))
    preferred = set(extract_jd_skills(preferred_text)) if preferred_text else set()
    implicit = set(extract_jd_skills(responsibilities_text)) if responsibilities_text else set()

    required |= explicit_req
    preferred |= explicit_pref

    preferred -= required
    implicit -= required
    implicit -= preferred

    role_context = {
        "software engineer", "backend developer", "backend engineer",
        "full stack developer", "data systems",
    }
    required -= role_context
    preferred -= role_context
    implicit -= role_context

    return {
        "required": sorted(required),
        "preferred": sorted(preferred),
        "implicit": sorted(implicit),
    }


def match_skills(candidate_skills, jd_skills):
    """
    Compare candidate skills against JD skills, using the inference graph
    to credit implied skills.

    Supports two-hop inference chains (e.g. next.js → react → html/css).

    Returns
    -------
    {
        "matched_skills":    [...],  # explicitly listed by candidate
        "inferred_skills":   [...],  # not listed but provably implied
        "missing_skills":    [...],  # genuinely not known
        "unknown_jd_skills": [...],  # JD mentions skills not in our seed
        "inference_weights": {...},  # skill → best confidence weight
    }
    """
    candidate_skills = extract_skills(candidate_skills)

    # Separate known vs unknown JD skills
    known_jd = []
    seen_known_jd = set()
    unknown_jd = []
    for s in jd_skills:
        if isinstance(s, str) and s.startswith("unknown:"):
            unknown_jd.append(s)
        else:
            normalized = normalize_skill(s)
            if normalized not in seen_known_jd:
                seen_known_jd.add(normalized)
                known_jd.append(normalized)

    # ── Build expanded skill set via inference (2-pass for chains) ───────────
    expanded = set(candidate_skills)
    inferred_weights: dict = {}

    for _pass in range(2):
        for skill in list(expanded):
            if skill in SKILL_INFERENCE:
                for implied_skill, weight in SKILL_INFERENCE[skill].items():
                    if implied_skill not in expanded:
                        inferred_weights[implied_skill] = max(
                            inferred_weights.get(implied_skill, 0), weight
                        )
                        expanded.add(implied_skill)

    # ── Classify each JD skill ────────────────────────────────
    def group_weight(skill_norm: str) -> float:
        group = SKILL_GROUPS.get(skill_norm)
        if not group:
            return 0.0
        return 1.0 if expanded & group else 0.0

    matched = []
    inferred_only = []
    missing = []

    for skill in known_jd:
        skill_norm = normalize_skill(skill)
        if skill_norm in candidate_skills:
            matched.append(skill_norm)
        elif skill_norm in inferred_weights:
            inferred_only.append(skill_norm)
        elif group_weight(skill_norm):
            inferred_weights[skill_norm] = max(inferred_weights.get(skill_norm, 0), group_weight(skill_norm))
            inferred_only.append(skill_norm)
        else:
            missing.append(skill_norm)

    return {
        "matched_skills":    matched,
        "inferred_skills":   inferred_only,
        "missing_skills":    missing,
        "unknown_jd_skills": unknown_jd,
        "inference_weights": inferred_weights,
    }


# ── Updated Score Function ────────────────────────────────────

def skill_match_score(candidate_skills, jd_skills):
    result = match_skills(candidate_skills, jd_skills)

    matched = result["matched_skills"]
    inferred = result["inference_weights"]

    # Only score against *known* JD skills (unknown ones are flagged, not penalised)
    known_jd = {
        normalize_skill(s)
        for s in jd_skills
        if isinstance(s, str) and not s.startswith("unknown:")
    }

    score = len(matched)
    for skill in result["inferred_skills"]:
        score += inferred.get(skill, 0)

    if not known_jd:
        return 0.0

    return score / len(known_jd)


# ── Updated Missing Skills ────────────────────────────────────

def identify_missing_skills(candidate_skills, jd_skills):
    """
    Returns only genuinely missing skills — skills the JD requires that the
    candidate neither listed nor can be inferred to know.
    Unknown/new skills from the JD are available via match_skills() directly.
    
    """
    result = match_skills(candidate_skills, jd_skills)
    return result["missing_skills"]
