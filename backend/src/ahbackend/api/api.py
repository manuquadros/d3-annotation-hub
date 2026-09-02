import asyncio
import contextlib
import json
import os
import secrets
import string
import tempfile
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal, Protocol, runtime_checkable

from d3textdb import DuplicateCurieError, OntologyInUseError
from d3textdb.owl import (
    MAX_PEEK_BYTES,
    OntologyStreamParser,
    peek_ontology_metadata,
)
from d3textdb.schema import (
    EntityAnnotation,
    Ontology,
    Pointer,
    Reference,
    ReferenceAnnotation,
    Relation,
    User,
    Verdict,
)
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from xkcdpass import xkcd_password as xp
from xmlparser import (
    XMLSyntaxError,
    transform_article,
)

from ahbackend import users
from ahbackend.db import UserAuth
from ahbackend.db.operations import (
    add_project_member,
    add_reference_to_project,
    archive_project,
    assign_ontology_to_project,
    backfill_entity_project,
    confirm_entity,
    create_project,
    create_user,
    delete_entity,
    delete_ontology,
    delete_user,
    disable_user,
    load_entities_bulk,
    load_properties_bulk,
    load_triples_bulk,
    mark_annotation_complete,
    mark_annotation_incomplete,
    rebuild_fts,
    remove_all_project_roles,
    remove_ontology_from_project,
    remove_project_member,
    remove_reference_from_project,
    save_curated_annotation,
    set_curation_decision,
    set_user_last_project,
    set_user_permissions,
    store_ontology_metadata,
    store_proposed_entity,
    store_proposed_property,
    store_reference,
    update_entity_curie,
    upsert_annotation,
)
from ahbackend.db.queries import (
    get_annotator_snapshots,
    get_curated_annotation,
    get_curation_claims,
    get_curation_decisions,
    get_curation_queue,
    get_entities_by_curies,
    get_entity_project_id,
    get_entity_types,
    get_ontology_entities,
    get_ontology_properties_by_id,
    get_ontology_triples,
    get_project,
    get_project_members,
    get_project_ontologies,
    get_project_properties,
    get_project_queue_with_status,
    get_project_reference_ids,
    get_reference_annotation,
    get_reference_by_doi,
    get_reference_by_id,
    get_reference_by_pubmed_id,
    get_user,
    get_user_auth,
    get_user_last_project,
    get_user_project_roles,
    list_ontologies,
    list_project_references,
    list_projects,
    list_proposed_entities,
    list_proposed_properties,
    list_user_projects,
    list_users,
    search_entities,
    search_users,
    user_has_references,
)
from ahbackend.fetch import fetch_reference_from_ncbi


@runtime_checkable
class _NamedRoute(Protocol):
    """What ``generate_unique_id_function`` is actually handed.

    FastAPI documents the parameter as ``APIRoute`` but passes a private
    wrapper around one, and beartype checks the annotation at run time — so
    match on the single attribute this needs rather than the concrete class.
    """

    name: str


def _operation_id(route: _NamedRoute) -> str:
    """Use the endpoint's own name as the OpenAPI operationId.

    Client generators derive function names from operationId; FastAPI's default
    appends the path and method ("fetch_annotation_reference__get"), which makes
    every generated call site unreadable. Endpoint names are unique across the
    app, so the bare name is enough to disambiguate.
    """
    return route.name


app = FastAPI(generate_unique_id_function=_operation_id)

