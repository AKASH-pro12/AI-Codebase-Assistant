
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import Query
from pydantic import BaseModel

from app.database import db

from app.routes.codebase_routes.upload import (
    router as upload_router
)

from app.routes.codebase_routes.repository import (
    router as repository_router
)

from app.routes.codebase_routes.analysis import (
    router as analysis_router
)

from app.routes.codebase_routes.architecture import (
    router as architecture_router
)

from app.routes.codebase_routes.search import (
    router as search_router
)

from app.services.vector_search import search_similar_chunks
from app.services.llm import ask_llm, explain_file
from app.services.function_analyzer import analyze_python_file
from app.services.class_analyzer import analyze_python_classes
from app.services.api_route_analyzer import analyze_python_routes

from app.services.dependency_analyzer import (
    analyze_python_dependencies,
    resolve_local_dependencies
)
from app.services.relationship_analyzer import (
    build_repository_relationships
)

from app.services.architecture_analyzer import (
    build_architecture_context
)

router = APIRouter(
    prefix="/codebase",
    tags=["Codebase"]
)

router.include_router(
    upload_router
)

router.include_router(
    repository_router
)

router.include_router(
    analysis_router
)

router.include_router(
    architecture_router
)

router.include_router(
    search_router
)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    chat_history: list = []
    previous_sources: list = []



