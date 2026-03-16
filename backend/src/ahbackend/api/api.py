import base64
import json
from typing import Annotated, Optional

from ahbackend import db, users
from ahbackend.db import (
    delete_ontology,
    get_annotation_queue,
    get_entity_types,
    get_ontology_entities,
    list_ontologies,
    list_proposed_entities,
    query,
    run_ontology_import,
    search_entities,
    upsert_annotation,
)
from d3textdb.owl import parse_owl
from d3textdb.schema import EntityAnnotation, Ontology, ReferenceAnnotation, User
from fastapi import Body, Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from xmlparser import (
    XMLSyntaxError,
    replace_annotation,
    transform_article,
    transform_tree,
)

app = FastAPI()

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
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
    try:
        reference_annotation = query(ref_identifier, str(current_user.user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

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


class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str


@app.get("/me")
def get_me(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> UserInfo:
    """Return the authenticated user's profile and role."""
    user_auth = db.get_user_auth(current_user.user_id)
    return UserInfo(
        user_id=str(current_user.user_id),
        email=str(current_user.email),
        role=user_auth.role if user_auth else "annotator",
    )


@app.get("/admin/ontologies")
def get_ontologies(
    current_user: Annotated[User, Depends(users.get_current_admin_user)],
) -> list[Ontology]:
    """List all ontologies loaded into the database."""
    return list_ontologies()


@app.post("/admin/ontology/import")
async def import_ontology(
    current_user: Annotated[User, Depends(users.get_current_admin_user)],
    file: UploadFile,
    name: str = Form(...),
    prefix: str = Form(...),
    base_iri: str = Form(default=""),
    version: str | None = Form(default=None),
) -> dict:
    """Upload an OWL file and import its classes and hierarchy into the DB."""
    import io

    content = await file.read()
    try:
        parsed = parse_owl(io.BytesIO(content), prefix, base_iri)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"OWL parse error: {exc}") from exc

    return run_ontology_import(parsed, name, prefix, base_iri, version)


@app.get("/admin/ontologies/{ontology_id}/entities")
def list_ontology_entities(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin_user)],
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return a page of entities for an ontology plus the total count."""
    entities, total = get_ontology_entities(ontology_id, limit, offset)
    return {"entities": entities, "total": total}


@app.get("/admin/entities/proposed")
def get_proposed_entities(
    current_user: Annotated[User, Depends(users.get_current_admin_user)],
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return unconfirmed (user-coined) entities pending curator review."""
    entities, total = list_proposed_entities(limit, offset)
    return {"entities": entities, "total": total}


@app.delete("/admin/ontologies/{ontology_id}")
def remove_ontology(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin_user)],
) -> dict:
    """Delete an ontology and all its entities, names, and triples."""
    delete_ontology(ontology_id)
    return {"ok": True}


@app.get("/entity/types")
def list_entity_types(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    q: str = "",
) -> list[EntityAnnotation]:
    """Return entity classes available as annotation types."""
    return get_entity_types(q)


@app.get("/entity/search")
def entity_search(
    q: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    limit: int = 20,
    project_id: int | None = None,
) -> list[EntityAnnotation]:
    """Search entities by name or synonym prefix."""
    return search_entities(q, limit, project_id)


@app.get("/queue/")
def annotation_queue(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> list[str]:
    """Returns a list of documents that the user is yet to annotate."""
    return [str(pmid) for pmid in get_annotation_queue(current_user.user_id)]


@app.get(path="/relation/")
def retrieve_relation_data(predicate: str, subject: str, object: str) -> str:
    return query(predicate, subject, object)


@app.post("/save/")
def store_annotation(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    json_data: str = Body(..., embed=True),
) -> None:
    """Update annotation in the database"""
    annotation = ReferenceAnnotation.model_validate_json(json_data)
    upsert_annotation(annotation)


def get_response_json(*args) -> str:
    response = query(*args)
    response.content = transform_article(response.content)
    return response.model_dump_json()
