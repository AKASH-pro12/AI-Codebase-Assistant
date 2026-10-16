import io
import os
import shutil
import zipfile


UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR",
    "/tmp/uploads" if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB

ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".html",
    ".css",
    ".json",
    ".md",
    ".txt",
    ".sql",
}


IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".next",
    "venv",
    ".venv",
}


IGNORED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
    "id_rsa",
    "id_ed25519",
}

IGNORED_FILE_EXTENSIONS = {
    ".pem",
    ".key",
    ".pfx",
    ".p12",
}


def save_and_extract_zip(raw_data: bytes, codebase_id: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    extract_dir = os.path.join(UPLOAD_DIR, codebase_id)
    os.makedirs(extract_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(raw_data), "r") as zip_ref:
            abs_extract = os.path.realpath(extract_dir)

            for member in zip_ref.infolist():
                norm_name = os.path.normpath(member.filename)
                if norm_name.startswith("..") or os.path.isabs(norm_name):
                    raise ValueError(f"Path traversal detected in ZIP: {member.filename}")

                target_path = os.path.realpath(os.path.join(extract_dir, member.filename))
                if not (target_path == abs_extract or target_path.startswith(abs_extract + os.sep)):
                    raise ValueError(f"Path traversal detected in ZIP: {member.filename}")

            zip_ref.extractall(extract_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise ValueError("Invalid or corrupted ZIP archive")
    except Exception:
        shutil.rmtree(extract_dir, ignore_errors=True)
        raise

    return extract_dir


def get_code_files(directory: str):

    code_files = []

    for root, dirs, files in os.walk(directory):

        dirs[:] = [
            directory_name
            for directory_name in dirs
            if directory_name not in IGNORED_DIRECTORIES
        ]

        for filename in files:

            # Ignore dependency/lock and secret files
            if filename in IGNORED_FILES:
                continue

            extension = os.path.splitext(
                filename
            )[1].lower()

            if extension in IGNORED_FILE_EXTENSIONS:
                continue

            if extension in ALLOWED_EXTENSIONS:

                file_path = os.path.join(
                    root,
                    filename
                )

                code_files.append(
                    file_path
                )

    return code_files


def read_code_files(code_files: list[str]):

    files_data = []

    for file_path in code_files:

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                content = file.read()

            extension = os.path.splitext(
                file_path
            )[1].lower()

            files_data.append({
                "file_path": file_path,
                "extension": extension,
                "content": content
            })

        except (
            UnicodeDecodeError,
            OSError
        ):

            continue

    return files_data

def get_repository_metadata(
    directory: str,
    code_files: list[str]
):

    files_metadata = []

    for file_path in code_files:

        relative_path = os.path.relpath(
            file_path,
            directory
        ).replace("\\", "/")

        extension = os.path.splitext(
            file_path
        )[1].lower()

        files_metadata.append({
            "file_path": file_path,
            "relative_path": relative_path,
            "extension": extension
        })

    return {
        "total_files": len(files_metadata),
        "files": files_metadata
    }