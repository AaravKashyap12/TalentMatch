from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


vectorizer = TfidfVectorizer(stop_words="english")


def semantic_similarity(text1, text2):
    try:
        vectors = vectorizer.fit_transform([text1, text2])
        score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        return float(score)
    except:
        return 0.5  # safe fallback
