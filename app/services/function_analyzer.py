import ast


class FunctionAnalyzer(ast.NodeVisitor):

    def __init__(self):

        self.functions = []
        self.class_stack = []


    def visit_ClassDef(self, node):

        self.class_stack.append(
            node.name
        )

        self.generic_visit(
            node
        )

        self.class_stack.pop()


    def visit_FunctionDef(self, node):

        self._add_function(
            node,
            is_async=False
        )

        self.generic_visit(
            node
        )


    def visit_AsyncFunctionDef(self, node):

        self._add_function(
            node,
            is_async=True
        )

        self.generic_visit(
            node
        )


    def _add_function(
        self,
        node,
        is_async: bool
    ):

        parameters = []

        for argument in node.args.posonlyargs:

            parameters.append(
                argument.arg
            )

        for argument in node.args.args:

            parameters.append(
                argument.arg
            )

        if node.args.vararg:

            parameters.append(
                f"*{node.args.vararg.arg}"
            )

        for argument in node.args.kwonlyargs:

            parameters.append(
                argument.arg
            )

        if node.args.kwarg:

            parameters.append(
                f"**{node.args.kwarg.arg}"
            )

        parent_class = None

        if self.class_stack:

            parent_class = self.class_stack[-1]

        self.functions.append({
            "name": node.name,
            "parameters": parameters,
            "line_number": node.lineno,
            "end_line_number": getattr(
                node,
                "end_lineno",
                node.lineno
            ),
            "is_async": is_async,
            "parent_class": parent_class
        })


def analyze_python_file(
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


    analyzer = FunctionAnalyzer()

    analyzer.visit(
        tree
    )

    return analyzer.functions