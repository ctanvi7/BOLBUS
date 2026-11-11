from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db, get_write_db
from app.models import TicketBatch
from app.schemas import Version
from app.schemas.batches import BatchCreate, BatchEdit, BatchPrepare
from app.services import batches

router = APIRouter(prefix='/api/batches', tags=['batches'])


@router.post('', status_code=201)
def create(data: BatchCreate, db: Session = Depends(get_write_db)):
    batch = batches.create(db, data)
    db.commit()
    return batches.output(db, batch)


@router.get('')
def listing(db: Session = Depends(get_db)):
    # Include completed history so finishing one batch never hides other pending work.
    return [batches.output(db, b) for b in db.scalars(select(TicketBatch).order_by(TicketBatch.created_at.desc()))]


@router.get('/{batch_id}')
def detail(batch_id: str, db: Session = Depends(get_db)):
    return batches.output(db, batches.get_batch(db, batch_id))


@router.put('/{batch_id}/items/{item_id}')
def edit(batch_id: str, item_id: str, data: BatchEdit, db: Session = Depends(get_write_db)):
    item = batches.get_item(db, batch_id, item_id)
    batches.guard(item, data.version)
    item.draft_json, item.last_error = data.draft.model_dump_json(), None
    # Force a revision even for an identical save to reject old editors deterministically.
    item.version += 1
    db.commit()
    return batches.output(db, batches.get_batch(db, batch_id))


@router.post('/{batch_id}/prepare')
def prepare(batch_id: str, data: BatchPrepare, db: Session = Depends(get_write_db)):
    result = batches.prepare(db, batches.get_batch(db, batch_id), data.versions)
    db.commit()
    return result


@router.post('/{batch_id}/items/{item_id}/cancel')
def cancel(batch_id: str, item_id: str, data: Version, db: Session = Depends(get_write_db)):
    item = batches.get_item(db, batch_id, item_id)
    batches.guard(item, data.version)
    item.cancelled = True
    db.commit()
    return batches.output(db, batches.get_batch(db, batch_id))
