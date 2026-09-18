import ast
import os


class DependencyAnalyzer(ast.NodeVisitor):

    def __init__(self):

        self.dependencies = []


    def visit_Import(self, node):

        for alias in node.names:

            self.dependencies.append({
                "type": "import",
                "module": alias.name,
                "name": None,
                "line_number": node.lineno
            })

        self.generic_visit(
            node
        )


    def visit_ImportFrom(self, node):

        module = node.module or ""

        if node.level:

            module = "." * node.level + module

        for alias in node.names:

            self.dependencies.append({
                "type": "from_import",
                "module": module,
                "name": alias.name,
                "line_number": node.lineno
            })

        self.generic_visit(
            node
        )


def analyze_python_dependencies(
    file_path: str
):

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            source_code = file.read()

    except (
        UnicodeDecodeError,
        OSError
    ) as error:

        raise ValueError(
            f"Unable to read file: {error}"
        )


    try:

        tree = ast.parse(
            source_code
        )

    except SyntaxError as error:

        raise ValueError(
            f"Unable to parse Python file: {error}"
        )


    analyzer = DependencyAnalyzer()

    analyzer.visit(
        tree
    )

    return analyzer.dependencies


def resolve_local_dependencies(
    file_path: str,
    dependencies: list,
    repository_files: list
):

    file_directory = os.path.dirname(
        file_path
    )

    repository_file_set = {
        os.path.normpath(
            path
        )
        for path in repository_files
    }

    resolved_dependencies = []

    for dependency in dependencies:

        module = dependency.get(
            "module",
            ""
        )

        if not module:
            continue

        clean_module = module.lstrip(
            "."
        )

        module_parts = clean_module.split(
            "."
        )

        possible_path = os.path.join(
            file_directory,
            *module_parts
        )

        python_file = os.path.normpath(
            possible_path + ".py"
        )

        package_file = os.path.normpath(
            os.path.join(
                possible_path,
                "__init__.py"
            )
        )

        target_file = None

        if python_file in repository_file_set:

            target_file = python_file

        elif package_file in repository_file_set:

            target_file = package_file

        if target_file:

            resolved_dependencies.append({
                "source_file": file_path,
                "target_file": target_file,
                "type": dependency["type"],
                "module": dependency["module"],
                "name": dependency["name"],
                "line_number": dependency["line_number"]
            })

    return resolved_dependencies