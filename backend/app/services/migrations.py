"""Additive v2 migration; preserves existing requests and legacy fare catalogs."""
from sqlalchemy import inspect, text
from app.database import Base


def migrate(engine):
    Base.metadata.create_all(engine)
    additions = {
        'service_type': "VARCHAR NOT NULL DEFAULT 'ordinary'",
        'origin_text': 'VARCHAR', 'destination_text': 'VARCHAR',
        'documents_verified': 'BOOLEAN NOT NULL DEFAULT 0', 'quote_snapshot': 'VARCHAR',
    }
    with engine.begin() as connection:
        existing = {c['name'] for c in inspect(connection).get_columns('ticket_requests')}
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(text(f'ALTER TABLE ticket_requests ADD COLUMN {name} {definition}'))
