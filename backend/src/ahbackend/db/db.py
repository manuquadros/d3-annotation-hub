import pathlib
import uuid
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from importlib import resources
from typing import Any, Optional

from d3textdb import D3TextDB, ParsedOntology
from d3textdb.schema import (
    OntologyProperty,
    ProposedEntity,
    ProposedProperty,
    AnnotationSnapshot,
    AnnotationState,
    AnnotatorSnapshot,
    CuratedAnnotation,
    CuratedAnnotationPointer,
    CuratedAnnotationRelation,
    EntityAnnotation,
    Ontology,
    Pointer,
    Project,
    ProjectReference,
    Reference,
    ReferenceAnnotation,
    Relation,
    SnapshotPointer,
    SnapshotRelation,
    StatePointer,
    StateRelation,
    User,
    UserAuth,
)
from multimethod import multimethod
from pydantic import EmailStr
from rich import print
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.functions import random
from sqlmodel import Session, col, create_engine, delete, select
from tokenizers.normalizers import BertNormalizer
from xmlparser import transform_article

db_path = resources.files("ahbackend.db") / "database.db"
annodb = D3TextDB(db_path, echo=True)


def get_user(email: EmailStr) -> User | None:
    return annodb.get_user(email)


def get_user_auth(user_id: uuid.UUID) -> UserAuth | None:
    return annodb.get_user_auth(user_id)


def create_user(user: User, password: str, role: str = "user") -> uuid.UUID | None:
    return annodb.create_user(user, password, role)


def get_reference_by_pubmed_id(pubmed_id: int) -> Reference | None:
    return annodb.get_article_by_pubmed_id(pubmed_id)


def get_reference_by_doi(doi: str) -> Reference | None:
    return annodb.get_reference_by_doi(doi)


def get_project_reference_ids(project_id: int) -> set[int]:
    return annodb.get_project_reference_ids(project_id)


def list_project_references(project_id: int) -> list[Reference]:
    return annodb.list_project_references(project_id)


def get_reference_by_id(reference_id: int) -> Reference | None:
    with Session(annodb.engine) as session:
        return session.get(Reference, reference_id)


def search_entities(
    query: str, limit: int = 20, project_id: int | None = None, is_class: bool = False
) -> list[EntityAnnotation]:
    return annodb.search_entities(query, limit, project_id, is_class)


def get_entities_by_curies(curies: list[str]) -> list[EntityAnnotation]:
    return annodb.get_entities_by_curies(curies)


def get_entity_types(query: str = "") -> list[EntityAnnotation]:
    return annodb.get_entity_types(query)


def list_ontologies() -> list[Ontology]:
    return annodb.list_ontologies()


def get_ontology_entities(
    ontology_id: int,
    limit: int = 50,
    offset: int = 0,
    curie_filter: str = "",
    name_filter: str = "",
    type_filter: str = "",
) -> tuple[list[EntityAnnotation], int]:
    return annodb.get_ontology_entities(
        ontology_id, limit, offset, curie_filter, name_filter, type_filter
    )


def delete_ontology(ontology_id: int) -> None:
    annodb.delete_ontology(ontology_id)


def list_proposed_entities(
    limit: int = 50, offset: int = 0
) -> tuple[list[EntityAnnotation], int]:
    return annodb.list_proposed_entities(limit, offset)


def confirm_entity(curie: str) -> None:
    annodb.confirm_entity(curie)


def delete_entity(curie: str) -> None:
    annodb.delete_entity(curie)


def update_entity_curie(old_curie: str, new_curie: str) -> None:
    annodb.update_entity_curie(old_curie, new_curie)


def update_password(user_id: uuid.UUID, new_password: str) -> None:
    annodb.update_password(user_id, new_password)


def run_ontology_import(
    parsed: ParsedOntology,
    name: str,
    prefix: str,
    base_iri: str,
    version: str | None,
) -> dict[str, int]:
    """Store ontology metadata, bulk-load entities, triples, and properties.

    Returns a summary dict with ``ontology_id``, ``entities``, ``triples``,
    and ``properties``.
    """
    ontology_id = annodb.store_ontology(
        name=name, prefix=prefix, uri=base_iri, version=version
    )
    entity_count = annodb.load_ontology_entities(ontology_id, parsed.entities)
    triple_count = annodb.load_ontology_triples(parsed.triples)
    property_count = annodb.load_ontology_properties(ontology_id, parsed.properties)
    return {
        "ontology_id": ontology_id,
        "entities": entity_count,
        "triples": triple_count,
        "properties": property_count,
    }


