from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.routes.admin import router as admin_router
from app.routes.auth import customer_router as customer_auth_router
from app.routes.auth import router as auth_router
from app.routes.chef import router as chef_router
from app.routes.customer import router as customer_router
from app.routes.waitress import router as waitress_router
from app.services import seed_defaults
from sqlmodel import Session
from app.core.database import engine

settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(',') if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_defaults(session)
    yield


app = FastAPI(
    title=settings.app_name,
    version='1.0.0',
    description='API-first restaurant menu system with staff RBAC, QR onboarding, and OTP customer flows.',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health', tags=['health'])
def health_check() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(customer_auth_router, prefix=settings.api_prefix)
app.include_router(customer_router, prefix=settings.api_prefix)
app.include_router(chef_router, prefix=settings.api_prefix)
app.include_router(waitress_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
