import ast
import re


class IssueDetector(ast.NodeVisitor):

    def __init__(self, source_code: str):

        self.source_code = source_code
        self.issues = []

        self.imports = []
        self.used_names = set()

    def visit_Import(self, node):

        for alias in node.names:

            imported_name = (
                alias.asname
                if alias.asname
                else alias.name.split(".")[0]
            )

            self.imports.append({
                "name": imported_name,
                "line_number": node.lineno,
                "module": alias.name
            })

        self.generic_visit(node)

    def visit_ImportFrom(self, node):

        for alias in node.names:

            if alias.name == "*":
                continue

            imported_name = (
                alias.asname
                if alias.asname
                else alias.name
            )

            self.imports.append({
                "name": imported_name,
                "line_number": node.lineno,
                "module": node.module or ""
            })

        self.generic_visit(node)

    def visit_Name(self, node):

        self.used_names.add(
            node.id
        )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node):

        if node.type is None:

            self.issues.append({
                "severity": "medium",
                "issue_type": "bare_except",
                "line_number": node.lineno,
                "message": (
                    "Bare except catches all exceptions "
                    "and may hide unexpected errors."
                )
            })

        elif (
            isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ):

            self.issues.append({
                "severity": "medium",
                "issue_type": "broad_exception",
                "line_number": node.lineno,
                "message": (
                    "Broad exception handling may hide "
                    "unexpected errors."
                )
            })

        self.generic_visit(node)

    def analyze_unused_imports(self):

        for imported in self.imports:

            if imported["name"] not in self.used_names:

                self.issues.append({
                    "severity": "low",
                    "issue_type": "unused_import",
                    "line_number": imported["line_number"],
                    "message": (
                        f"Imported name "
                        f"'{imported['name']}' "
                        f"does not appear to be used."
                    )
                })

    def analyze_comments(self):

        for line_number, line in enumerate(
            self.source_code.splitlines(),
            start=1
        ):

            if re.search(
                r"\b(TODO|FIXME)\b",
                line,
                re.IGNORECASE
            ):

                marker = re.search(
                    r"\b(TODO|FIXME)\b",
                    line,
                    re.IGNORECASE
                )

                self.issues.append({
                    "severity": "low",
                    "issue_type": marker.group(1).lower(),
                    "line_number": line_number,
                    "message": (
                        f"{marker.group(1).upper()} comment "
                        "indicates unfinished or pending work."
                    )
                })

    def analyze_hardcoded_values(self):

        sensitive_patterns = [
            r"\b(api[_-]?key)\b",
            r"\b(secret[_-]?key)\b",
            r"\b(password)\b",
            r"\b(token)\b",
        ]

        lines = self.source_code.splitlines()

        for line_number, line in enumerate(
            lines,
            start=1
        ):

            if line.strip().startswith("#"):
                continue

            for pattern in sensitive_patterns:

                if re.search(
                    pattern,
                    line,
                    re.IGNORECASE
                ):

                    if "=" not in line:
                        continue

                    value_part = line.split(
                        "=",
                        1
                    )[1].strip()

                    if value_part in (
                        "",
                        '""',
                        "''",
                        "None"
                    ):
                        continue

                    self.issues.append({
                        "severity": "high",
                        "issue_type": "hardcoded_sensitive_value",
                        "line_number": line_number,
                        "message": (
                            "A sensitive-looking value appears "
                            "to be hard-coded in the source code."
                        )
                    })

                    break

    def analyze(self):

        try:

            tree = ast.parse(
                self.source_code
            )

        except SyntaxError as error:

            return [{
                "severity": "high",
                "issue_type": "syntax_error",
                "line_number": error.lineno or 1,
                "message": (
                    f"Python syntax error: {error.msg}"
                )
            }]

        self.visit(tree)

        self.analyze_unused_imports()
        self.analyze_comments()
        self.analyze_hardcoded_values()

        self.issues.sort(
            key=lambda issue: (
                issue["line_number"],
                issue["severity"]
            )
        )

        return self.issues


def analyze_python_issues(
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
            f"Unable to read Python file: {error}"
        )

    detector = IssueDetector(
        source_code
    )

    issues = detector.analyze()

    for issue in issues:

        issue["file_path"] = file_path

    return issues