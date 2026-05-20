import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import log_json, setup_logging
from app.core.rate_limit import InMemoryRateLimitMiddleware
from app.orchestrator.scheduler import start_scheduler, stop_scheduler
from app import models  # noqa: F401

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    try:
        import sentry_sdk  # type: ignore

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=0.1,
        )
    except Exception as exc:  # pragma: no cover
        log_json(logger, logging.WARNING, 'sentry_init_failed', error=str(exc))

app = FastAPI(title=settings.app_name, debug=settings.app_debug)

trusted_hosts = [host.strip() for host in settings.trusted_hosts.split(',') if host.strip()]
if trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(',') if origin.strip()],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=[method.strip() for method in settings.cors_allow_methods.split(',') if method.strip()],
    allow_headers=[header.strip() for header in settings.cors_allow_headers.split(',') if header.strip()],
)
if settings.rate_limit_enabled:
    app.add_middleware(
        InMemoryRateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )


@app.middleware('http')
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get('x-request-id') or str(uuid4())
    start = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 2)
    response.headers['x-request-id'] = request_id
    log_json(
        logger,
        logging.INFO,
        'http_request',
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
        client_ip=request.client.host if request.client else None,
    )
    return response


@app.on_event('startup')
def startup_event():
    if settings.app_auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.orchestrator_scheduler_autostart:
        start_scheduler(profile_path=settings.orchestrator_profile_path)
    log_json(logger, logging.INFO, 'app_started', app_name=settings.app_name, env=settings.app_env)


@app.on_event('shutdown')
def shutdown_event():
    stop_scheduler()


@app.get('/health')
def health_check():
    return {'status': 'ok', 'service': settings.app_name}


@app.get('/health/live')
def liveness_check():
    return {'status': 'alive', 'service': settings.app_name}


@app.get('/health/ready')
def readiness_check():
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'status': 'ready', 'service': settings.app_name}
    except Exception as exc:
        return JSONResponse(status_code=503, content={'status': 'not_ready', 'detail': str(exc)})


app.include_router(api_router)
