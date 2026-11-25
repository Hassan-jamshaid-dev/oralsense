import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api import (
    assessments,
    auth,
    comparison,
    dashboard,
    exports,
    health,
    participants,
    protocol_details,
    protocol_library,
    protocol_versions,
    quality_review,
    studies,
    study_analytics,
    trial_analysis,
    workspace_settings,
    workspaces,
)
from app.config import get_settings
from app.errors import register_error_handlers
from app.http_security import (
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    BrowserSecurityMiddleware,
    reject_wildcard_allowed_hosts,
    reject_wildcard_cors_origins,
    reject_wildcard_trusted_proxies,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oralsense")


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.is_production and settings.registration_allowed:
        logger.warning(
            "ALLOW_REGISTRATION is enabled in production. Disable it unless open signup is intended."
        )

    app = FastAPI(
        title="OralSense API",
        version="0.1.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # CSRF is inner so CORS can still label the 403 for a browser preflighted POST.
    app.add_middleware(BrowserSecurityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=reject_wildcard_cors_origins(settings.cors_origin_list),
        allow_credentials=True,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=reject_wildcard_allowed_hosts(
            settings.allowed_host_list, production=settings.is_production
        ),
        www_redirect=False,
    )
    if settings.trust_forwarding:
        trusted_proxies = reject_wildcard_trusted_proxies(
            settings.trusted_proxy_ip_list, production=settings.is_production
        )
        if not trusted_proxies:
            raise RuntimeError("TRUST_FORWARDING=true requires at least one TRUSTED_PROXY_IPS entry.")
        # Outermost: rewrite scheme and client only when the peer is a listed proxy.
        # Uvicorn's middleware does not apply X-Forwarded-Host; Host stays the request Host.
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_proxies)

    register_error_handlers(app)

    for router in (
        health.router,
        auth.router,
        workspaces.router,
        # Member list only. Name and active context stay on workspaces.router.
        workspace_settings.router,
        dashboard.router,
        participants.router,
        comparison.router,
        assessments.router,
        # Details owns GET /protocols/{id}. The library router also declares that
        # path; registering details first keeps the detail contract.
        protocol_details.router,
        protocol_library.router,
        protocol_versions.router,
        studies.router,
        study_analytics.router,
        exports.router,
        trial_analysis.router,
        quality_review.router,
    ):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