def get_project_properties(project_id: int) -> list[OntologyProperty]:
    """Return all object properties from ontologies assigned to the project."""
    return annodb.get_project_properties(project_id)


def get_ontology_triples(
    ontology_id: int,
    limit: int = 50,
    offset: int = 0,
    subject_filter: str = "",
    predicate_filter: str = "",
    object_filter: str = "",
) -> tuple[list[dict], int]:
    """Return a page of triples for an ontology and the total count."""
    return annodb.get_ontology_triples(
        ontology_id, limit, offset, subject_filter, predicate_filter, object_filter
    )


def rebuild_fts() -> None:
    """Rebuild the FTS5 name index from the current Name table contents."""
    annodb.rebuild_fts()


def get_ontology_properties_by_id(ontology_id: int) -> list[OntologyProperty]:
    """Return all object properties defined in a specific ontology."""
    return annodb.get_ontology_properties_by_id(ontology_id)


def list_proposed_entities(
    project_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[dict], int]:
    return annodb.list_proposed_entities(project_id, limit, offset)


def store_proposed_entity(
    project_id: int,
    label: str,
    curie: str,
    kind: str,
    proposed_by: str | None = None,
) -> dict:
    return annodb.store_proposed_entity(project_id, label, curie, kind, proposed_by)


def list_proposed_properties(
    project_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[dict], int]:
    return annodb.list_proposed_properties(project_id, limit, offset)


def store_proposed_property(
    project_id: int,
    label: str,
    curie: str | None = None,
    domain_curie: str | None = None,
    range_curie: str | None = None,
    proposed_by: str | None = None,
) -> dict:
    return annodb.store_proposed_property(
        project_id, label, curie, domain_curie, range_curie, proposed_by
    )


def upsert_annotation(annotation: ReferenceAnnotation) -> None:
    """Insert or update the database annotation corresponding to `annotation`."""

    annodb.store_annotation(annotation)


# def get_unannotated(
#     annotator: Optional[EmailStr] = None, batch_size: Optional[int] = None
# ) -> Iterator[Response]:
#     if annotator is not None:
#         annotated = select(Annotation.chunk).where(
#             Annotation.annotator == annotator
#         )
#     else:
#         annotated = select(Annotation.chunk)

#     query = (
#         select(TextChunk, Text)
#         .join(Text)
#         .where(col(TextChunk.id).not_in(annotated))
#     )

#     if batch_size is not None:
#         query = query.limit(batch_size)

#     with Session(engine) as session:
#         results = session.exec(query).all()

#     for result in results:
#         article = result[1]
#         chunk = result[0]
#         yield Response(
#             article=article,
#             chunk=chunk,
#             content=chunk.content,
#         )


# ------------------------------------------------------------------
# Project management
# ------------------------------------------------------------------


def create_project(
    name: str,
    description: str | None = None,
    required_annotators: int = 2,
) -> int:
    return annodb.create_project(name, description, required_annotators)


def get_project(project_id: int) -> Project | None:
    return annodb.get_project(project_id)


def list_projects() -> list[Project]:
    return annodb.list_projects()


def list_user_projects(user_id: uuid.UUID) -> list[Project]:
    return annodb.list_user_projects(user_id)


def is_project_manager(user_id: uuid.UUID) -> bool:
    return annodb.is_project_manager(user_id)


def set_user_role(user_id: uuid.UUID, role: str) -> None:
    with Session(annodb.engine) as session:
        auth = session.get(UserAuth, user_id)
        if auth is None:
            raise ValueError(f"No auth record for user_id {user_id}")
        auth.role = role
        session.add(auth)
        session.commit()


def list_users() -> list[tuple[User, UserAuth]]:
    """Return all users with their auth records."""
    with Session(annodb.engine) as session:
        rows = session.execute(
            select(User, UserAuth).join(UserAuth, UserAuth.user_id == User.user_id)
        ).all()
        return [(u, a) for u, a in rows]


def add_project_member(
    project_id: int, user_id: uuid.UUID, role: str
) -> None:
    annodb.add_project_member(project_id, user_id, role)


def remove_project_member(
    project_id: int, user_id: uuid.UUID, role: str
) -> None:
    annodb.remove_project_member(project_id, user_id, role)


def get_project_members(
    project_id: int,
) -> list[tuple[User, list[str]]]:
    return annodb.get_project_members(project_id)


def get_user_project_roles(user_id: uuid.UUID, project_id: int) -> list[str]:
    return annodb.get_user_project_roles(user_id, project_id)


def get_project_ontologies(project_id: int) -> list[Ontology]:
    return annodb.get_project_ontologies(project_id)


