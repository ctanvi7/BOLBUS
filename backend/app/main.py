from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.routes.api import router
from app.routes.speech import router as speech_router
from app.services.seed import seed_demo
from app.services.migrations import migrate


@asynccontextmanager
async def lifespan(app):
    migrate(engine)
    with SessionLocal() as db:
        seed_demo(db)
    yield


app = FastAPI(title='BOLBUS Demo API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=['GET', 'POST', 'PUT'], allow_headers=['Content-Type'])
app.include_router(router)
app.include_router(speech_router)


@app.exception_handler(StaleDataError)
@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc):
    return JSONResponse(status_code=409, content={'detail': 'Concurrent update. Refresh before retrying.'})


@app.exception_handler(OperationalError)
async def unavailable(request: Request, exc):
    return JSONResponse(status_code=503, content={'detail': 'Database unavailable. Keep your draft and retry.'})
