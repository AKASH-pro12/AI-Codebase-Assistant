
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.codebase import router as codebase_router
from app.routes.admin import router as admin_router


app = FastAPI(
    title="AI-Powered Codebase Assistant",
    description=(
        "Backend API for the AI-powered codebase analysis and chat application.\n\n"
        "## Authentication\n"
        "Use `POST /auth/login` to obtain an access token, then click the **Authorize** "
        "button above and enter the token under **HTTPBearer** (or log in via OAuth2PasswordBearer) "
        "to authenticate protected endpoints."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow Next.js dev server, Vercel deployments, and FRONTEND_URL
# ---------------------------------------------------------------------------
import os

frontend_url = os.getenv("FRONTEND_URL", "").strip()
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "https://ai-codebase-assistant-six.vercel.app",
]
if frontend_url:
    for u in frontend_url.split(","):
        clean = u.strip()
        if clean and clean not in allowed_origins:
            allowed_origins.append(clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(codebase_router)
app.include_router(admin_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "AI-Powered Codebase Assistant API is running",
        "docs": "/docs",
        "version": "1.0.0",
    }
