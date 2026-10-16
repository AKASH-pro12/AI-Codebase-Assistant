import ast


class APIRouteAnalyzer(ast.NodeVisitor):

    def __init__(self):

        self.routes = []


    def visit_FunctionDef(self, node):

        self._analyze_function_routes(
            node
        )

        self.generic_visit(
            node
        )


    def visit_AsyncFunctionDef(self, node):

        self._analyze_function_routes(
            node
        )

        self.generic_visit(
            node
        )


    def _analyze_function_routes(
        self,
        node
    ):

        for decorator in node.decorator_list:

            route_info = self._parse_route_decorator(
                decorator
            )

            if route_info:

                route_info["function_name"] = node.name

                route_info["line_number"] = decorator.lineno

                route_info["end_line_number"] = getattr(
                    decorator,
                    "end_lineno",
                    decorator.lineno
                )

                route_info["is_async"] = isinstance(
                    node,
                    ast.AsyncFunctionDef
                )

                self.routes.append(
                    route_info
                )


    HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

    def _parse_route_decorator(
        self,
        decorator
    ):

        if not isinstance(
            decorator,
            ast.Call
        ):
            return None

        if not isinstance(
            decorator.func,
            ast.Attribute
        ):
            return None

        attr_name = decorator.func.attr.lower()
        if attr_name not in self.HTTP_METHODS and attr_name not in {"route", "api_route"}:
            return None

        route_path = None
        methods = []

        if decorator.args:
            route_path = self._get_string_value(
                decorator.args[0]
            )

        if attr_name in self.HTTP_METHODS:
            methods = [attr_name.upper()]
        else:
            for keyword in decorator.keywords:
                if keyword.arg == "methods":
                    methods = self._get_methods(
                        keyword.value
                    )
            if not methods:
                methods = ["GET"]

        if not route_path:
            for keyword in decorator.keywords:
                if keyword.arg == "path":
                    route_path = self._get_string_value(keyword.value)

        return {
            "path": route_path or "/",
            "methods": methods
        }


    def _get_string_value(
        self,
        node
    ):

        if isinstance(
            node,
            ast.Constant
        ) and isinstance(
            node.value,
            str
        ):

            return node.value

        try:

            return ast.unparse(
                node
            )

        except Exception:

            return None


    def _get_methods(
        self,
        node
    ):

        methods = []

        if isinstance(
            node,
            (ast.List, ast.Tuple, ast.Set)
        ):

            for element in node.elts:

                method = self._get_string_value(
                    element
                )

                if method:

                    methods.append(
                        method.upper()
                    )

        elif isinstance(
            node,
            ast.Constant
        ) and isinstance(
            node.value,
            str
        ):

            methods.append(
                node.value.upper()
            )

        return methods


def analyze_python_routes(
    file_path: str,
    source_code: str | None = None
):

    if source_code is None:
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


    analyzer = APIRouteAnalyzer()

    analyzer.visit(
        tree
    )

    return analyzer.routes