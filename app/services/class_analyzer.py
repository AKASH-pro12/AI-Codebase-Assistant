import ast


class ClassAnalyzer(ast.NodeVisitor):

    def __init__(self):

        self.classes = []
        self.class_stack = []


    def visit_ClassDef(self, node):

        base_classes = []

        for base in node.bases:

            if isinstance(
                base,
                ast.Name
            ):

                base_classes.append(
                    base.id
                )

            elif isinstance(
                base,
                ast.Attribute
            ):

                base_classes.append(
                    self._get_attribute_name(base)
                )

            else:

                base_classes.append(
                    ast.unparse(base)
                )

        methods = []

        for child in node.body:

            if isinstance(
                child,
                ast.FunctionDef
            ):

                methods.append({
                    "name": child.name,
                    "line_number": child.lineno,
                    "end_line_number": getattr(
                        child,
                        "end_lineno",
                        child.lineno
                    ),
                    "is_async": False
                })

            elif isinstance(
                child,
                ast.AsyncFunctionDef
            ):

                methods.append({
                    "name": child.name,
                    "line_number": child.lineno,
                    "end_line_number": getattr(
                        child,
                        "end_lineno",
                        child.lineno
                    ),
                    "is_async": True
                })

        parent_class = None

        if self.class_stack:

            parent_class = self.class_stack[-1]

        self.classes.append({
            "name": node.name,
            "base_classes": base_classes,
            "line_number": node.lineno,
            "end_line_number": getattr(
                node,
                "end_lineno",
                node.lineno
            ),
            "parent_class": parent_class,
            "methods": methods
        })

        self.class_stack.append(
            node.name
        )

        self.generic_visit(
            node
        )

        self.class_stack.pop()


    def _get_attribute_name(
        self,
        node
    ):

        parts = []

        current = node

        while isinstance(
            current,
            ast.Attribute
        ):

            parts.append(
                current.attr
            )

            current = current.value

        if isinstance(
            current,
            ast.Name
        ):

            parts.append(
                current.id
            )

        return ".".join(
            reversed(parts)
        )


def analyze_python_classes(
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


    analyzer = ClassAnalyzer()

    analyzer.visit(
        tree
    )

    return analyzer.classes