import base64
import json
import secrets
import string
from typing import Annotated, Optional, Self

from ahbackend import db, users
from ahbackend.db import (
    get_project_properties,
    get_ontology_triples,
    rebuild_fts,
    get_ontology_properties_by_id,
    list_proposed_entities,
    store_proposed_entity,
    list_proposed_properties,
    store_proposed_property,
    add_project_member,
    add_reference_to_project,
    assign_ontology_to_project,
    confirm_entity,
    create_project,
    create_user,
    delete_entity,
    delete_ontology,
    get_annotator_snapshots,
    get_curated_annotation,
    get_annotation_queue,
    get_entities_by_curies,
    get_curation_queue,
    get_entity_types,
    get_ontology_entities,
    get_project,
    get_project_annotation_queue,
    get_project_ontologies,
    get_project_queue_with_status,
    mark_annotation_complete,
    mark_annotation_incomplete,
    get_project_reference_ids,
    get_reference_by_doi,
    list_project_references,
    get_project_members,
    get_reference_annotation,
    get_reference_by_id,
    get_reference_by_pubmed_id,
    get_user,
    get_user_last_project,
    get_user_project_roles,
    list_ontologies,
    list_projects,
    list_proposed_entities,
    list_user_projects,
    query,
    remove_ontology_from_project,
    remove_project_member,
    remove_reference_from_project,
    run_ontology_import,
    save_curated_annotation,
    search_entities,
    set_user_last_project,
    set_user_role,
    list_users,
    update_entity_curie,
    upsert_annotation,
)
from d3textdb.owl import parse_owl
from d3textdb.schema import (
    EntityAnnotation,
    Ontology,
    Pointer,
    Project,
    ReferenceAnnotation,
    Relation,
    User,
)
from fastapi import Body, Depends, FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, ConfigDict
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
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> str:
    try:
        reference_annotation = get_reference_annotation(
            ref_identifier, str(current_user.user_id), project_id
        )
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
    is_project_manager: bool


