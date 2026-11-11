import unicodedata
from sqlalchemy import select
from app.models import Stop, StopAlias


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def resolve(db, route_id, query):
    key = normalize(query)
    stops = db.scalars(select(Stop).where(Stop.route_id == route_id)).all()
    aliases = db.execute(select(StopAlias.stop_id, StopAlias.alias).join(Stop, Stop.id == StopAlias.stop_id).where(Stop.route_id == route_id)).all()
    matches = {s.id for s in stops if key and key in {normalize(s.name), normalize(s.name_kn), normalize(s.name_hi)}}
    matches.update(stop_id for stop_id, alias in aliases if key and normalize(alias) == key)
    return {'status': 'resolved' if len(matches) == 1 else 'ambiguous' if matches else 'unknown',
            'stop_id': next(iter(matches)) if len(matches) == 1 else None,
            'candidates': [{'id': s.id, 'name': s.name} for s in stops if s.id in matches]}


def suggestions(db, route_id, query, limit=3):
    """Suggestions are UI choices only; never feed them back into automatic resolution."""
    from difflib import SequenceMatcher
    result = resolve(db, route_id, query)
    if result['status'] == 'ambiguous':
        return result['candidates'][:limit]
    key = normalize(query)
    if not key or result['status'] == 'resolved':
        return []
    stops = db.scalars(select(Stop).where(Stop.route_id == route_id)).all()
    aliases = db.execute(select(StopAlias.stop_id, StopAlias.alias).join(Stop, Stop.id == StopAlias.stop_id).where(Stop.route_id == route_id)).all()
    ranked = []
    for stop in stops:
        names = [stop.name, stop.name_kn, stop.name_hi] + [a for stop_id, a in aliases if stop_id == stop.id]
        score = max(SequenceMatcher(None, key, normalize(name)).ratio() for name in names)
        if score >= 0.45:
            ranked.append((score, stop))
    ranked.sort(key=lambda entry: (-entry[0], entry[1].position))
    return [{'id': stop.id, 'name': stop.name} for _, stop in ranked[:limit]]