def assign_ontology_to_project(project_id: int, ontology_id: int) -> None:
    annodb.assign_ontology_to_project(project_id, ontology_id)


def remove_ontology_from_project(project_id: int, ontology_id: int) -> None:
    annodb.remove_ontology_from_project(project_id, ontology_id)


def add_reference_to_project(project_id: int, reference_id: int) -> None:
    annodb.add_reference_to_project(project_id, reference_id)


def remove_reference_from_project(project_id: int, reference_id: int) -> None:
    annodb.remove_reference_from_project(project_id, reference_id)


def get_user_last_project(user_id: uuid.UUID) -> int | None:
    return annodb.get_user_last_project(user_id)


def set_user_last_project(user_id: uuid.UUID, project_id: int) -> None:
    annodb.set_user_last_project(user_id, project_id)


def get_project_annotation_queue(
    project_id: int, user_id: uuid.UUID
) -> list[str]:
    return annodb.get_project_annotation_queue(project_id, user_id)


def get_curation_queue(project_id: int) -> list[Reference]:
    return annodb.get_curation_queue(project_id)


def get_annotator_snapshots(
    project_id: int, reference_id: int
) -> list[AnnotatorSnapshot]:
    return annodb.get_annotator_snapshots(project_id, reference_id)


def save_curated_annotation(
    project_id: int,
    reference_id: int,
    curator_id: uuid.UUID,
    pointers: list[Pointer],
    relations: list[Relation],
) -> int:
    # Drop any pointers that don't exist in the pointer table; this guards
    # against FK violations if the caller sends stale or example data.
    if pointers:
        with Session(annodb.engine) as session:
            valid: list[Pointer] = []
            for p in pointers:
                exists = session.scalar(
                    select(Pointer.reference_id).where(
                        (Pointer.reference_id == p.reference_id)
                        & (Pointer.entity_id == p.entity_id)
                        & (Pointer.offset == p.offset)
                        & (Pointer.length == p.length)
                    )
                )
                if exists is not None:
                    valid.append(p)
            pointers = valid

    return annodb.save_curated_annotation(
        project_id, reference_id, curator_id, pointers, relations
    )


def get_annotation_queue(user_id: uuid.UUID) -> list[str]:
    """Return identifiers of references not yet completed by the user.

    Returns the pubmed_id when available, otherwise the doi.
    """
    annotated = select(AnnotationSnapshot.reference_id).where(
        AnnotationSnapshot.user_id == user_id
    )
    stmt = select(Reference.pubmed_id, Reference.doi).where(
        col(Reference.reference_id).not_in(annotated)
    )
    with Session(annodb.engine) as session:
        return [
            str(pubmed_id) if pubmed_id is not None else doi
            for pubmed_id, doi in session.execute(stmt).all()
        ]


@multimethod
def query(pmid: int) -> Reference:
    return annodb.get_article_by_pubmed_id(pmid)


def get_reference_annotation(
    ref_identifier: str, user_id: str, project_id: int
) -> ReferenceAnnotation:
    return annodb.get_reference_annotation(
        int(ref_identifier), uuid.UUID(user_id), project_id
    )


@query.register
def _(predicate: str, subject: str, object: str) -> str:
    relation = annodb.get_relation(
        predicate=predicate, subject=subject, object=object
    )
    if relation is None:
        return ""
    return relation.model_dump_json()


# def get_batch(
#     annotator_email: EmailStr, batch_size: int
# ) -> Iterator[HtmlChunk]:
#     for item in get_unannotated(annotator_email, batch_size):
#         yield response_to_article(item)


# def response_to_article(item: Response) -> HtmlChunk:
#     content = BertNormalizer(lowercase=False).normalize_str(item.content)

#     return HtmlChunk(
#         article_id=item.article.id,
#         chunk_id=item.chunk.id if item.chunk else None,
#         metadata=item.article.meta,
#         body=content,
#     )


def get_project_queue_with_status(
    project_id: int, user_id: uuid.UUID
) -> list[tuple[str, bool]]:
    """Return all project references with completion status for the user.

    Returns a list of (identifier, completed) tuples where identifier is the
    pubmed_id string when available, otherwise the doi.
    """
    with Session(annodb.engine) as session:
        completed_ref_ids = set(
            session.scalars(
                select(AnnotationSnapshot.reference_id).where(
                    (AnnotationSnapshot.project_id == project_id)
                    & (AnnotationSnapshot.user_id == user_id)
                )
            ).all()
        )
        rows = session.execute(
            select(Reference.pubmed_id, Reference.doi, Reference.reference_id)
            .join(
                ProjectReference,
                ProjectReference.reference_id == Reference.reference_id,
            )
            .where(ProjectReference.project_id == project_id)
        ).all()
        return [
            (
                str(pubmed_id) if pubmed_id is not None else doi,
                ref_id in completed_ref_ids,
            )
            for pubmed_id, doi, ref_id in rows
        ]


