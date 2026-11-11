from sqlalchemy import select
from app.models import Route, Stop, FareRule


def seed_demo(db):
    if db.scalar(select(Route.id).limit(1)):
        return
    route = Route(code='DEMO-01', name='Central → Lake • fictional training corridor', is_demo=True)
    db.add(route)
    db.flush()
    for position, names in enumerate([
        ('Central', 'ಕೇಂದ್ರ', 'केंद्र'), ('Market', 'ಮಾರುಕಟ್ಟೆ', 'बाज़ार'),
        ('College', 'ಕಾಲೇಜು', 'कॉलेज'), ('Hospital', 'ಆಸ್ಪತ್ರೆ', 'अस्पताल'),
        ('Lake', 'ಕೆರೆ', 'झील'),
    ]):
        db.add(Stop(route_id=route.id, position=position, name=names[0], name_kn=names[1], name_hi=names[2]))
    db.add_all([
        FareRule(route_id=route.id, category='standard', label='Standard demo', per_stage_paise=500, verification_required=False),
        FareRule(route_id=route.id, category='demo-concession', label='Demo concession (manual check)', per_stage_paise=250, verification_required=True),
    ])
    db.commit()
