from fastapi import APIRouter


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

from app.routes.codebase_routes.issues import (
    router as issues_router
)

from app.routes.codebase_routes.improvements import (
    router as improvements_router
)


router = APIRouter(
    prefix="/codebase"
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

router.include_router(
    issues_router
)

router.include_router(
    improvements_router
)