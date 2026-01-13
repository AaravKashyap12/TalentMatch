import spacy
import re
import nltk

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load('en_core_web_sm')

def clean_text(text):
    if not text:
        return ""
    
    text = text.lower()
    
    # Remove emails and http links
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove non-alphanumeric characters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    doc = nlp(text)
    
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.text.strip()]
    
    return " ".join(tokens)

