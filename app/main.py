from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.codebase import router as codebase_router

app = FastAPI(
    title="AI-Powered Codebase Assistant",
    description="Backend API for the AI-powered codebase analysis and chat application.",
    version="1.0.0"
)

app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "AI-Powered Codebase Assistant API is running"
    }


app = FastAPI(
    title="AI-Powered Codebase Assistant",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(codebase_router)