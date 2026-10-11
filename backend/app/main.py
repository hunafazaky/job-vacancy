import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, extract, history
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Vacancy Image Parser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# IMPORTANT: an unhandled exception raised inside a route bypasses
# CORSMiddleware entirely (it propagates straight to Starlette's outer
# ServerErrorMiddleware), so the resulting 500 response has no
# Access-Control-Allow-Origin header — the browser then reports it as a
# CORS error, masking the real 500. Registering an exception handler here
# means FastAPI builds the response *inside* the middleware stack instead,
# so CORS headers are applied normally even on failure.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )


app.include_router(auth.router)
app.include_router(extract.router)
app.include_router(history.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
