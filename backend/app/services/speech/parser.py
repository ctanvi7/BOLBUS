"""Conservative grammar extraction only. No fare/eligibility decisions or LLM."""
import re
from pydantic import BaseModel, Field
from app.services.route_engine import normalize, resolve, suggestions

NUMBERS = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,
    'ondu':1,'eradu':2,'mooru':3,'muru':3,'naalku':4,'aidu':5,'ಒಂದು':1,'ಎರಡು':2,'ಮೂರು':3,'ನಾಲ್ಕು':4,'ಐದು':5,
    'ek':1,'do':2,'teen':3,'char':4,'chaar':4,'paanch':5,'एक':1,'दो':2,'तीन':3,'चार':4,'पांच':5}
FILLERS = {'ticket','tickets','ಟಿಕೆಟ್','ಟಿಕೆಟ್ಗಳು','ಟಿಕೆಟ್‌ಗಳು','टिकट','to','ge','ke','ಗೆ','के','please','ಕೊಡಿ','beku','ಬೇಕು','ಕೊಡು'}


class ExtractedItem(BaseModel):
    destination: str
    destination_stop_id: int | None
    quantity: int | None = Field(default=None, ge=1, le=20)
    category: str | None = None
    unresolved: list[str]
    candidates: list[dict]


class Extraction(BaseModel):
    original_transcription: str
    items: list[ExtractedItem]
    parser: str = 'deterministic-v1'
    confidence: None = None


def parse(db, route_id, text):
    parts = re.split(r'[,;\n]+|\s+(?:and|mattu|ಹಾಗೂ|ಮತ್ತು|और)\s+', normalize(text))
    items = []
    for part in parts:
        if not part.strip():
            continue
        words = re.findall(r'[^\s.!?]+', part)
        quantities, destination_words, categories = [], [], []
        unresolved = []
        for word in words:
            if word in NUMBERS:
                quantities.append(NUMBERS[word])
            elif word.isdecimal():
                quantities.append(int(word))
            elif word in ('shakti','ಶಕ್ತಿ','शक्ति'):
                categories.append('shakti-demo')
            elif word in ('standard', 'ಸಾಮಾನ್ಯ', 'सामान्य'):
                categories.append('standard')
            elif word not in FILLERS:
                # Kannada destination suffix, e.g. ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ; no fuzzy name replacement.
                destination_words.append(re.sub(r'(?:ಗೆ)$', '', word).rstrip('‌'))
        quantity = quantities[0] if len(quantities) == 1 and 1 <= quantities[0] <= 20 else None
        if quantity is None:
            unresolved.append('Confirm passenger quantity (1–20).')
        if len(categories) > 1:
            unresolved.append('Confirm ticket category; multiple category words found.')
        category = categories[0] if len(categories) == 1 else None
        if category is None:
            unresolved.append('Choose a category; none was reliably stated.')
        destination = ' '.join(destination_words)
        result = resolve(db, route_id, destination)
        if result['status'] != 'resolved':
            unresolved.append(f"Destination {result['status']}; choose a route stop.")
        if any(w in words for w in ('not','no','ಬೇಡ','नहीं','cancel','change','instead')):
            unresolved.append('Correction or negation detected. Review the entire request manually.')
            quantity, category = None, None
            result['stop_id'] = None
        items.append(ExtractedItem(destination=destination, destination_stop_id=result['stop_id'], quantity=quantity,
            category=category, unresolved=unresolved, candidates=result['candidates'] or suggestions(db, route_id, destination)))
    return Extraction(original_transcription=text, items=items)