@app.get("/me")
def get_me(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> UserInfo:
    """Return the authenticated user's profile and role."""
    user_auth = db.get_user_auth(current_user.user_id)
    role = user_auth.role if user_auth else "user"
    return UserInfo(
        user_id=str(current_user.user_id),
        email=str(current_user.email),
        role=role,
        is_project_manager=role in ("project_manager", "super_user"),
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


@app.post("/admin/ontology/import")
async def import_ontology(
    current_user: Annotated[User, Depends(users.get_current_admin)],
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
        ontology_id, limit, offset, subject_filter, predicate_filter, object_filter
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


@app.post("/admin/entities/{curie:path}/confirm")
def confirm_proposed_entity(
    curie: str,
    current_user: Annotated[User, Depends(users.get_current_superuser)],
) -> dict:
    """Confirm (accept) a proposed entity."""
    confirm_entity(curie)
    return {"ok": True}


@app.delete("/admin/entities/{curie:path}")
def remove_proposed_entity(
    curie: str,
    current_user: Annotated[User, Depends(users.get_current_superuser)],
) -> dict:
    """Delete a proposed entity and all its annotations."""
    delete_entity(curie)
    return {"ok": True}


@app.patch("/admin/entities/{curie:path}/curie")
def rename_entity_curie(
    curie: str,
    body: UpdateCurieRequest,
    current_user: Annotated[User, Depends(users.get_current_superuser)],
) -> dict:
    """Rename an entity's CURIE across all tables."""
    update_entity_curie(curie, body.new_curie)
    return {"ok": True}


@app.delete("/admin/ontologies/{ontology_id}")
def remove_ontology(
    ontology_id: int,
    current_user: Annotated[User, Depends(users.get_current_superuser)],
) -> dict:
    """Delete an ontology and all its entities, names, and triples."""
    delete_ontology(ontology_id)
    return {"ok": True}


_VALID_SYSTEM_ROLES = {"user", "project_manager", "superuser"}


class SetRoleRequest(BaseModel):
    role: str


@app.put("/admin/users/{username}/role", status_code=204)
def update_user_role(
    username: str,
    body: SetRoleRequest,
    _: Annotated[User, Depends(users.get_current_superuser)],
) -> None:
    """Set the system-level role for a user (superuser only)."""
    if body.role not in _VALID_SYSTEM_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of {sorted(_VALID_SYSTEM_ROLES)}",
        )
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    set_user_role(user.user_id, body.role)


@app.get("/admin/users")
def get_all_users(
    _: Annotated[User, Depends(users.get_current_superuser)],
) -> list[UserInfo]:
    """List all users with their system roles."""
    return [
        UserInfo(
            user_id=str(u.user_id),
            email=str(u.email),
            role=a.role,
            is_project_manager=a.role == "project_manager",
        )
        for u, a in list_users()
    ]


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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


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
    add_project_member(project_id, current_user.user_id, "project_manager")
    project = get_project(project_id)
    return ProjectResponse.model_validate(project)


@app.get("/projects")
def list_all_projects(
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> list[ProjectResponse]:
    """List projects. Superusers see all; other users see only their own."""
    user_auth = db.get_user_auth(current_user.user_id)
    if user_auth and user_auth.role == "super_user":
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
    user_auth = db.get_user_auth(current_user.user_id)
    if not (user_auth and user_auth.role == "super_user"):
        roles = get_user_project_roles(current_user.user_id, project_id)
        if not roles:
            raise HTTPException(status_code=403, detail="Access denied")
    return ProjectResponse.from_orm(project)


# ---------------------------------------------------------------------------
# Project members
# ---------------------------------------------------------------------------


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: str  # "project_manager" | "annotator" | "curator"
    password: str | None = None  # if set, used when creating a new user


class UserLookupResponse(BaseModel):
    exists: bool
    user_id: str | None = None
    email: str | None = None


class MemberInfo(BaseModel):
    user_id: str
    email: str
    roles: list[str]
    generated_password: str | None = None


@app.get("/projects/{project_id}/members")
def list_project_members(
    project_id: int,
    _: Annotated[User, Depends(users.require_project_manager)],
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
    _: Annotated[User, Depends(users.require_project_manager)],
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


@app.post("/projects/{project_id}/members", status_code=201)
def add_member_to_project(
    project_id: int,
    body: AddMemberRequest,
    _: Annotated[User, Depends(users.require_project_manager)],
) -> MemberInfo:
    """Add a user to a project.

    If the user does not exist they are created. If ``body.password`` is
    provided it is used as the initial password; otherwise one is generated and
    returned in ``generated_password`` (shown only once).
    """
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    valid_roles = {"project_manager", "annotator", "curator"}
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of {sorted(valid_roles)}",
        )

    generated_password: str | None = None
    user = get_user(body.email)
    if user is None:
        password = body.password if body.password else _generate_password()
        if not body.password:
            generated_password = password
        from d3textdb.schema import User as DbUser

        create_user(DbUser(email=body.email), password, role="user")
        user = get_user(body.email)
        if user is None:
            raise HTTPException(
                status_code=500, detail="Failed to create user"
            )

    add_project_member(project_id, user.user_id, body.role)
    roles = get_user_project_roles(user.user_id, project_id)
    return MemberInfo(
        user_id=str(user.user_id),
        email=str(user.email),
        roles=roles,
        generated_password=generated_password,
    )


@app.delete("/projects/{project_id}/members/{user_id}/{role}", status_code=204)
def remove_member_from_project(
    project_id: int,
    user_id: str,
    role: str,
    _: Annotated[User, Depends(users.require_project_manager)],
) -> None:
    """Remove a specific role from a user within a project."""
    import uuid as _uuid

    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid user_id")
    remove_project_member(project_id, uid, role)


# ---------------------------------------------------------------------------
# Project ontologies
# ---------------------------------------------------------------------------


@app.get("/projects/{project_id}/ontologies")
def list_project_ontologies(
    project_id: int,
    _: Annotated[User, Depends(users.require_project_manager)],
) -> list[Ontology]:
    """List ontologies assigned to a project."""
    return get_project_ontologies(project_id)


@app.post("/projects/{project_id}/ontologies/{ontology_id}", status_code=204)
def assign_ontology(
    project_id: int,
    ontology_id: int,
    _: Annotated[User, Depends(users.require_project_manager)],
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
    """Return OWL object properties from all ontologies assigned to the project."""
    return [PropertyResponse.model_validate(p) for p in get_project_properties(project_id)]


# ---------------------------------------------------------------------------
# Project-scoped proposals (entities and properties)
# ---------------------------------------------------------------------------


class ProposedEntityRequest(BaseModel):
    label: str
    curie: str
    kind: str


class ProposedPropertyRequest(BaseModel):
    label: str
    curie: str | None = None
    domain_curie: str | None = None
    range_curie: str | None = None


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
    _: Annotated[User, Depends(users.require_project_manager)],
) -> None:
    """Remove an ontology from a project."""
    remove_ontology_from_project(project_id, ontology_id)


# ---------------------------------------------------------------------------
# Project references
# ---------------------------------------------------------------------------


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
    body: str | None = None


@app.get("/projects/{project_id}/references")
def get_project_references(
    project_id: int,
    _: Annotated[User, Depends(users.require_project_manager)],
) -> list[ReferenceInfo]:
    """List references associated with a project."""
    if get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return [ReferenceInfo.model_validate(r) for r in list_project_references(project_id)]


@app.post("/projects/{project_id}/references")
def add_references(
    project_id: int,
    body: AddReferencesRequest,
    _: Annotated[User, Depends(users.require_project_manager)],
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
        else:
            try:
                ref = get_reference_by_pubmed_id(int(identifier))
            except ValueError:
                not_found.append(identifier)
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
    _: Annotated[User, Depends(users.require_project_manager)],
) -> None:
    """Remove a reference from a project."""
    remove_reference_from_project(project_id, reference_id)


# ---------------------------------------------------------------------------
# Project annotation queue
# ---------------------------------------------------------------------------


class QueueItem(BaseModel):
    ref: str
    completed: bool


@app.get("/projects/{project_id}/queue")
def project_annotation_queue(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> list[QueueItem]:
    """Return the annotation queue for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    user_auth = db.get_user_auth(current_user.user_id)
    if not roles and not (user_auth and user_auth.role == "super_user"):
        raise HTTPException(status_code=403, detail="Access denied")
    items = get_project_queue_with_status(project_id, current_user.user_id)
    return [QueueItem(ref=ref, completed=completed) for ref, completed in items]


@app.post("/projects/{project_id}/queue/complete", status_code=204)
def complete_queue_item(
    project_id: int,
    ref: str,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> None:
    """Mark a reference as complete for the current user within a project."""
    roles = get_user_project_roles(current_user.user_id, project_id)
    user_auth = db.get_user_auth(current_user.user_id)
    if not roles and not (user_auth and user_auth.role == "super_user"):
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
    user_auth = db.get_user_auth(current_user.user_id)
    if not roles and not (user_auth and user_auth.role == "super_user"):
        raise HTTPException(status_code=403, detail="Access denied")
    mark_annotation_incomplete(project_id, current_user.user_id, ref)


# ---------------------------------------------------------------------------
# Curator entity management
# ---------------------------------------------------------------------------


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
    _curator_or_superuser(project_id, current_user)
    update_entity_curie(curie, body.new_curie)


# ---------------------------------------------------------------------------
# Curation queue
# ---------------------------------------------------------------------------


@app.get("/projects/{project_id}/curation/queue")
def curation_queue(
    project_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> list[ReferenceInfo]:
    """Return references ready for curation (have enough annotator completions)."""
    user_auth = db.get_user_auth(current_user.user_id)
    roles = get_user_project_roles(current_user.user_id, project_id)
    if "curator" not in roles and not (
        user_auth and user_auth.role == "super_user"
    ):
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


# ---------------------------------------------------------------------------
# Curation: annotator snapshots and save
# ---------------------------------------------------------------------------


class PointerOut(BaseModel):
    reference_id: int
    entity_id: str
    offset: int
    length: int


class RelationOut(BaseModel):
    relation_id: int | None
    predicate: str
    subject: str
    object: str


class EntityOut(BaseModel):
    entity_id: str
    preferred_name: str
    kind: str
    confirmed: bool


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


def _curator_or_superuser(
    project_id: int, current_user: User
) -> None:
    user_auth = db.get_user_auth(current_user.user_id)
    if user_auth and user_auth.role == "super_user":
        return
    roles = get_user_project_roles(current_user.user_id, project_id)
    if "curator" not in roles:
        raise HTTPException(
            status_code=403, detail="Curator access required"
        )


@app.get(
    "/projects/{project_id}/curation/{reference_id}/snapshots"
)
def annotator_snapshots(
    project_id: int,
    reference_id: int,
    current_user: Annotated[User, Depends(users.get_current_active_user)],
) -> SnapshotsResponse:
    """Return each annotator's completed snapshot for a reference.

    Also includes entity metadata (name, kind) for every CURIE referenced in
    any pointer, so the frontend can display meaningful labels.
    """
    _curator_or_superuser(project_id, current_user)
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
    body_html: str | None = None
    if ref.body:
        try:
            body_html = transform_article(ref.body)
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
    _curator_or_superuser(project_id, current_user)
    pointers = [
        Pointer(
            reference_id=p.reference_id,
            entity_id=p.entity_id,
            offset=p.offset,
            length=p.length,
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
