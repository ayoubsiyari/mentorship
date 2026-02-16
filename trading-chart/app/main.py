from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .db import SessionLocal, engine
from .models import Base, User
from .routes import admin, auth, bootcamp, chart_pages, monitoring, newsletter, sessions
from .security import hash_password
from .settings import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    origins = [o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(admin.router)
    app.include_router(bootcamp.router)
    app.include_router(chart_pages.router)
    app.include_router(monitoring.router)
    app.include_router(newsletter.router)

    @app.on_event("startup")
    def _startup():
        Base.metadata.create_all(bind=engine)

        if settings.admin_email and settings.admin_password:
            with SessionLocal() as db:
                existing = db.execute(select(User).where(User.email == settings.admin_email.lower())).scalar_one_or_none()
                if not existing:
                    u = User(
                        name=settings.admin_name,
                        email=settings.admin_email.lower(),
                        password_hash=hash_password(settings.admin_password),
                        role="admin",
                        is_active=True,
                    )
                    db.add(u)
                    db.commit()

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
