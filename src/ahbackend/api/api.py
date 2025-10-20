import base64
import json
from typing import Annotated, Optional

from ahbackend import users
from ahbackend.db import query, update_annotation
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr
from xmlparser import replace_annotation, transform_article, transform_tree

app = FastAPI()

origins = ["http://localhost:5173"]

app.add_middleware(CORSMiddleware, allow_origins=origins)
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


@app.put("/annotation/")
@app.get(path="/relation/")
def retrieve_relation_data(predicate: str, subject: str, object: str) -> str:
    return query(predicate, subject, object)


def store_annotation(
    annotator: Annotated[EmailStr, Form()],
    id: Annotated[int, Form()],
    annotation: Annotated[str, Form()],
) -> None:
    """Update annotation in the database

    Todo: the job here would be far easier if the annotations were all standoff
        annotations. The database would be lighter as well.
    """
    previous = query(annotator, id).content
    new = replace_annotation(previous, annotation)

    update_annotation(annotator, id, new)


def get_response_json(*args) -> str:
    response = query(*args)
    response.content = transform_article(response.content)
    return response.model_dump_json()
