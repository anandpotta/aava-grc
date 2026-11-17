"""AAVA GRC Intelligence — API entrypoint.

    uvicorn app.main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import access, ask, catalog, collab, changes, govern, maps
from app.core.config import settings

app = FastAPI(title=settings.app_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router, prefix=settings.api_prefix, tags=["catalog"])
app.include_router(maps.router, prefix=settings.api_prefix, tags=["compliance-maps"])
app.include_router(changes.router, prefix=settings.api_prefix, tags=["reg-change"])
app.include_router(ask.router, prefix=settings.api_prefix, tags=["ask-aava"])
app.include_router(govern.router, prefix=settings.api_prefix, tags=["scope-assess-act"])
app.include_router(access.router, prefix=settings.api_prefix, tags=["access"])
app.include_router(collab.router, prefix=settings.api_prefix, tags=["stakeholders"])


@app.middleware("http")
async def actor(request: Request, call_next):
    """Record who is acting, so every audit entry names a person and a role."""
    from app.services import access_service, store
    u = access_service.user(request.headers.get("x-aava-user"))
    store.ACTOR.set((u["id"], f'{u["name"]} ({access_service.ROLES[u["role"]]["name"]})'))
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.version}
