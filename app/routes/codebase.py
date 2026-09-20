
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

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    chat_history: list = []
    previous_sources: list = []






@router.get("/architecture")
def get_repository_architecture():

    codebase = db.codebases.find_one(
        {},
        {
            "_id": 0,
            "codebase_name": 1,
            "files": 1
        },
        sort=[
            ("created_at", -1)
        ]
    )

    if not codebase:

        raise HTTPException(
            status_code=404,
            detail="No processed codebase found"
        )

    repository_files = codebase.get(
        "files",
        []
    )

    technologies = []

    technology_rules = {
        "Python": {".py"},
        "JavaScript": {".js", ".jsx"},
        "TypeScript": {".ts", ".tsx"},
        "HTML": {".html"},
        "CSS": {".css"},
        "Java": {".java"},
        "C/C++": {".c", ".cpp", ".h"},
        "SQL": {".sql"},
        "Markdown": {".md"},
        "JSON": {".json"}
    }

    for technology, extensions in technology_rules.items():

        evidence = []

        for file_data in repository_files:

            extension = file_data.get(
                "extension",
                ""
            ).lower()

            if extension in extensions:

                evidence.append(
                    extension
                )

        evidence = sorted(
            set(evidence)
        )

        if evidence:

            technologies.append({
                "name": technology,
                "evidence": evidence
            })


    routes = []

    for file_data in repository_files:

        extension = file_data.get(
            "extension",
            ""
        ).lower()

        if extension != ".py":
            continue

        stored_file_path = file_data.get(
            "file_path"
        )

        if not stored_file_path:
            continue

        try:

            file_routes = analyze_python_routes(
                stored_file_path
            )

        except ValueError:

            continue

        for route in file_routes:

            route_with_file = {
                **route,
                "file_path": file_data.get(
                    "relative_path"
                )
            }

            routes.append(
                route_with_file
            )


    repository_filesystem_paths = []

    for file_data in repository_files:

        repository_file = file_data.get(
            "file_path"
        )

        if repository_file:

            repository_filesystem_paths.append(
                repository_file
            )


    all_dependencies = []

    for repository_file in repository_filesystem_paths:

        if not repository_file.lower().endswith(
            ".py"
        ):
            continue

        try:

            dependencies = analyze_python_dependencies(
                repository_file
            )

            local_dependencies = resolve_local_dependencies(
                file_path=repository_file,
                dependencies=dependencies,
                repository_files=repository_filesystem_paths
            )

            all_dependencies.extend(
                local_dependencies
            )

        except ValueError:

            continue


    relationships = build_repository_relationships(
        all_dependencies
    )


    architecture_context = build_architecture_context(
        repository_files=repository_files,
        technologies=technologies,
        routes=routes,
        relationships=relationships
    )


    prompt = f"""
You are an AI Codebase Assistant.

Explain the architecture of the provided software repository.

Use ONLY the architecture information provided below.

Do not invent:
- files
- frameworks
- databases
- services
- routes
- components
- relationships
- functionality

If the provided information is insufficient to determine something,
clearly state that it cannot be determined from the available
architecture information.

Explain the architecture in a developer-friendly way.

Include:

1. Overall Architecture
2. Main Technologies
3. Important Components
4. API / Route Layer
5. File Relationships
6. Application Flow

Keep the explanation clear and focused.

ARCHITECTURE INFORMATION:

{architecture_context}

FINAL ANSWER:
"""


    answer = ask_llm(
        question=prompt,
        context=architecture_context,
        chat_history=[]
    )


    return {
        "codebase_name": codebase.get(
            "codebase_name"
        ),
        "total_files": len(repository_files),
        "total_routes": len(routes),
        "total_relationships": len(relationships),
        "architecture": answer
    }


@router.post("/search")
def search_codebase(request: SearchRequest):

    search_query = request.query

    if request.chat_history:

        previous_messages = []

        for message in request.chat_history[-6:]:

            role = message.get("role", "")
            content = message.get("content", "")

            if content:

                previous_messages.append(
                    f"{role}: {content}"
                )

        if previous_messages:

            search_query = (
                "\n".join(previous_messages)
                + "\n"
                + request.query
            )

    if request.previous_sources:

        previous_files = list(
            dict.fromkeys(
                request.previous_sources
            )
        )

        python_files = [
            file_path
            for file_path in previous_files
            if file_path.lower().endswith(".py")
        ]

        if python_files:
            previous_file = python_files[0]
        else:
            previous_file = previous_files[0]

        results = list(
            db.code_chunks.find(
                {
                    "file_path": previous_file
                },
                {
                    "_id": 0,
                    "file_path": 1,
                    "extension": 1,
                    "chunk_index": 1,
                    "content": 1
                }
            ).sort(
                "chunk_index",
                1
            )
        )

        results = results[:request.limit]

    else:

        query_embedding = generate_embedding(
            search_query
        )

        results = search_similar_chunks(
            query_embedding=query_embedding,
            limit=request.limit
        )

    context_parts = []

    for result in results:

        context_parts.append(
            f"""
File: {result["file_path"]}
Chunk: {result["chunk_index"]}

Code:
{result["content"]}
"""
        )

    context = "\n\n".join(
        context_parts
    )

    answer = ask_llm(
        question=request.query,
        context=context,
        chat_history=request.chat_history
    )

    return {
        "query": request.query,
        "answer": answer,
        "sources": results
    }