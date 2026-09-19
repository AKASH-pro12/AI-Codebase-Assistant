class ArchitectureAnalyzer:

    def __init__(
        self,
        repository_files: list,
        technologies: list,
        routes: list,
        relationships: list
    ):

        self.repository_files = repository_files
        self.technologies = technologies
        self.routes = routes
        self.relationships = relationships


    def build_architecture_context(self):

        context_parts = []

        context_parts.append(
            "REPOSITORY FILES:"
        )

        for file_data in self.repository_files:

            relative_path = file_data.get(
                "relative_path",
                ""
            )

            extension = file_data.get(
                "extension",
                ""
            )

            if relative_path:

                context_parts.append(
                    f"- {relative_path} ({extension})"
                )


        context_parts.append(
            "\nDETECTED TECHNOLOGIES:"
        )

        for technology in self.technologies:

            name = technology.get(
                "name",
                ""
            )

            evidence = technology.get(
                "evidence",
                []
            )

            if name:

                context_parts.append(
                    f"- {name}: {', '.join(evidence)}"
                )


        context_parts.append(
            "\nAPI ROUTES:"
        )

        for route in self.routes:

            path = route.get(
                "path",
                ""
            )

            methods = route.get(
                "methods",
                []
            )

            function_name = route.get(
                "function_name",
                ""
            )

            file_path = route.get(
                "file_path",
                ""
            )

            context_parts.append(
                f"- {methods} {path} "
                f"-> {function_name} "
                f"({file_path})"
            )


        context_parts.append(
            "\nFILE RELATIONSHIPS:"
        )

        for relationship in self.relationships:

            source_file = relationship.get(
                "source_file",
                ""
            )

            target_file = relationship.get(
                "target_file",
                ""
            )

            relationship_type = relationship.get(
                "relationship",
                ""
            )

            if source_file and target_file:

                context_parts.append(
                    f"- {source_file} "
                    f"--{relationship_type}--> "
                    f"{target_file}"
                )


        return "\n".join(
            context_parts
        )


def build_architecture_context(
    repository_files: list,
    technologies: list,
    routes: list,
    relationships: list
):

    analyzer = ArchitectureAnalyzer(
        repository_files=repository_files,
        technologies=technologies,
        routes=routes,
        relationships=relationships
    )

    return analyzer.build_architecture_context()