# slowapi rate limiting: the limiter lives in the users module (it decorates
# /token and /change-password); the app just needs the instance on its state
# and the 429 handler registered.
app.state.limiter = users.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(DuplicateCurieError)
def _duplicate_curie_handler(
    request: Request, exc: DuplicateCurieError
) -> JSONResponse:
    """Map the domain-level duplicate-CURIE error to a 409 for every route
    that renames a CURIE, so callers don't each repeat the translation."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


VALID_ROLES: frozenset[str] = frozenset({"manager", "annotator", "curator"})
EXCLUSIVE_ROLES: frozenset[str] = frozenset({"annotator", "curator"})

_TRIPLE_CHUNK = 500

# Shared pagination bounds for every list endpoint. `le` caps the page size so a
# single request can't materialize an entire table; `ge=1` blocks SQLite's
# `LIMIT -1` (== unbounded) footgun that a negative `limit` would otherwise hit.
MAX_PAGE_SIZE = 200
LimitParam = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
OffsetParam = Annotated[int, Query(ge=0)]


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def reference_body_xml(ref: Reference) -> str:
    """Wrap a body fragment with the minimal article envelope needed by
    the XSL."""
    pmc_tag = (
        f'<article-id pub-id-type="pmcid">PMC{ref.pmc_id}</article-id>'
        if ref.pmc_id
        else ""
    )
    return (
        f"<article><front><article-meta>{pmc_tag}</article-meta></front>"
        f"{ref.body or ''}</article>"
    )


origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(users.router, generate_unique_id_function=_operation_id)


class ReferenceOut(BaseModel):
    """A stored reference. Unlike the table model, the key is assigned."""

    model_config = ConfigDict(from_attributes=True)

    reference_id: int
    pubmed_id: int | None
    pmc_id: int | None
    pmc_open: bool | None
    doi: str | None
    authors: str
    title: str
    journal: str
    volume: str
    number: str | None
    pages: str
    year: int
    abstract: str | None
    body: str | None


class EntityAnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_id: str
    preferred_name: str
    uri: str | None
    kind: str
    synonyms: list[str]
    confirmed: bool
    is_class: bool


class PointerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference_id: int
    entity_id: str
    offset: int
    length: int
    field: Literal["abstract", "body"]
    exact_text: str
    prefix_text: str
    suffix_text: str


class RelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Null only for a relation the client has coined but not yet saved.
    relation_id: int | None
    predicate: str
    subject: str
    object: str


class ReferenceAnnotationOut(BaseModel):
    """An annotation as read back from the database.

    The request model (``ReferenceAnnotationIn``) leaves anything with a
    default optional, which is right for a client that omits it but wrong for
    a response, where every field has been filled in. Declaring the read shape
    separately is what lets the generated frontend types be exact.
    """

    model_config = ConfigDict(from_attributes=True)

    user: User
    reference: ReferenceOut
    entities: list[EntityAnnotationOut]
    pointers: list[PointerOut]
    relations: list[RelationOut]
    completed: bool
    last_updated: datetime | None
    project_id: int


class UserIn(BaseModel):
    """The annotator a client names on a write.

    The handler always overwrites it with the authenticated user; it is
    declared so the identity a client does send has to be well formed.
    """

    user_id: uuid.UUID
    email: EmailStr


class ReferenceIn(BaseModel):
    """A reference as submitted with an annotation.

    ``reference_id`` is accepted because a client posts back what
    ``/reference/`` handed it, but the store matches on the natural
    identifier and assigns the key itself.
    """

    reference_id: int | None = None
    pubmed_id: int | None = None
    pmc_id: int | None = None
    pmc_open: bool | None = None
    doi: str | None = None
    authors: str
    title: str
    journal: str
    volume: str
    number: str | None = None
    pages: str
    year: int
    abstract: str | None = None
    body: str | None = None


class PointerIn(BaseModel):
    """A pointer as submitted by a client.

    The response models are strict because a stored pointer has every field;
    a client may leave the defaulted ones out.
    """

    reference_id: int
    entity_id: str
    offset: int
    length: int
    field: Literal["abstract", "body"] = "body"
    exact_text: str = ""
    prefix_text: str = ""
    suffix_text: str = ""


class RelationIn(BaseModel):
    relation_id: int | None = None
    predicate: str
    subject: str
    object: str


class ReferenceAnnotationIn(BaseModel):
    """An annotation as submitted on ``POST /save/``.

    SQLModel turns Pydantic validation off on ``table=True`` models, so a body
    typed with the storage model (``ReferenceAnnotation``, which embeds
    ``Reference``, ``Pointer`` and ``Relation``) reached the database with its
    nested objects unchecked. Restating the write shape in plain Pydantic is
    what puts them back under validation.
    """

    user: UserIn
    reference: ReferenceIn
    entities: list[EntityAnnotation] = []
    pointers: list[PointerIn] = []
    relations: list[RelationIn] = []
    completed: bool = False
    last_updated: datetime | None = None
    project_id: int

    def to_annotation(self, user: User) -> ReferenceAnnotation:
        """Build the storage model, attributed to ``user``."""
        return ReferenceAnnotation(
            user=user,
            reference=Reference(**self.reference.model_dump()),
            entities=self.entities,
            pointers=[Pointer(**p.model_dump()) for p in self.pointers],
            relations=[Relation(**r.model_dump()) for r in self.relations],
            completed=self.completed,
            last_updated=self.last_updated,
            project_id=self.project_id,
        )


@app.get("/reference/")
def fetch_annotation(
    ref_identifier: str,
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> ReferenceAnnotationOut:
    _require_project_member(project_id, current_user, user_auth)
    try:
        reference_annotation = get_reference_annotation(
            ref_identifier, str(current_user.user_id), project_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    ref = reference_annotation.reference

    try:
        abstract = transform_article(ref.abstract) if ref.abstract else None
    except XMLSyntaxError:
        abstract = ref.abstract

    try:
        body = transform_article(reference_body_xml(ref)) if ref.body else None
    except XMLSyntaxError:
        body = None

    return ReferenceAnnotationOut.model_validate(
        reference_annotation.model_copy(
            update={
                "reference": ref.model_copy(
                    update={"abstract": abstract, "body": body}
                )
            }
        )
    )


class UserInfo(BaseModel):
    user_id: str
    email: str
    is_super_user: bool
    can_manage: bool
    disabled: bool = False


@app.get("/me")
def get_me(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> UserInfo:
    """Return the authenticated user's profile and role."""
    return UserInfo(
        user_id=str(current_user.user_id),
        email=str(current_user.email),
        is_super_user=user_auth.is_super_user if user_auth else False,
        can_manage=user_auth.can_manage if user_auth else False,
    )


class LastProjectResponse(BaseModel):
    project_id: int | None


