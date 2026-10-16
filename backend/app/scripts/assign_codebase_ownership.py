
from app.database import db

USER_ID = "6acd1764bfbe88a216cf1338"


def main():
    codebases = list(db.codebases.find({}))

    if len(codebases) != 7:
        raise RuntimeError(
            f"Expected 7 codebases, found {len(codebases)}. "
            "No changes made."
        )

    for codebase in codebases:
        codebase_id = codebase.get("codebase_id")
        if not codebase_id:
            print(
                "WARNING: Missing codebase_id:",
                str(codebase["_id"]),
                "-",
                codebase.get("codebase_name", "Unnamed")
            )
            continue

        existing_owner = codebase.get("user_id")

        if existing_owner and str(existing_owner) != USER_ID:
            raise RuntimeError(
                f"Different owner exists for codebase {codebase_id}. "
                "No changes made."
            )

    print("Codebases found:", len(codebases))
    print("Target user ID:", USER_ID)

    for codebase in codebases:
        codebase_id = codebase["codebase_id"]

        chunk_count = db.code_chunks.count_documents({
            "codebase_id": codebase_id
        })

        print(
            f"- {codebase.get('codebase_name', 'Unnamed')}: "
            f"{chunk_count} matching chunks"
        )

    if "--apply" not in __import__("sys").argv:
        print("\nDRY RUN ONLY. No database changes made.")
        print("Review the output, then run with --apply to update.")
        return

    updated_codebases = 0
    updated_chunks = 0

    for codebase in codebases:
        codebase_id = codebase["codebase_id"]

        result = db.codebases.update_one(
            {"_id": codebase["_id"]},
            {"$set": {"user_id": USER_ID}}
        )
        updated_codebases += result.modified_count

        chunk_result = db.code_chunks.update_many(
            {"codebase_id": codebase_id},
            {"$set": {"user_id": USER_ID}}
        )
        updated_chunks += chunk_result.modified_count

    print("\nOwnership assignment completed.")
    print("Codebase documents modified:", updated_codebases)
    print("Code chunks modified:", updated_chunks)

    for codebase in db.codebases.find({}):
        assert str(codebase.get("user_id")) == USER_ID

    print("Verification passed for all 7 codebases.")


if __name__ == "__main__":
    main()


from app.database import db

for d in db.codebases.find({}):
    print({
        "_id": str(d["_id"]),
        "fields": list(d.keys()),
        "codebase_id": repr(d.get("codebase_id")),
        "codebase_name": d.get("codebase_name")
    })