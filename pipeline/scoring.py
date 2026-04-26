def compute_base_score(skill_score, exp_score, semantic_score, ats_score):
    weights = {
        "skills": 0.35,
        "experience": 0.20,
        "semantic": 0.30,
        "ats": 0.15
    }

    final = (
        skill_score * weights["skills"] +
        exp_score * weights["experience"] +
        semantic_score * weights["semantic"] +
        ats_score * weights["ats"]
    )

    return round(final * 100, 2)