@app.get("/me/last-project")
def get_last_project(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> LastProjectResponse:
    """Return the user's last active project id, or null if none."""
    return LastProjectResponse(
        project_id=get_user_last_project(current_user.user_id)
    )


@app.put("/me/last-project", status_code=204)
def set_last_project(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> None:
    """Record the user's last active project."""
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    set_user_last_project(current_user.user_id, project_id)


class ProjectRolesResponse(BaseModel):
    roles: list[str]


@app.get("/me/project-roles")
def get_project_roles(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> ProjectRolesResponse:
    """Return the current user's roles in a specific project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    return ProjectRolesResponse(roles=roles)


@app.get("/admin/ontologies")
def get_ontologies(
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> list[Ontology]:
    """List all ontologies loaded into the database."""
    return list_ontologies()


class OntologyPeek(BaseModel):
    name: str | None = None
    prefix: str | None = None
    base_iri: str | None = None
    version: str | None = None


@app.post("/admin/ontology/peek")
async def peek_ontology(
    current_user: Annotated[User, Depends(users.get_current_admin)],
    file: UploadFile,
) -> OntologyPeek:
    """Extract ontology metadata from an uploaded OWL file without
    importing it."""
    # Non-XML serializations (Turtle, RDF/XML, JSON-LD) require a complete
    # document to parse, so read the whole file up to the cap. Reading one extra
    # byte lets us detect files that exceed it and skip the (potentially slow)
    # parse rather than truncating and failing.
    content = await file.read(MAX_PEEK_BYTES + 1)
    if len(content) > MAX_PEEK_BYTES:
        return OntologyPeek()
    meta = await run_in_threadpool(peek_ontology_metadata, content)
    return OntologyPeek(
        name=meta.name,
        prefix=meta.prefix,
        base_iri=meta.base_iri,
        version=meta.version,
    )


@app.post("/admin/ontology/import")
async def import_ontology(  # noqa: C901
    current_user: Annotated[User, Depends(users.get_current_admin)],
    file: UploadFile,
    name: str = Form(...),
    prefix: str = Form(...),
    base_iri: str = Form(default=""),
    version: str | None = Form(default=None),
) -> StreamingResponse:
    """Upload an OWL file and stream import progress as SSE events.

    The upload is spooled to a temp file and parsed with a streaming parser
    (``OntologyStreamParser``), so peak memory stays bounded even for very
    large ontologies (e.g. NCBITaxon at 1.5 GB+) instead of materializing the
    whole graph. Entity/triple counts are therefore not known up front, so
    ``total`` is reported as 0 (the client shows a running count).
    """
    # Spool the upload to disk in bounded-size chunks rather than reading the
    # whole (potentially multi-GB) file into memory.
    tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
        suffix=".owl", delete=False
    )
    try:
        while chunk := await file.read(1024 * 1024):
            tmp.write(chunk)
    finally:
        tmp.close()
    tmp_path = tmp.name

    async def _stream():  # noqa: C901
        loop = asyncio.get_running_loop()

        async def _load_phase(
            step: str, worker, out: list[int]
        ) -> AsyncIterator[str]:
            """Run ``worker(report)`` in a thread, streaming SSE progress.

            ``worker`` reports running counts via its ``report`` callback and
            returns the final total, which is appended to ``out``. Progress
            uses ``total: 0`` because the stream size is unknown until the
            parse completes.
            """
            queue: asyncio.Queue[int] = asyncio.Queue()

            def report(count: int) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, count)

            task = asyncio.create_task(asyncio.to_thread(worker, report))
            while not task.done():
                try:
                    loaded = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield _sse(
                        "progress",
                        {"step": step, "loaded": loaded, "total": 0},
                    )
                except TimeoutError:
                    pass
            await asyncio.sleep(0)  # flush call_soon_threadsafe callbacks
            while not queue.empty():
                yield _sse(
                    "progress",
                    {"step": step, "loaded": queue.get_nowait(), "total": 0},
                )
            total = await task
            out.append(total)
            yield _sse("progress", {"step": step, "loaded": total, "total": 0})

        try:
            # 1. Build the streaming parser (cheap: reads only the header).
            yield _sse("progress", {"step": "parse", "loaded": 0, "total": 1})
            try:
                parser = OntologyStreamParser(
                    path=tmp_path, prefix=prefix, base_iri=base_iri
                )
            except Exception as exc:
                yield _sse("error", {"detail": f"OWL parse error: {exc}"})
                return
            yield _sse("progress", {"step": "parse", "loaded": 1, "total": 1})

            # 2. Store ontology metadata
            yield _sse(
                "progress", {"step": "store_ontology", "loaded": 0, "total": 1}
            )
            try:
                ontology_id = store_ontology_metadata(
                    name, prefix, base_iri, version
                )
            except Exception as exc:
                yield _sse("error", {"detail": str(exc)})
                return
            yield _sse(
                "progress", {"step": "store_ontology", "loaded": 1, "total": 1}
            )

            # 3. Load entities — streamed and batched in a worker thread.
            def _entities_worker(report) -> int:
                def tracked():
                    for count, entity in enumerate(parser.iter_entities(), 1):
                        if count % 500 == 0:
                            report(count)
                        yield entity

                return load_entities_bulk(ontology_id, tracked())

            entity_out: list[int] = []
            try:
                async for event in _load_phase(
                    "load_entities", _entities_worker, entity_out
                ):
                    yield event
            except Exception as exc:
                yield _sse("error", {"detail": f"Entity loading error: {exc}"})
                delete_ontology(ontology_id)
                return
            entity_count = entity_out[0]

            # 4. Load triples — streamed and batched in a worker thread.
            def _triples_worker(report) -> int:
                total = 0
                batch: list = []
                for triple in parser.iter_triples():
                    batch.append(triple)
                    if len(batch) >= _TRIPLE_CHUNK:
                        total += load_triples_bulk(batch)
                        report(total)
                        batch = []
                if batch:
                    total += load_triples_bulk(batch)
                return total

            triple_out: list[int] = []
            try:
                async for event in _load_phase(
                    "load_triples", _triples_worker, triple_out
                ):
                    yield event
            except Exception as exc:
                yield _sse("error", {"detail": f"Triple loading error: {exc}"})
                delete_ontology(ontology_id)
                return
            triple_count = triple_out[0]

            # 5. Load properties — single shot (small; collected during pass 3).
            yield _sse(
                "progress",
                {"step": "load_properties", "loaded": 0, "total": 0},
            )
            try:
                property_count = await asyncio.to_thread(
                    load_properties_bulk, ontology_id, parser.properties
                )
            except Exception as exc:
                yield _sse("error", {"detail": str(exc)})
                delete_ontology(ontology_id)
                return

            yield _sse(
                "progress",
                {
                    "step": "load_properties",
                    "loaded": property_count,
                    "total": 0,
                },
            )
            yield _sse(
                "complete",
                {
                    "ontology_id": ontology_id,
                    "entities": entity_count,
                    "triples": triple_count,
                    "properties": property_count,
                },
            )
        finally:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class OntologyEntityPage(BaseModel):
    entities: list[EntityAnnotationOut]
    total: int


@app.get("/admin/ontologies/{ontology_id}/entities")
def list_ontology_entities(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
    curie_filter: str = "",
    name_filter: str = "",
    type_filter: str = "",
) -> OntologyEntityPage:
    """Return a page of entities for an ontology plus the total count."""
    entities, total = get_ontology_entities(
        ontology_id, limit, offset, curie_filter, name_filter, type_filter
    )
    return OntologyEntityPage(entities=entities, total=total)


class OntologyTripleOut(BaseModel):
    subject_curie: str
    subject_name: str
    predicate: str
    object_curie: str | None
    object_name: str | None
    object_literal: str | None


class OntologyTriplePage(BaseModel):
    triples: list[OntologyTripleOut]
    total: int


@app.get("/admin/ontologies/{ontology_id}/triples")
def list_ontology_triples(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
    subject_filter: str = "",
    predicate_filter: str = "",
    object_filter: str = "",
) -> OntologyTriplePage:
    """Return a page of triples for an ontology plus the total count."""
    rows, total = get_ontology_triples(
        ontology_id,
        limit,
        offset,
        subject_filter,
        predicate_filter,
        object_filter,
    )
    return OntologyTriplePage(
        triples=[OntologyTripleOut(**r) for r in rows], total=total
    )


class StatusResponse(BaseModel):
    status: str


@app.post("/admin/fts/rebuild")
def rebuild_fts_index(
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> StatusResponse:
    """Rebuild the FTS5 name search index from the current Name table
    contents."""
    rebuild_fts()
    return StatusResponse(status="ok")


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    curie: str
    label: str
    domain_curie: str | None
    range_curie: str | None


@app.get("/admin/ontologies/{ontology_id}/properties")
def list_ontology_properties(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> list[PropertyResponse]:
    """Return all object properties defined in a specific ontology."""
    return [
        PropertyResponse.model_validate(p)
        for p in get_ontology_properties_by_id(ontology_id)
    ]


class ProposedEntityOut(BaseModel):
    proposal_id: int
    curie: str | None
    label: str | None
    kind: str
    proposed_by: str | None
    status: str | None
    created_at: str | None


class ProposedEntityPage(BaseModel):
    entities: list[ProposedEntityOut]
    total: int


@app.get("/admin/entities/proposed")
def get_proposed_entities_admin(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> ProposedEntityPage:
    """Return proposed entities for a project (admin/curator view)."""
    entities, total = list_proposed_entities(project_id, limit, offset)
    return ProposedEntityPage.model_validate(
        {"entities": entities, "total": total}
    )


class UpdateCurieRequest(BaseModel):
    new_curie: str

    @field_validator("new_curie")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        # An empty CURIE would rename the entity and all its pointers/relations
        # to "", corrupting the annotations. Reject it at the boundary.
        stripped = v.strip()
        if not stripped:
            raise ValueError("new_curie must be a non-empty CURIE")
        return stripped


class OkResponse(BaseModel):
    ok: bool = True


@app.post("/admin/entities/{curie:path}/confirm")
def confirm_proposed_entity(
    curie: str,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> OkResponse:
    """Confirm (accept) a proposed entity."""
    confirm_entity(curie)
    return OkResponse()


@app.delete("/admin/entities/{curie:path}")
def remove_proposed_entity(
    curie: str,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> OkResponse:
    """Delete a proposed entity and all its annotations."""
    delete_entity(curie)
    return OkResponse()


@app.patch("/admin/entities/{curie:path}/curie")
def rename_entity_curie(
    curie: str,
    body: UpdateCurieRequest,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> OkResponse:
    """Rename an entity's CURIE across all tables."""
    update_entity_curie(curie, body.new_curie)
    return OkResponse()


@app.delete("/admin/ontologies/{ontology_id}")
def remove_ontology(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> OkResponse:
    """Delete an ontology and all its entities, names, and triples."""
    try:
        delete_ontology(ontology_id)
    except OntologyInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OkResponse()


class SetPermissionsRequest(BaseModel):
    is_super_user: bool
    can_manage: bool


@app.put("/admin/users/{username}/permissions", status_code=204)
def update_user_permissions(
    username: str,
    body: SetPermissionsRequest,
    _: Annotated[User, Depends(users.get_current_superuser)],
) -> None:
    """Set system-level permission flags for a user (superuser only)."""
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    set_user_permissions(user.user_id, body.is_super_user, body.can_manage)


class RemoveUserResponse(BaseModel):
    action: Literal["disabled", "deleted"]


@app.delete("/admin/users/{username}")
def remove_user_account(
    username: str,
    current_user: Annotated[User, Depends(users.get_current_superuser)],
) -> RemoveUserResponse:
    """Disable or delete a user account (superuser only).

    If the user has any associated data (annotations, memberships, etc.) they
    are disabled rather than deleted, preserving referential integrity. If no
    references exist the account is hard-deleted.
    """
    if str(current_user.email) == username:
        raise HTTPException(
            status_code=400, detail="Cannot remove your own account"
        )
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user_has_references(user.user_id):
        disable_user(user.user_id)
        return RemoveUserResponse(action="disabled")
    delete_user(user.user_id)
    return RemoveUserResponse(action="deleted")


@app.get("/admin/users")
def get_all_users(
    _: Annotated[User, Depends(users.get_current_superuser)],
) -> list[UserInfo]:
    """List all users with their system roles."""
    return [
        UserInfo(
            user_id=str(u.user_id),
            email=str(u.email),
            is_super_user=a.is_super_user,
            can_manage=a.can_manage,
            disabled=a.disabled,
        )
        for u, a in list_users()
    ]


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str | None = None


class CreateUserResponse(UserInfo):
    generated_password: str | None = None


@app.post("/admin/users", status_code=201)
def create_new_user(
    body: CreateUserRequest,
    _: Annotated[User, Depends(users.get_current_superuser)],
) -> CreateUserResponse:
    """Create a new user account (superuser only)."""
    if get_user(body.email) is not None:
        raise HTTPException(
            status_code=409, detail="A user with this email already exists"
        )

    generated_password = None
    password = body.password if body.password else _generate_passphrase()
    if not body.password:
        generated_password = password

    from d3textdb.schema import User as DbUser

    create_user(DbUser(email=body.email), password)
    user = get_user(body.email)
    if user is None:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user_auth = get_user_auth(user.user_id)
    return CreateUserResponse(
        user_id=str(user.user_id),
        email=str(user.email),
        is_super_user=user_auth.is_super_user if user_auth else False,
        can_manage=user_auth.can_manage if user_auth else False,
        generated_password=generated_password,
    )


@app.get("/admin/passphrase-suggestion")
def passphrase_suggestion(
    _: Annotated[User, Depends(users.get_current_active_user)],
) -> str:
    """Return a suggested passphrase for use as an initial password."""
    return _generate_passphrase()


@app.get("/entity/types")
def list_entity_types(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    q: str = "",
) -> list[EntityAnnotationOut]:
    """Return entity classes available as annotation types."""
    return [EntityAnnotationOut.model_validate(e) for e in get_entity_types(q)]


@app.get("/entity/search")
def entity_search(
    q: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
    limit: LimitParam = 20,
    project_id: int | None = None,
    is_class: bool = False,
) -> list[EntityAnnotationOut]:
    """Search entities by name or synonym prefix."""
    # A project scope surfaces that project's unconfirmed (proposed) entities,
    # so it may only be used by a member; the unscoped search stays open.
    if project_id is not None:
        _require_project_member(project_id, current_user, user_auth)
    return [
        EntityAnnotationOut.model_validate(e)
        for e in search_entities(q, limit, project_id, is_class)
    ]


@app.post("/save/")
def store_annotation(
    annotation: ReferenceAnnotationIn,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> None:
    """Update annotation in the database"""
    roles = get_user_project_roles(current_user.user_id, annotation.project_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    # Persist under the authenticated identity; a client-supplied user/project
    # must never let the caller impersonate another annotator or write into a
    # project they don't belong to.
    upsert_annotation(annotation.to_annotation(current_user))


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


_passphrase_wordlist = xp.generate_wordlist(
    wordfile=xp.locate_wordfile(), min_length=4, max_length=8
)


def _generate_passphrase(numwords: int = 4) -> str:
    return xp.generate_xkcdpassword(
        _passphrase_wordlist, numwords=numwords, delimiter="-"
    )


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    required_annotators: int = 2


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    name: str
    description: str | None
    required_annotators: int


@app.post("/projects", status_code=201)
def create_new_project(
    body: CreateProjectRequest,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> ProjectResponse:
    """Create a new annotation project (admin only)."""
    project_id = create_project(
        body.name, body.description, body.required_annotators
    )
    add_project_member(project_id, current_user.user_id, "manager")
    project = get_project(project_id)
    return ProjectResponse.model_validate(project)


@app.delete("/projects/{project_id}", status_code=204)
def archive_one_project(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> None:
    """Soft-delete (archive) a project. Requires the can_manage permission."""
    project = get_project(project_id)
    if project is None or project.archived_at is not None:
        raise HTTPException(status_code=404, detail="Project not found")
    archive_project(project_id)


@app.get("/projects")
def list_all_projects(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> list[ProjectResponse]:
    """List projects. Superusers see all; other users see only their own."""
    if user_auth and (user_auth.can_manage or user_auth.is_super_user):
        projects = list_projects()
    else:
        projects = list_user_projects(current_user.user_id)
    return [ProjectResponse.model_validate(p) for p in projects]


@app.get("/projects/{project_id}")
def get_one_project(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> ProjectResponse:
    """Return a single project. Accessible to any member or superuser."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not (user_auth and (user_auth.can_manage or user_auth.is_super_user)):
        roles = get_user_project_roles(current_user.user_id, project_id)
        if not roles:
            raise HTTPException(status_code=403, detail="Access denied")
    return ProjectResponse.model_validate(project)


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: str  # "manager" | "annotator" | "curator"
    password: str | None = None  # if set, used when creating a new user


class UserLookupResponse(BaseModel):
    exists: bool
    user_id: str | None = None
    email: str | None = None


class UserSearchResult(BaseModel):
    user_id: str
    email: str


class MemberInfo(BaseModel):
    user_id: str
    email: str
    roles: list[str]
    generated_password: str | None = None


@app.get("/projects/{project_id}/members")
def list_project_members(
    project_id: int,
    _: Annotated[User, Depends(users.require_manager)],
) -> list[MemberInfo]:
    """Return all members of a project with their roles."""
    members = get_project_members(project_id)
    return [
        MemberInfo(user_id=str(u.user_id), email=str(u.email), roles=roles)
        for u, roles in members
    ]


@app.get("/projects/{project_id}/members/lookup")
def lookup_user_for_project(
    project_id: int,
    email: str,
    _: Annotated[User, Depends(users.require_manager)],
) -> UserLookupResponse:
    """Check whether a user with the given email exists in the database."""
    user = get_user(email)
    if user is None:
        return UserLookupResponse(exists=False)
    return UserLookupResponse(
        exists=True,
        user_id=str(user.user_id),
        email=str(user.email),
    )


@app.get("/projects/{project_id}/users/search")
def search_project_users(
    project_id: int,
    q: str,
    _: Annotated[User, Depends(users.require_manager)],
    limit: LimitParam = 20,
) -> list[UserSearchResult]:
    results = search_users(q, limit)
    return [
        UserSearchResult(user_id=str(u.user_id), email=str(u.email))
        for u, a in results
        if not a.disabled
    ]


@app.post("/projects/{project_id}/members", status_code=201)
def add_member_to_project(
    project_id: int,
    body: AddMemberRequest,
    _: Annotated[User, Depends(users.require_manager)],
) -> MemberInfo:
    """Add a user to a project.

    If the user does not exist they are created. If ``body.password`` is
    provided it is used as the initial password; otherwise one is generated and
    returned in ``generated_password`` (shown only once).
    """
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of {sorted(VALID_ROLES)}",
        )

    generated_password: str | None = None
    user = get_user(body.email)
    if user is None:
        password = body.password if body.password else _generate_password()
        if not body.password:
            generated_password = password
        from d3textdb.schema import User as DbUser

        create_user(DbUser(email=body.email), password)
        user = get_user(body.email)
        if user is None:
            raise HTTPException(status_code=500, detail="Failed to create user")

    if body.role in EXCLUSIVE_ROLES:
        for other in EXCLUSIVE_ROLES - {body.role}:
            remove_project_member(project_id, user.user_id, other)

    add_project_member(project_id, user.user_id, body.role)
    roles = get_user_project_roles(user.user_id, project_id)
    return MemberInfo(
        user_id=str(user.user_id),
        email=str(user.email),
        roles=roles,
        generated_password=generated_password,
    )


@app.delete("/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member_from_project_all_roles(
    project_id: int,
    user_id: uuid.UUID,
    _: Annotated[User, Depends(users.require_manager)],
) -> None:
    """Remove a user from a project entirely (all roles)."""
    remove_all_project_roles(project_id, user_id)


@app.delete("/projects/{project_id}/members/{user_id}/{role}", status_code=204)
def remove_member_from_project(
    project_id: int,
    user_id: uuid.UUID,
    role: str,
    _: Annotated[User, Depends(users.require_manager)],
) -> None:
    """Remove a specific role from a user within a project."""
    remove_project_member(project_id, user_id, role)


@app.get("/projects/{project_id}/ontologies")
def list_project_ontologies(
    project_id: int,
    _: Annotated[User, Depends(users.require_manager)],
) -> list[Ontology]:
    """List ontologies assigned to a project."""
    return get_project_ontologies(project_id)


@app.post("/projects/{project_id}/ontologies/{ontology_id}", status_code=204)
def assign_ontology(
    project_id: int,
    ontology_id: int,
    _: Annotated[User, Depends(users.require_manager)],
) -> None:
    """Make an ontology available for annotation within a project."""
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    assign_ontology_to_project(project_id, ontology_id)


@app.get("/projects/{project_id}/properties")
def list_project_properties(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> list[PropertyResponse]:
    """Return OWL object properties plus pending proposed properties for
    the project."""
    _require_project_member(project_id, current_user, user_auth)
    owl_props = [
        PropertyResponse.model_validate(p)
        for p in get_project_properties(project_id)
    ]
    proposed, _ = list_proposed_properties(project_id, limit=500, offset=0)
    proposed_props = [
        PropertyResponse(
            curie=p["curie"],
            label=p["label"],
            domain_curie=p["domain_curie"],
            range_curie=p["range_curie"],
        )
        for p in proposed
        if p["status"] == "pending" and p["curie"]
    ]
    # Deduplicate: OWL properties take precedence over proposed ones with
    # the same curie.
    seen = {p.curie for p in owl_props}
    return owl_props + [p for p in proposed_props if p.curie not in seen]


class ProposedEntityRequest(BaseModel):
    label: str
    curie: str
    kind: str

    @field_validator("curie")
    @classmethod
    def _non_empty_curie(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("curie must be a non-empty CURIE")
        return stripped


class ProposedPropertyRequest(BaseModel):
    label: str
    curie: str | None = None
    domain_curie: str | None = None
    range_curie: str | None = None

    @field_validator("curie")
    @classmethod
    def _blank_curie_is_none(cls, v: str | None) -> str | None:
        # curie is optional for properties; normalize a whitespace-only value
        # to None rather than storing a blank identifier.
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None


@app.get("/projects/{project_id}/proposed-entities")
def get_project_proposed_entities(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> ProposedEntityPage:
    """Return proposed entities for a project (curator/manager view)."""
    entities, total = list_proposed_entities(project_id, limit, offset)
    return ProposedEntityPage.model_validate(
        {"entities": entities, "total": total}
    )


@app.post("/projects/{project_id}/proposed-entities", status_code=201)
def create_project_proposed_entity(
    project_id: int,
    body: ProposedEntityRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> ProposedEntityOut:
    """Record an annotator-proposed entity for the project."""
    _require_project_member(project_id, current_user, user_auth)
    return ProposedEntityOut.model_validate(
        store_proposed_entity(
            project_id,
            label=body.label,
            curie=body.curie,
            kind=body.kind,
            proposed_by=current_user.email,
        )
    )


class ProposedPropertyOut(BaseModel):
    proposal_id: int
    curie: str | None
    label: str
    domain_curie: str | None
    range_curie: str | None
    proposed_by: str | None
    status: str
    created_at: str


class ProposedPropertyPage(BaseModel):
    properties: list[ProposedPropertyOut]
    total: int


@app.get("/projects/{project_id}/proposed-properties")
def get_project_proposed_properties(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: LimitParam = 50,
    offset: OffsetParam = 0,
) -> ProposedPropertyPage:
    """Return proposed properties for a project (curator/manager view)."""
    properties, total = list_proposed_properties(project_id, limit, offset)
    return ProposedPropertyPage.model_validate(
        {"properties": properties, "total": total}
    )


@app.post("/projects/{project_id}/proposed-properties", status_code=201)
def create_project_proposed_property(
    project_id: int,
    body: ProposedPropertyRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> ProposedPropertyOut:
    """Record an annotator-proposed property for the project."""
    _require_project_member(project_id, current_user, user_auth)
    return ProposedPropertyOut.model_validate(
        store_proposed_property(
            project_id,
            label=body.label,
            curie=body.curie,
            domain_curie=body.domain_curie,
            range_curie=body.range_curie,
            proposed_by=current_user.email,
        )
    )


@app.delete("/projects/{project_id}/ontologies/{ontology_id}", status_code=204)
def unassign_ontology(
    project_id: int,
    ontology_id: int,
    _: Annotated[User, Depends(users.require_manager)],
) -> None:
    """Remove an ontology from a project."""
    remove_ontology_from_project(project_id, ontology_id)


class AddReferencesRequest(BaseModel):
    identifiers: list[str]


class AddReferencesResponse(BaseModel):
    imported: int
    already_in_project: int
    not_found: list[str]


def _is_doi(identifier: str) -> bool:
    return identifier.startswith("10.")


class ReferenceInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference_id: int
    pubmed_id: int | None
    doi: str | None
    title: str
    authors: str
    year: int
    abstract: str | None = None
    body: str | None = None


@app.get("/projects/{project_id}/references")
def get_project_references(
    project_id: int,
    _: Annotated[User, Depends(users.require_manager)],
) -> list[ReferenceInfo]:
    """List references associated with a project."""
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return [
        ReferenceInfo.model_validate(r)
        for r in list_project_references(project_id)
    ]


@app.post("/projects/{project_id}/references")
def add_references(
    project_id: int,
    body: AddReferencesRequest,
    _: Annotated[User, Depends(users.require_manager)],
) -> AddReferencesResponse:
    """Add references to a project by PubMed ID or DOI."""
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_ids = get_project_reference_ids(project_id)
    imported = 0
    already_in_project = 0
    not_found: list[str] = []

    for identifier in body.identifiers:
        identifier = identifier.strip()
        if not identifier:
            continue
        if _is_doi(identifier):
            ref = get_reference_by_doi(identifier)
            pubmed_id = None
        else:
            try:
                pubmed_id = int(identifier)
            except ValueError:
                not_found.append(identifier)
                continue
            ref = get_reference_by_pubmed_id(pubmed_id)

        if ref is None and pubmed_id is not None:
            fetched = fetch_reference_from_ncbi(pubmed_id)
            if fetched is not None:
                ref_id = store_reference(fetched)
                add_reference_to_project(project_id, ref_id)
                existing_ids.add(ref_id)
                imported += 1
                continue

        if ref is None:
            not_found.append(identifier)
        elif ref.reference_id in existing_ids:
            already_in_project += 1
        else:
            add_reference_to_project(project_id, ref.reference_id)
            existing_ids.add(ref.reference_id)
            imported += 1

    return AddReferencesResponse(
        imported=imported,
        already_in_project=already_in_project,
        not_found=not_found,
    )


@app.delete("/projects/{project_id}/references/{reference_id}", status_code=204)
def remove_reference(
    project_id: int,
    reference_id: int,
    _: Annotated[User, Depends(users.require_manager)],
) -> None:
    """Remove a reference from a project."""
    remove_reference_from_project(project_id, reference_id)


class QueueItem(BaseModel):
    ref: str
    citation: str
    completed: bool


@app.get("/projects/{project_id}/queue")
def project_annotation_queue(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> list[QueueItem]:
    """Return the annotation queue for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    items = get_project_queue_with_status(project_id, current_user.user_id)
    return [
        QueueItem(ref=ref, citation=citation, completed=completed)
        for ref, citation, completed in items
    ]


@app.post("/projects/{project_id}/queue/complete", status_code=204)
def complete_queue_item(
    project_id: int,
    ref: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> None:
    """Mark a reference as complete for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    mark_annotation_complete(project_id, current_user.user_id, ref)


@app.delete("/projects/{project_id}/queue/complete", status_code=204)
def uncomplete_queue_item(
    project_id: int,
    ref: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> None:
    """Mark a reference as incomplete for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    mark_annotation_incomplete(project_id, current_user.user_id, ref)


@app.patch("/projects/{project_id}/curation/entity-curie", status_code=204)
def curator_rename_entity_curie(
    project_id: int,
    curie: str,
    body: UpdateCurieRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> None:
    """Rename a proposed entity's CURIE (curator access).

    Only unconfirmed (proposed) entities may be renamed via this endpoint.
    """
    _require_curator(project_id, current_user, user_auth)
    entities = get_entities_by_curies([curie])
    if not entities:
        raise HTTPException(status_code=404, detail="Entity not found")
    entity = entities[0]
    if entity.confirmed:
        raise HTTPException(
            status_code=409,
            detail="Only proposed (unconfirmed) entities can be renamed",
        )
    # The lookup and rename are global by CURIE; scope to this project so a
    # curator cannot rename another project's proposed entity. A legacy row
    # predating the project_id column carries a NULL project_id; adopt it into
    # the current project rather than leaving it permanently un-renamable.
    entity_project_id = get_entity_project_id(curie)
    if entity_project_id is None:
        backfill_entity_project(curie, project_id)
    elif entity_project_id != project_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    update_entity_curie(curie, body.new_curie)


@app.get("/projects/{project_id}/curation/queue")
def curation_queue(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> list[ReferenceInfo]:
    """Return references ready for curation (have enough annotator
    completions)."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_curate_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Curator access required")
    refs = get_curation_queue(project_id)
    return [
        ReferenceInfo(
            reference_id=r.reference_id,
            pubmed_id=r.pubmed_id,
            doi=r.doi,
            title=r.title,
            authors=r.authors,
            year=r.year,
        )
        for r in refs
    ]


class EntityOut(BaseModel):
    entity_id: str
    preferred_name: str
    kind: str
    confirmed: bool


class EvidencePointerItem(BaseModel):
    offset: int
    length: int


class EvidenceItem(BaseModel):
    reference_id: int
    pubmed_id: int | None
    title: str
    body: str | None
    subject_pointers: list[EvidencePointerItem]
    object_pointers: list[EvidencePointerItem]


class ClaimItem(BaseModel):
    relation_id: int
    subject: str
    predicate: str
    object: str
    verdict: Verdict | None = None
    evidence: list[EvidenceItem]


class ClaimsResponse(BaseModel):
    claims: list[ClaimItem]
    entities: dict[str, EntityOut]


@app.get("/projects/{project_id}/curation/claims")
def curation_claims(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> ClaimsResponse:
    """Return all unique relations from completed annotations, with evidence."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_curate_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Curator access required")

    claims_map, refs, entity_curies, relation_ids = get_curation_claims(
        project_id
    )
    decisions = get_curation_decisions(project_id, current_user.user_id)

    entity_list = get_entities_by_curies(list(entity_curies))
    entities = {
        e.entity_id: EntityOut(
            entity_id=e.entity_id,
            preferred_name=e.preferred_name,
            kind=e.kind,
            confirmed=e.confirmed,
        )
        for e in entity_list
    }

    claims: list[ClaimItem] = []
    for (subject, predicate, object_), evidence_map in claims_map.items():
        relation_id = relation_ids[(subject, predicate, object_)]
        evidence_items: list[EvidenceItem] = []
        for ref_id, ptrs in evidence_map.items():
            ref = refs.get(ref_id)
            if ref is None:
                continue
            body_html: str | None = None
            if ref.body:
                try:
                    body_html = transform_article(reference_body_xml(ref))
                except Exception:
                    body_html = None
            evidence_items.append(
                EvidenceItem(
                    reference_id=ref_id,
                    pubmed_id=ref.pubmed_id,
                    title=ref.title,
                    body=body_html,
                    subject_pointers=[
                        EvidencePointerItem(offset=offset, length=length)
                        for offset, length in ptrs["subject_pointers"]
                    ],
                    object_pointers=[
                        EvidencePointerItem(offset=offset, length=length)
                        for offset, length in ptrs["object_pointers"]
                    ],
                )
            )
        claims.append(
            ClaimItem(
                relation_id=relation_id,
                subject=subject,
                predicate=predicate,
                object=object_,
                verdict=decisions.get(relation_id),
                evidence=evidence_items,
            )
        )

    return ClaimsResponse(claims=claims, entities=entities)


class VerdictBody(BaseModel):
    verdict: Verdict


@app.post(
    "/projects/{project_id}/curation/claims/{relation_id}/verdict",
    status_code=204,
)
def set_claim_verdict(
    project_id: int,
    relation_id: int,
    body: VerdictBody,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> None:
    """Record the current curator's accept/reject verdict on a relation."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_curate_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Curator access required")
    set_curation_decision(
        project_id, relation_id, current_user.user_id, body.verdict
    )


class AnnotatorSnapshotResponse(BaseModel):
    user_id: str
    email: str
    reference_id: int
    pointers: list[PointerOut]
    relations: list[RelationOut]
    created_at: str


class SnapshotsResponse(BaseModel):
    """Snapshot collection enriched with entity metadata.

    ``entities`` maps each CURIE that appears in any pointer to its display
    name and kind, so the frontend doesn't need a separate lookup.
    ``reference`` carries the reference title and metadata for display.
    ``curated_pointers`` and ``curated_relations`` carry this curator's
    previously saved curated annotation (empty lists if none yet).
    """

    reference: ReferenceInfo
    entities: dict[str, EntityOut]
    snapshots: list[AnnotatorSnapshotResponse]
    curated_pointers: list[PointerOut] = []
    curated_relations: list[RelationOut] = []


def can_access_project(user_auth: UserAuth | None, roles: list[str]) -> bool:
    """Return True if the user has any project role or the can_manage flag."""
    return bool(roles) or (
        user_auth is not None
        and (user_auth.can_manage or user_auth.is_super_user)
    )


def can_curate_project(user_auth: UserAuth | None, roles: list[str]) -> bool:
    """Return True if the user has the curator or manager role."""
    return "curator" in roles or "manager" in roles


def _require_project_member(
    project_id: int, current_user: User, user_auth: UserAuth | None
) -> None:
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")


def _require_curator(
    project_id: int, current_user: User, user_auth: UserAuth | None
) -> None:
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_curate_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Curator access required")


@app.get("/projects/{project_id}/curation/{reference_id}/snapshots")
def annotator_snapshots(
    project_id: int,
    reference_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> SnapshotsResponse:
    """Return each annotator's completed snapshot for a reference.

    Also includes entity metadata (name, kind) for every CURIE referenced in
    any pointer, so the frontend can display meaningful labels.
    """
    _require_curator(project_id, current_user, user_auth)
    ref = get_reference_by_id(reference_id)
    if ref is None:
        raise HTTPException(status_code=404, detail="Reference not found")
    snapshots = get_annotator_snapshots(project_id, reference_id)

    all_curies = {p.entity_id for s in snapshots for p in s.pointers}
    entity_list = get_entities_by_curies(list(all_curies))
    entities = {
        e.entity_id: EntityOut(
            entity_id=e.entity_id,
            preferred_name=e.preferred_name,
            kind=e.kind,
            confirmed=e.confirmed,
        )
        for e in entity_list
    }

    snapshot_responses = [
        AnnotatorSnapshotResponse(
            user_id=str(s.user.user_id),
            email=str(s.user.email),
            reference_id=s.reference_id,
            pointers=[PointerOut.model_validate(p) for p in s.pointers],
            relations=[RelationOut.model_validate(r) for r in s.relations],
            created_at=s.created_at.isoformat(),
        )
        for s in snapshots
    ]
    abstract_html: str | None = None
    if ref.abstract:
        try:
            abstract_html = transform_article(ref.abstract)
        except XMLSyntaxError:
            abstract_html = ref.abstract

    body_html: str | None = None
    if ref.body:
        try:
            body_html = transform_article(reference_body_xml(ref))
        except Exception:
            body_html = None

    curated_ptr_rows, curated_rel_rows = get_curated_annotation(
        project_id, reference_id, current_user.user_id
    )
    curated_pointers = [PointerOut.model_validate(p) for p in curated_ptr_rows]
    curated_relations = [
        RelationOut.model_validate(r) for r in curated_rel_rows
    ]

    return SnapshotsResponse(
        reference=ReferenceInfo(
            reference_id=ref.reference_id,
            pubmed_id=ref.pubmed_id,
            doi=ref.doi,
            title=ref.title,
            authors=ref.authors,
            year=ref.year,
            abstract=abstract_html,
            body=body_html,
        ),
        entities=entities,
        snapshots=snapshot_responses,
        curated_pointers=curated_pointers,
        curated_relations=curated_relations,
    )


class SaveCuratedRequest(BaseModel):
    pointers: list[PointerIn]
    relations: list[RelationIn]


@app.post(
    "/projects/{project_id}/curation/{reference_id}",
    status_code=204,
)
def save_curated(
    project_id: int,
    reference_id: int,
    body: SaveCuratedRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    user_auth: Annotated[UserAuth | None, Depends(users.get_current_user_auth)],
) -> None:
    """Persist the curator's curated annotation for a reference.

    Replaces any previous curated annotation by the same curator for this
    (project, reference) pair.
    """
    _require_curator(project_id, current_user, user_auth)
    pointers = [
        Pointer(
            reference_id=p.reference_id,
            entity_id=p.entity_id,
            offset=p.offset,
            length=p.length,
            field=p.field,
            exact_text=p.exact_text,
            prefix_text=p.prefix_text,
            suffix_text=p.suffix_text,
        )
        for p in body.pointers
    ]
    relations = [
        Relation(
            predicate=r.predicate,
            subject=r.subject,
            object=r.object,
        )
        for r in body.relations
    ]
    save_curated_annotation(
        project_id, reference_id, current_user.user_id, pointers, relations
    )
