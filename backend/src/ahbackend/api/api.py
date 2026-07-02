import asyncio
import json
import secrets
import string
import uuid
from typing import TYPE_CHECKING, Annotated, Literal

from d3textdb import DuplicateCurieError, OntologyInUseError
from d3textdb.owl import MAX_PEEK_BYTES, parse_owl, peek_ontology_metadata
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
    Body,
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
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

app = FastAPI()


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


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def reference_body_xml(ref: Reference) -> str:
    """Wrap a body fragment with the minimal article envelope needed by the XSL."""
    pmc_tag = (
        f'<article-id pub-id-type="pmcid">PMC{ref.pmc_id}</article-id>'
        if ref.pmc_id
        else ""
    )
    return f"<article><front><article-meta>{pmc_tag}</article-meta></front>{ref.body or ''}</article>"


origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(users.router)


@app.get("/reference/")
def fetch_annotation(
    ref_identifier: str,
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> str:
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

    return reference_annotation.model_copy(
        update={
            "reference": ref.model_copy(
                update={"abstract": abstract, "body": body}
            )
        }
    ).model_dump_json()


class UserInfo(BaseModel):
    user_id: str
    email: str
    is_super_user: bool
    can_manage: bool
    disabled: bool = False


@app.get("/me")
def get_me(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> UserInfo:
    """Return the authenticated user's profile and role."""
    user_auth = get_user_auth(current_user.user_id)
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
    """Extract ontology metadata from an uploaded OWL file without importing it."""
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
    """Upload an OWL file and stream import progress as SSE events."""
    content = await file.read()

    async def _stream():  # noqa: C901
        # 1. Parse OWL
        yield _sse("progress", {"step": "parse", "loaded": 0, "total": 1})
        try:
            parsed = parse_owl(content, prefix, base_iri)
        except Exception as exc:
            yield _sse("error", {"detail": f"OWL parse error: {exc}"})
            return
        yield _sse("progress", {"step": "parse", "loaded": 1, "total": 1})

        n_entities = len(parsed.entities)
        n_triples = len(parsed.triples)
        n_props = len(parsed.properties)

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

        # 3. Load entities in a thread; iterable wrapper reports per batch
        yield _sse(
            "progress",
            {"step": "load_entities", "loaded": 0, "total": n_entities},
        )
        loop = asyncio.get_running_loop()
        entity_q: asyncio.Queue[int] = asyncio.Queue()

        def _tracked_entities():
            for count, entity in enumerate(parsed.entities, 1):
                yield entity
                if count % 500 == 0 or count == n_entities:
                    loop.call_soon_threadsafe(entity_q.put_nowait, count)

        try:
            load_task = asyncio.create_task(
                asyncio.to_thread(
                    load_entities_bulk, ontology_id, _tracked_entities()
                )
            )
            while not load_task.done():
                try:
                    loaded = await asyncio.wait_for(entity_q.get(), timeout=0.5)
                    yield _sse(
                        "progress",
                        {
                            "step": "load_entities",
                            "loaded": loaded,
                            "total": n_entities,
                        },
                    )
                except TimeoutError:
                    pass
            await asyncio.sleep(0)  # flush call_soon_threadsafe callbacks
            while not entity_q.empty():
                loaded = entity_q.get_nowait()
                yield _sse(
                    "progress",
                    {
                        "step": "load_entities",
                        "loaded": loaded,
                        "total": n_entities,
                    },
                )
            entity_count = await load_task
        except Exception as exc:
            yield _sse("error", {"detail": f"Entity loading error: {exc}"})
            delete_ontology(ontology_id)
            return

        # 4. Load triples — chunked for per-batch progress
        yield _sse(
            "progress",
            {"step": "load_triples", "loaded": 0, "total": n_triples},
        )
        triple_count = 0
        try:
            for start in range(0, n_triples, _TRIPLE_CHUNK):
                chunk = parsed.triples[start : start + _TRIPLE_CHUNK]
                stored = await asyncio.to_thread(load_triples_bulk, chunk)
                triple_count += stored
                yield _sse(
                    "progress",
                    {
                        "step": "load_triples",
                        "loaded": triple_count,
                        "total": n_triples,
                    },
                )
        except Exception as exc:
            yield _sse("error", {"detail": f"Triple loading error: {exc}"})
            delete_ontology(ontology_id)
            return

        # 5. Load properties — single shot
        yield _sse(
            "progress",
            {"step": "load_properties", "loaded": 0, "total": n_props},
        )
        try:
            property_count = await asyncio.to_thread(
                load_properties_bulk, ontology_id, parsed.properties
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
                "total": n_props,
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

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/admin/ontologies/{ontology_id}/entities")
def list_ontology_entities(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: int = 50,
    offset: int = 0,
    curie_filter: str = "",
    name_filter: str = "",
    type_filter: str = "",
) -> dict:
    """Return a page of entities for an ontology plus the total count."""
    entities, total = get_ontology_entities(
        ontology_id, limit, offset, curie_filter, name_filter, type_filter
    )
    return {"entities": entities, "total": total}


class OntologyTripleOut(BaseModel):
    subject_curie: str
    subject_name: str
    predicate: str
    object_curie: str | None
    object_name: str | None
    object_literal: str | None


@app.get("/admin/ontologies/{ontology_id}/triples")
def list_ontology_triples(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: int = 50,
    offset: int = 0,
    subject_filter: str = "",
    predicate_filter: str = "",
    object_filter: str = "",
) -> dict:
    """Return a page of triples for an ontology plus the total count."""
    rows, total = get_ontology_triples(
        ontology_id,
        limit,
        offset,
        subject_filter,
        predicate_filter,
        object_filter,
    )
    return {"triples": [OntologyTripleOut(**r) for r in rows], "total": total}


@app.post("/admin/fts/rebuild")
def rebuild_fts_index(
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> dict:
    """Rebuild the FTS5 name search index from the current Name table contents."""
    rebuild_fts()
    return {"status": "ok"}


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


@app.get("/admin/entities/proposed")
def get_proposed_entities_admin(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return proposed entities for a project (admin/curator view)."""
    entities, total = list_proposed_entities(project_id, limit, offset)
    return {"entities": entities, "total": total}


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


@app.post("/admin/entities/{curie:path}/confirm")
def confirm_proposed_entity(
    curie: str,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> dict:
    """Confirm (accept) a proposed entity."""
    confirm_entity(curie)
    return {"ok": True}


@app.delete("/admin/entities/{curie:path}")
def remove_proposed_entity(
    curie: str,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> dict:
    """Delete a proposed entity and all its annotations."""
    delete_entity(curie)
    return {"ok": True}


@app.patch("/admin/entities/{curie:path}/curie")
def rename_entity_curie(
    curie: str,
    body: UpdateCurieRequest,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> dict:
    """Rename an entity's CURIE across all tables."""
    update_entity_curie(curie, body.new_curie)
    return {"ok": True}


@app.delete("/admin/ontologies/{ontology_id}")
def remove_ontology(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
) -> dict:
    """Delete an ontology and all its entities, names, and triples."""
    try:
        delete_ontology(ontology_id)
    except OntologyInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True}


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
    email: str
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
) -> list[EntityAnnotation]:
    """Return entity classes available as annotation types."""
    return get_entity_types(q)


@app.get("/entity/search")
def entity_search(
    q: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    limit: int = 20,
    project_id: int | None = None,
    is_class: bool = False,
) -> list[EntityAnnotation]:
    """Search entities by name or synonym prefix."""
    return search_entities(q, limit, project_id, is_class)


@app.post("/save/")
def store_annotation(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
    json_data: str = Body(..., embed=True),
) -> None:
    """Update annotation in the database"""
    annotation = ReferenceAnnotation.model_validate_json(json_data)
    roles = get_user_project_roles(current_user.user_id, annotation.project_id)
    user_auth = get_user_auth(current_user.user_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    # Persist under the authenticated identity; a client-supplied user/project
    # must never let the caller impersonate another annotator or write into a
    # project they don't belong to.
    annotation.user = current_user
    upsert_annotation(annotation)


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
) -> list[ProjectResponse]:
    """List projects. Superusers see all; other users see only their own."""
    user_auth = get_user_auth(current_user.user_id)
    if user_auth and (user_auth.can_manage or user_auth.is_super_user):
        projects = list_projects()
    else:
        projects = list_user_projects(current_user.user_id)
    return [ProjectResponse.from_orm(p) for p in projects]


@app.get("/projects/{project_id}")
def get_one_project(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> ProjectResponse:
    """Return a single project. Accessible to any member or superuser."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    user_auth = get_user_auth(current_user.user_id)
    if not (user_auth and (user_auth.can_manage or user_auth.is_super_user)):
        roles = get_user_project_roles(current_user.user_id, project_id)
        if not roles:
            raise HTTPException(status_code=403, detail="Access denied")
    return ProjectResponse.from_orm(project)


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
    limit: int = 20,
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
) -> list[PropertyResponse]:
    """Return OWL object properties plus pending proposed properties for the project."""
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
    # Deduplicate: OWL properties take precedence over proposed ones with the same curie.
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
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return proposed entities for a project (curator/manager view)."""
    entities, total = list_proposed_entities(project_id, limit, offset)
    return {"entities": entities, "total": total}


@app.post("/projects/{project_id}/proposed-entities", status_code=201)
def create_project_proposed_entity(
    project_id: int,
    body: ProposedEntityRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> dict:
    """Record an annotator-proposed entity for the project."""
    _require_project_member(project_id, current_user)
    return store_proposed_entity(
        project_id,
        label=body.label,
        curie=body.curie,
        kind=body.kind,
        proposed_by=current_user.email,
    )


@app.get("/projects/{project_id}/proposed-properties")
def get_project_proposed_properties(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_admin)],
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return proposed properties for a project (curator/manager view)."""
    properties, total = list_proposed_properties(project_id, limit, offset)
    return {"properties": properties, "total": total}


@app.post("/projects/{project_id}/proposed-properties", status_code=201)
def create_project_proposed_property(
    project_id: int,
    body: ProposedPropertyRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> dict:
    """Record an annotator-proposed property for the project."""
    _require_project_member(project_id, current_user)
    return store_proposed_property(
        project_id,
        label=body.label,
        curie=body.curie,
        domain_curie=body.domain_curie,
        range_curie=body.range_curie,
        proposed_by=current_user.email,
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
) -> list[QueueItem]:
    """Return the annotation queue for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    user_auth = get_user_auth(current_user.user_id)
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
) -> None:
    """Mark a reference as complete for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    user_auth = get_user_auth(current_user.user_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    mark_annotation_complete(project_id, current_user.user_id, ref)


@app.delete("/projects/{project_id}/queue/complete", status_code=204)
def uncomplete_queue_item(
    project_id: int,
    ref: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> None:
    """Mark a reference as incomplete for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    user_auth = get_user_auth(current_user.user_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")
    mark_annotation_incomplete(project_id, current_user.user_id, ref)


@app.patch("/projects/{project_id}/curation/entity-curie", status_code=204)
def curator_rename_entity_curie(
    project_id: int,
    curie: str,
    body: UpdateCurieRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> None:
    """Rename a proposed entity's CURIE (curator access).

    Only unconfirmed (proposed) entities may be renamed via this endpoint.
    """
    _require_curator(project_id, current_user)
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
    # curator cannot rename another project's proposed entity.
    if entity.project_id != project_id:
        raise HTTPException(status_code=404, detail="Entity not found")
    update_entity_curie(curie, body.new_curie)


@app.get("/projects/{project_id}/curation/queue")
def curation_queue(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> list[ReferenceInfo]:
    """Return references ready for curation (have enough annotator completions)."""
    user_auth = get_user_auth(current_user.user_id)
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
) -> ClaimsResponse:
    """Return all unique relations from completed annotations, with evidence."""
    user_auth = get_user_auth(current_user.user_id)
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
                        EvidencePointerItem(offset=o, length=l)
                        for o, l in ptrs["subject_pointers"]
                    ],
                    object_pointers=[
                        EvidencePointerItem(offset=o, length=l)
                        for o, l in ptrs["object_pointers"]
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
) -> None:
    """Record the current curator's accept/reject verdict on a relation."""
    user_auth = get_user_auth(current_user.user_id)
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_curate_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Curator access required")
    set_curation_decision(
        project_id, relation_id, current_user.user_id, body.verdict
    )


class PointerOut(BaseModel):
    reference_id: int
    entity_id: str
    offset: int
    length: int
    field: str = "body"
    exact_text: str = ""
    prefix_text: str = ""
    suffix_text: str = ""


class RelationOut(BaseModel):
    relation_id: int | None
    predicate: str
    subject: str
    object: str


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


def _require_project_member(project_id: int, current_user: User) -> None:
    user_auth = get_user_auth(current_user.user_id)
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_access_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Access denied")


def _require_curator(project_id: int, current_user: User) -> None:
    user_auth = get_user_auth(current_user.user_id)
    roles = get_user_project_roles(current_user.user_id, project_id)
    if not can_curate_project(user_auth, roles):
        raise HTTPException(status_code=403, detail="Curator access required")


@app.get("/projects/{project_id}/curation/{reference_id}/snapshots")
def annotator_snapshots(
    project_id: int,
    reference_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> SnapshotsResponse:
    """Return each annotator's completed snapshot for a reference.

    Also includes entity metadata (name, kind) for every CURIE referenced in
    any pointer, so the frontend can display meaningful labels.
    """
    _require_curator(project_id, current_user)
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
            pointers=[
                PointerOut(
                    reference_id=p.reference_id,
                    entity_id=p.entity_id,
                    offset=p.offset,
                    length=p.length,
                    field=p.field,
                    exact_text=p.exact_text,
                    prefix_text=p.prefix_text,
                    suffix_text=p.suffix_text,
                )
                for p in s.pointers
            ],
            relations=[
                RelationOut(
                    relation_id=r.relation_id,
                    predicate=r.predicate,
                    subject=r.subject,
                    object=r.object,
                )
                for r in s.relations
            ],
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
    curated_pointers = [
        PointerOut(
            reference_id=p.reference_id,
            entity_id=p.entity_id,
            offset=p.offset,
            length=p.length,
            field=p.field,
            exact_text=p.exact_text,
            prefix_text=p.prefix_text,
            suffix_text=p.suffix_text,
        )
        for p in curated_ptr_rows
    ]
    curated_relations = [
        RelationOut(
            relation_id=r.relation_id,
            predicate=r.predicate,
            subject=r.subject,
            object=r.object,
        )
        for r in curated_rel_rows
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
    pointers: list[PointerOut]
    relations: list[RelationOut]


@app.post(
    "/projects/{project_id}/curation/{reference_id}",
    status_code=204,
)
def save_curated(
    project_id: int,
    reference_id: int,
    body: SaveCuratedRequest,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> None:
    """Persist the curator's curated annotation for a reference.

    Replaces any previous curated annotation by the same curator for this
    (project, reference) pair.
    """
    _require_curator(project_id, current_user)
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