def mark_annotation_complete(
    project_id: int, user_id: uuid.UUID, ref_identifier: str
) -> None:
    """Create an AnnotationSnapshot for the user's current state on this reference.

    Mirrors the logic in D3TextDB.store_annotation for the snapshot portion,
    without re-saving entity/pointer data.  Idempotent: does nothing if a
    snapshot already exists for the (project, user, reference) triple.
    """
    if ref_identifier.startswith("10."):
        ref = annodb.get_reference_by_doi(ref_identifier)
    else:
        try:
            ref = annodb.get_article_by_pubmed_id(int(ref_identifier))
        except (ValueError, TypeError):
            return
    if ref is None:
        return

    reference_id = ref.reference_id

    with Session(annodb.engine) as session:
        existing = session.scalar(
            select(AnnotationSnapshot).where(
                (AnnotationSnapshot.project_id == project_id)
                & (AnnotationSnapshot.user_id == user_id)
                & (AnnotationSnapshot.reference_id == reference_id)
            )
        )
        if existing is not None:
            return

        latest_state = session.scalar(
            select(AnnotationState)
            .where(AnnotationState.project_id == project_id)
            .where(AnnotationState.user_id == user_id)
            .where(AnnotationState.reference_id == reference_id)
            .order_by(AnnotationState.state_id.desc())
            .limit(1)
        )

        content_hash = latest_state.content_hash if latest_state else ""
        snapshot = AnnotationSnapshot(
            project_id=project_id,
            user_id=user_id,
            reference_id=reference_id,
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc),
        )
        session.add(snapshot)
        session.flush()

        if latest_state is not None:
            state_pointers = session.scalars(
                select(StatePointer).where(
                    StatePointer.state_id == latest_state.state_id
                )
            ).all()
            for sp in state_pointers:
                session.add(
                    SnapshotPointer(
                        snapshot_id=snapshot.snapshot_id,
                        reference_id=sp.reference_id,
                        entity_id=sp.entity_id,
                        offset=sp.offset,
                        length=sp.length,
                    )
                )
            state_relations = session.scalars(
                select(StateRelation).where(
                    StateRelation.state_id == latest_state.state_id
                )
            ).all()
            for sr in state_relations:
                session.add(
                    SnapshotRelation(
                        snapshot_id=snapshot.snapshot_id,
                        relation_id=sr.relation_id,
                    )
                )

        session.commit()


def mark_annotation_incomplete(
    project_id: int, user_id: uuid.UUID, ref_identifier: str
) -> None:
    """Delete all AnnotationSnapshot rows for the (project, user, reference) triple."""
    if ref_identifier.startswith("10."):
        ref = annodb.get_reference_by_doi(ref_identifier)
    else:
        try:
            ref = annodb.get_article_by_pubmed_id(int(ref_identifier))
        except (ValueError, TypeError):
            return
    if ref is None:
        return

    with Session(annodb.engine) as session:
        session.execute(
            delete(AnnotationSnapshot).where(
                (AnnotationSnapshot.project_id == project_id)
                & (AnnotationSnapshot.user_id == user_id)
                & (AnnotationSnapshot.reference_id == ref.reference_id)
            )
        )
        session.commit()


def get_curated_annotation(
    project_id: int, reference_id: int, curator_id: uuid.UUID
) -> tuple[list[CuratedAnnotationPointer], list[Relation]]:
    """Return the accepted pointers and relations from this curator's saved
    curated annotation for (project, reference), or empty lists if none."""
    with Session(annodb.engine) as session:
        curated = session.scalar(
            select(CuratedAnnotation)
            .where(CuratedAnnotation.project_id == project_id)
            .where(CuratedAnnotation.reference_id == reference_id)
            .where(CuratedAnnotation.curator_id == curator_id)
        )
        if curated is None:
            return [], []

        pointers = list(
            session.scalars(
                select(CuratedAnnotationPointer).where(
                    CuratedAnnotationPointer.curated_id == curated.curated_id
                )
            ).all()
        )

        relations = list(
            session.scalars(
                select(Relation)
                .join(
                    CuratedAnnotationRelation,
                    CuratedAnnotationRelation.relation_id == Relation.relation_id,
                )
                .where(
                    CuratedAnnotationRelation.curated_id == curated.curated_id
                )
            ).all()
        )

        return pointers, relations
