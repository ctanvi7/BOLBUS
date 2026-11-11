from sqlalchemy import select
from app.models import Route, Stop, FareRule, FareTable, FareEntry, ConcessionRule, StopAlias


def seed_demo(db):
    if db.scalar(select(Route.id).limit(1)):
        seed_tables(db)
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
    seed_tables(db)


def seed_tables(db):
    # Upgrade only our explicitly synthetic corridor; never fabricate fares for other routes.
    route = db.scalar(select(Route).where(Route.code == 'DEMO-01', Route.is_demo.is_(True)))
    if route is not None and not db.scalar(select(FareRule.id).where(FareRule.route_id == route.id, FareRule.category == 'shakti-demo')):
        db.add(FareRule(route_id=route.id, category='shakti-demo', label='Shakti-style DEMO (manual checks)', per_stage_paise=0, verification_required=True))
        db.commit()
    if route is None or db.scalar(select(FareTable.id).where(FareTable.route_id == route.id)):
        return
    table = FareTable(route_id=route.id, version='synthetic-1', effective_date='2026-01-01',
        source='Synthetic BOLBUS training table; not an official BMTC fare or concession policy', is_demo=True)
    db.add(table); db.flush()
    stops = db.scalars(select(Stop).where(Stop.route_id == route.id).order_by(Stop.position)).all()
    for service, multiplier in [('ordinary', 1), ('express', 2)]:
        for category, rate in [('standard', 500), ('demo-concession', 250), ('shakti-demo', 0)]:
            for origin in stops:
                for destination in stops:
                    if destination.position > origin.position:
                        db.add(FareEntry(table_id=table.id, service_type=service, category=category,
                            boarding_stage=origin.position, destination_stage=destination.position,
                            unit_paise=(destination.position-origin.position)*rate*multiplier, concession_required=category != 'standard'))
            if category != 'standard':
                db.add(ConcessionRule(table_id=table.id, service_type=service, category=category,
                    label='Shakti-style DEMO — not official policy' if category == 'shakti-demo' else 'Synthetic reduced fare',
                    eligibility_check='Conductor must confirm applicability and eligibility for this demonstration rule.',
                    document_check='Conductor must confirm applicable documents were checked; store no numbers or photos.', is_demo=True))
    for stop in stops:
        db.add(StopAlias(stop_id=stop.id, alias=stop.name + ' stop'))
    db.commit()
