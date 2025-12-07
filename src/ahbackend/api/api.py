import base64
import json
from typing import Annotated, Optional

from ahbackend import users
from ahbackend.db import query, upsert_annotation
from d3textdb.schema import ReferenceAnnotation, User
from fastapi import Body, Depends, FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr
from xmlparser import (
    XMLSyntaxError,
    replace_annotation,
    transform_article,
    transform_tree,
)

app = FastAPI()

origins = ["http://localhost:5173"]

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"])
app.include_router(users.router)


def get_test_response() -> str:
    with open("tests/15117974_test.json") as f:
        data = json.load(f)
        for ref in data["references"].values():
            if "body" in ref:
                html_article = transform_article(
                    article_xml=ref["body"], style="jats"
                )
                ref["body"] = base64.b64encode(html_article).decode(
                    encoding="utf-8"
                )
            ref["abstract"] = base64.b64encode(ref["abstract"].encode()).decode(
                encoding="utf-8"
            )
        return json.dumps(data)


@app.get("/segment/")
def show_segment(
    pmid: Optional[int] = None, start: Optional[int] = None
) -> str:
    args = [arg for arg in (pmid, start) if arg is not None]

    return get_response_json(*args)


@app.get("/")
def index() -> str:
    return get_test_response()


@app.get("/reference/")
def fetch_annotation(
    ref_identifier: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> str:
    reference_annotation = query(ref_identifier, current_user)

    try:
        abstract = str(
            transform_article(reference_annotation.reference.abstract)
        )
    except XMLSyntaxError:
        abstract = reference_annotation.reference.abstract

    return reference_annotation.model_copy(
        update={
            "reference": reference_annotation.reference.model_copy(
                update={
                    "abstract": abstract,
                    "body": transform_article(
                        reference_annotation.reference.body
                    ),
                }
            )
        }
    ).model_dump_json()


@app.get(path="/relation/")
def retrieve_relation_data(predicate: str, subject: str, object: str) -> str:
    return query(predicate, subject, object)


@app.post("/save/")
def store_annotation(json_data: str = Body(..., embed=True)) -> None:
    """Update annotation in the database"""
    annotation = ReferenceAnnotation.model_validate_json(json_data)
    upsert_annotation(annotation)


def get_response_json(*args) -> str:
    response = query(*args)
    response.content = transform_article(response.content)
    return response.model_dump_json()
