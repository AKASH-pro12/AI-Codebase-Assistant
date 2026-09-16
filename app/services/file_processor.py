import os
import zipfile


UPLOAD_DIR = "uploads"


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
}


def save_and_extract_zip(file, filename: str):

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    zip_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    with open(zip_path, "wb") as buffer:
        buffer.write(file)

    extract_dir = os.path.join(
        UPLOAD_DIR,
        os.path.splitext(filename)[0]
    )

    os.makedirs(
        extract_dir,
        exist_ok=True
    )

    with zipfile.ZipFile(
        zip_path,
        "r"
    ) as zip_ref:

        zip_ref.extractall(
            extract_dir
        )

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

            # Ignore dependency/lock files
            if filename in IGNORED_FILES:
                continue

            extension = os.path.splitext(
                filename
            )[1].lower()

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
        )

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