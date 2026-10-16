import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from app.database import db
from app.utils.auth import get_current_user

from app.services.file_processor import (
    save_and_extract_zip,
    get_code_files,
    read_code_files,
    get_repository_metadata,
    UPLOAD_DIR,
    MAX_UPLOAD_BYTES,
    ALLOWED_EXTENSIONS,
    IGNORED_FILES,
    IGNORED_FILE_EXTENSIONS,
)

from app.services.code_chunker import chunk_code
from app.services.embedding import generate_embedding
from app.services.function_analyzer import analyze_python_file
from app.services.class_analyzer import analyze_python_classes
from app.services.api_route_analyzer import analyze_python_routes
from app.services.issue_detector import analyze_python_issues


router = APIRouter(
    tags=["Codebase Upload"]
)


@router.post("/upload")
def upload_codebase(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are allowed"
        )

    # Get the authenticated user's ID
    user_id = str(current_user["_id"])
    codebase_id = str(uuid.uuid4())
    extract_dir = None

    try:
        # Read uploaded ZIP file
        raw_data = file.file.read()

        if not raw_data:
            raise HTTPException(
                status_code=400,
                detail="Uploaded ZIP file is empty"
            )

        # Enforce server-side file size limit
        if len(raw_data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
            )

        # Extract repository files into isolated directory for this codebase
        try:
            extract_dir = save_and_extract_zip(
                raw_data,
                codebase_id
            )
        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )

        code_files = get_code_files(extract_dir)
        if not code_files:
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail="No supported source code files found in the ZIP archive"
            )

        files_data = read_code_files(code_files)
        if not files_data:
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail="No readable source code files found in the ZIP archive"
            )

        repository_metadata = get_repository_metadata(
            extract_dir,
            code_files
        )

        # Store codebase metadata with ownership
        codebase_document = {
            "codebase_id": codebase_id,
            "user_id": user_id,
            "codebase_name": file.filename,
            "total_files": repository_metadata["total_files"],
            "files": repository_metadata["files"],
            "created_at": datetime.now(timezone.utc)
        }

        all_chunks = []

        # Split files into chunks and generate embeddings
        for file_entry in files_data:
            chunks = chunk_code(file_entry["content"])

            for chunk in chunks:
                embedding_text = (
                    f"File: {file_entry['file_path']}\n"
                    f"Extension: {file_entry['extension']}\n\n"
                    f"Code:\n{chunk['content']}"
                )

                embedding = generate_embedding(embedding_text)

                all_chunks.append({
                    "codebase_id": codebase_id,
                    "user_id": user_id,
                    "file_path": file_entry["file_path"],
                    "extension": file_entry["extension"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "embedding": embedding
                })

        # Save metadata and chunks
        db.codebases.insert_one(codebase_document)

        if all_chunks:
            db.code_chunks.insert_many(all_chunks)

        return {
            "message": "Codebase processed and stored successfully",
            "codebase_id": codebase_id,
            "filename": file.filename,
            "total_files": len(files_data),
            "total_chunks": len(all_chunks)
        }

    except HTTPException:
        raise

    except Exception:
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        db.codebases.delete_one({"codebase_id": codebase_id, "user_id": user_id})
        db.code_chunks.delete_many({"codebase_id": codebase_id, "user_id": user_id})
        raise HTTPException(
            status_code=500,
            detail="Failed to process the uploaded codebase"
        )

    finally:
        file.file.close()


@router.post("/upload-files")
def upload_multiple_files(
    files: list[UploadFile] = File(...),
    codebase_name: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Accepts multiple individual source files or folder selections and creates a codebase."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    user_id = str(current_user["_id"])
    codebase_id = str(uuid.uuid4())
    codebase_dir = os.path.join(UPLOAD_DIR, codebase_id)
    os.makedirs(codebase_dir, exist_ok=True)

    final_name = (codebase_name or "").strip() or f"Codebase-{codebase_id[:8]}"
    saved_files = []
    total_bytes = 0

    try:
        for f in files:
            raw_filename = f.filename or "unknown.txt"
            # Sanitize path to prevent directory traversal
            clean_rel = raw_filename.replace("\\", "/").strip("/")
            parts = [p for p in clean_rel.split("/") if p and p != ".." and p != "."]
            if not parts:
                continue
            safe_rel_path = "/".join(parts)
            ext = os.path.splitext(parts[-1])[1].lower()

            if parts[-1] in IGNORED_FILES or ext in IGNORED_FILE_EXTENSIONS:
                continue

            if ext not in ALLOWED_EXTENSIONS:
                continue

            content_bytes = f.file.read()
            total_bytes += len(content_bytes)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Total upload size exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
                )

            try:
                text_content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                continue

            # Save on disk under codebase_dir
            dest_file_path = os.path.join(codebase_dir, *parts)
            os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
            with open(dest_file_path, "w", encoding="utf-8") as out:
                out.write(text_content)

            saved_files.append({
                "file_path": dest_file_path,
                "relative_path": safe_rel_path,
                "extension": ext,
                "content": text_content,
            })

        if not saved_files:
            shutil.rmtree(codebase_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail="No supported or readable source code files were uploaded"
            )

        codebase_document = {
            "codebase_id": codebase_id,
            "user_id": user_id,
            "codebase_name": final_name,
            "total_files": len(saved_files),
            "files": [
                {
                    "file_path": sf["file_path"],
                    "relative_path": sf["relative_path"],
                    "extension": sf["extension"],
                }
                for sf in saved_files
            ],
            "created_at": datetime.now(timezone.utc),
        }

        all_chunks = []
        for sf in saved_files:
            chunks = chunk_code(sf["content"])
            for chunk in chunks:
                embedding_text = (
                    f"File: {sf['file_path']}\n"
                    f"Extension: {sf['extension']}\n\n"
                    f"Code:\n{chunk['content']}"
                )
                embedding = generate_embedding(embedding_text)
                all_chunks.append({
                    "codebase_id": codebase_id,
                    "user_id": user_id,
                    "file_path": sf["file_path"],
                    "extension": sf["extension"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "embedding": embedding,
                })

        db.codebases.insert_one(codebase_document)
        if all_chunks:
            db.code_chunks.insert_many(all_chunks)

        return {
            "message": "Files processed and codebase created successfully",
            "codebase_id": codebase_id,
            "codebase_name": final_name,
            "total_files": len(saved_files),
            "total_chunks": len(all_chunks),
        }

    except HTTPException:
        if os.path.exists(codebase_dir):
            shutil.rmtree(codebase_dir, ignore_errors=True)
        db.codebases.delete_one({"codebase_id": codebase_id, "user_id": user_id})
        db.code_chunks.delete_many({"codebase_id": codebase_id, "user_id": user_id})
        raise
    except Exception as exc:
        if os.path.exists(codebase_dir):
            shutil.rmtree(codebase_dir, ignore_errors=True)
        db.codebases.delete_one({"codebase_id": codebase_id, "user_id": user_id})
        db.code_chunks.delete_many({"codebase_id": codebase_id, "user_id": user_id})
        raise HTTPException(status_code=500, detail=f"Failed to process files: {str(exc)}")


@router.post("/analyze-single-file")
def analyze_single_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Provides instant AST and code quality analysis on an individual file without saving."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    raw_data = file.file.read()
    if not raw_data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(raw_data) > 5 * 1024 * 1024:  # 5 MB max for single-file instant check
        raise HTTPException(status_code=400, detail="Single file analysis limit is 5 MB")

    try:
        content = raw_data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")

    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)

    functions = []
    classes = []
    routes = []
    issues = []
    language = "text"

    if ext == ".py":
        language = "python"
        try:
            functions = analyze_python_file(file.filename, source_code=content)
        except Exception:
            functions = []

        try:
            classes = analyze_python_classes(file.filename, source_code=content)
        except Exception:
            classes = []

        try:
            routes = analyze_python_routes(file.filename, source_code=content)
        except Exception:
            routes = []

        try:
            issues = analyze_python_issues(file.filename, source_code=content)
        except Exception:
            issues = []

    elif ext in {".js", ".jsx", ".ts", ".tsx"}:
        language = "javascript" if ext in {".js", ".jsx"} else "typescript"
        # Extract functions, imports, components using lexical patterns
        fn_pattern = re.compile(r"(?:function\s+([a-zA-Z0-9_$]+)|const\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)", re.MULTILINE)
        for m in fn_pattern.finditer(content):
            fn_name = m.group(1) or m.group(2)
            if fn_name:
                lineno = content[:m.start()].count("\n") + 1
                functions.append({"name": fn_name, "line_number": lineno, "is_async": "async" in m.group(0)})

        # Check for simple issues: console.log, debugger, TODO
        for idx, line in enumerate(lines, 1):
            if "debugger;" in line:
                issues.append({"severity": "high", "issue_type": "debugger_statement", "line_number": idx, "message": "Debugger statement left in code"})
            elif "console.log(" in line:
                issues.append({"severity": "low", "issue_type": "console_log", "line_number": idx, "message": "Console log call left in code"})
            elif "TODO" in line:
                issues.append({"severity": "low", "issue_type": "todo_comment", "line_number": idx, "message": f"TODO item found: {line.strip()}"})

    return {
        "filename": file.filename,
        "extension": ext,
        "language": language,
        "line_count": line_count,
        "character_count": char_count,
        "functions": functions,
        "classes": classes,
        "routes": routes,
        "issues": issues,
        "summary": {
            "total_functions": len(functions),
            "total_classes": len(classes),
            "total_routes": len(routes),
            "total_issues": len(issues),
        }
    }
