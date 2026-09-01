"""Export the FastAPI app's OpenAPI schema for frontend code generation.

Importing the app pulls in :mod:`ahbackend.config`, which reads ``config.toml``
and the signing keys at import time, so this runs only in a configured
environment — not in a bare container.
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "openapi.json"


def render() -> str:
    """Return the schema as stable, diffable JSON.

    Keys are sorted so an unrelated change to route declaration order cannot
    show up as drift.
    """
    from ahbackend.api.api import app

    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the file on disk is stale, writing nothing",
    )
    args = parser.parse_args(argv)

    schema = render()
    if args.check:
        current = (
            args.output.read_text(encoding="utf-8")
            if args.output.exists()
            else ""
        )
        if current == schema:
            return 0
        print(
            f"{args.output} is out of date — run `pdm run openapi`",
            file=sys.stderr,
        )
        return 1

    args.output.write_text(schema, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
