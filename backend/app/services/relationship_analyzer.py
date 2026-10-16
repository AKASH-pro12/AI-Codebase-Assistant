class RelationshipAnalyzer:

    def __init__(
        self,
        dependencies: list
    ):

        self.dependencies = dependencies


    def build_relationships(self):

        relationships = []

        for dependency in self.dependencies:

            source_file = dependency.get(
                "source_file"
            )

            target_file = dependency.get(
                "target_file"
            )

            if not source_file or not target_file:
                continue

            relationships.append({
                "source_file": source_file,
                "target_file": target_file,
                "relationship": "imports",
                "type": dependency.get(
                    "type"
                ),
                "module": dependency.get(
                    "module"
                ),
                "name": dependency.get(
                    "name"
                ),
                "line_number": dependency.get(
                    "line_number"
                )
            })

        return relationships


    def get_outgoing_relationships(
        self,
        file_path: str
    ):

        relationships = self.build_relationships()

        return [
            relationship
            for relationship in relationships
            if relationship["source_file"] == file_path
        ]


    def get_incoming_relationships(
        self,
        file_path: str
    ):

        relationships = self.build_relationships()

        return [
            relationship
            for relationship in relationships
            if relationship["target_file"] == file_path
        ]


    def get_file_relationship_summary(
        self,
        file_path: str
    ):

        outgoing = self.get_outgoing_relationships(
            file_path
        )

        incoming = self.get_incoming_relationships(
            file_path
        )

        return {
            "file_path": file_path,
            "outgoing_count": len(outgoing),
            "incoming_count": len(incoming),
            "outgoing_relationships": outgoing,
            "incoming_relationships": incoming
        }


def build_repository_relationships(
    dependencies: list
):

    analyzer = RelationshipAnalyzer(
        dependencies
    )

    return analyzer.build_relationships()