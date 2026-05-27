from collections.abc import Iterable
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from d3textdb import ParsedOntology, ParsedProperty, ParsedTriple
from d3textdb.schema import (
    AnnotationSnapshot,
    AnnotationState,
    EntityAnnotation,
    Pointer,
    Reference,
    ReferenceAnnotation,
    Relation,
    SnapshotPointer,
    SnapshotRelation,
    StatePointer,
    StateRelation,
    User,
    UserAuth,
    Verdict,
)
from sqlalchemy import or_
from sqlmodel import Session, col, delete, select

from ._annodb import annodb


def create_user(user: User, password: str) -> UUID | None:
    return annodb.create_user(user, password)


def disable_user(user_id: UUID) -> None:
    annodb.disable_user(user_id)


def delete_user(user_id: UUID) -> None:
    annodb.delete_user(user_id)


def update_password(user_id: UUID, new_password: str) -> None:
    annodb.update_password(user_id, new_password)


def set_user_permissions(
    user_id: UUID, is_super_user: bool, can_manage: bool
) -> None:
    with Session(annodb.engine) as session:
        auth = session.get(UserAuth, user_id)
        if auth is None:
            raise ValueError(f"No auth record for user_id {user_id}")
        auth.is_super_user = is_super_user
        auth.can_manage = can_manage
        session.add(auth)
        session.commit()


def store_reference(reference: Reference) -> int:
    return annodb.store_reference(reference)


def upsert_annotation(annotation: ReferenceAnnotation) -> None:
    annodb.store_annotation(annotation)


def create_project(
    name: str,
    description: str | None = None,
    required_annotators: int = 2,
) -> int:
    return annodb.create_project(name, description, required_annotators)


def archive_project(project_id: int) -> None:
    annodb.archive_project(project_id)


def add_project_member(project_id: int, user_id: UUID, role: str) -> None:
    annodb.add_project_member(project_id, user_id, role)


def remove_project_member(project_id: int, user_id: UUID, role: str) -> None:
    annodb.remove_project_member(project_id, user_id, role)


def remove_all_project_roles(project_id: int, user_id: UUID) -> None:
    annodb.remove_all_project_member_roles(project_id, user_id)


def assign_ontology_to_project(project_id: int, ontology_id: int) -> None:
    annodb.assign_ontology_to_project(project_id, ontology_id)


def remove_ontology_from_project(project_id: int, ontology_id: int) -> None:
    annodb.remove_ontology_from_project(project_id, ontology_id)


def add_reference_to_project(project_id: int, reference_id: int) -> None:
    annodb.add_reference_to_project(project_id, reference_id)


def remove_reference_from_project(project_id: int, reference_id: int) -> None:
    annodb.remove_reference_from_project(project_id, reference_id)


def set_user_last_project(user_id: UUID, project_id: int) -> None:
    annodb.set_user_last_project(user_id, project_id)


def store_proposed_entity(
    project_id: int,
    label: str,
    curie: str,
    kind: str,
    proposed_by: str | None = None,
) -> dict:
    return annodb.store_proposed_entity(
        project_id, label, curie, kind, proposed_by
    )


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
    property_count = annodb.load_ontology_properties(
        ontology_id, parsed.properties
    )
    return {
        "ontology_id": ontology_id,
        "entities": entity_count,
        "triples": triple_count,
        "properties": property_count,
    }


def store_ontology_metadata(
    name: str, prefix: str, base_iri: str, version: str | None
) -> int:
    return annodb.store_ontology(
        name=name, prefix=prefix, uri=base_iri, version=version
    )


def load_entities_bulk(
    ontology_id: int, entities: Iterable[EntityAnnotation]
) -> int:
    return annodb.load_ontology_entities(ontology_id, entities)


def load_triples_bulk(triples: list[ParsedTriple]) -> int:
    return annodb.load_ontology_triples(triples)


def load_properties_bulk(
    ontology_id: int, properties: list[ParsedProperty]
) -> int:
    return annodb.load_ontology_properties(ontology_id, properties)


def delete_ontology(ontology_id: int) -> None:
    annodb.delete_ontology(ontology_id)


def confirm_entity(curie: str) -> None:
    annodb.confirm_entity(curie)


def delete_entity(curie: str) -> None:
    annodb.delete_entity(curie)


def update_entity_curie(old_curie: str, new_curie: str) -> None:
    annodb.update_entity_curie(old_curie, new_curie)


def rebuild_fts() -> None:
    annodb.rebuild_fts()


def set_curation_decision(
    project_id: int,
    relation_id: int,
    curator_id: UUID,
    verdict: Verdict,
) -> None:
    annodb.set_curation_decision(project_id, relation_id, curator_id, verdict)


def save_curated_annotation(
    project_id: int,
    reference_id: int,
    curator_id: UUID,
    pointers: list[Pointer],
    relations: list[Relation],
) -> int:
    # Drop any pointers that don't exist in the pointer table; guards against
    # FK violations if the caller sends stale or example data.
    if pointers:
        with Session(annodb.engine) as session:
            existing = set(
                session.execute(
                    select(
                        Pointer.reference_id,
                        Pointer.entity_id,
                        Pointer.offset,
                        Pointer.length,
                    ).where(
                        or_(
                            *(
                                (Pointer.reference_id == p.reference_id)
                                & (Pointer.entity_id == p.entity_id)
                                & (Pointer.offset == p.offset)
                                & (Pointer.length == p.length)
                                for p in pointers
                            )
                        )
                    )
                ).all()
            )
            pointers = [
                p
                for p in pointers
                if (p.reference_id, p.entity_id, p.offset, p.length) in existing
            ]

    return annodb.save_curated_annotation(
        project_id, reference_id, curator_id, pointers, relations
    )


def _resolve_reference(ref_identifier: str) -> Reference | None:
    if ref_identifier.startswith("10."):
        return annodb.get_reference_by_doi(ref_identifier)
    try:
        return annodb.get_article_by_pubmed_id(int(ref_identifier))
    except (ValueError, TypeError):
        return None


def mark_annotation_complete(
    project_id: int, user_id: UUID, ref_identifier: str
) -> None:
    """Idempotent: does nothing if a snapshot already exists for the (project, user, reference) triple."""
    ref = _resolve_reference(ref_identifier)
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
                        field=sp.field,
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
    project_id: int, user_id: UUID, ref_identifier: str
) -> None:
    """Delete all AnnotationSnapshot rows for the (project, user, reference) triple."""
    ref = _resolve_reference(ref_identifier)
    if ref is None:
        return

    with Session(annodb.engine) as session:
        snapshot_ids = list(
            session.scalars(
                select(AnnotationSnapshot.snapshot_id).where(
                    (AnnotationSnapshot.project_id == project_id)
                    & (AnnotationSnapshot.user_id == user_id)
                    & (AnnotationSnapshot.reference_id == ref.reference_id)
                )
            ).all()
        )
        if snapshot_ids:
            session.execute(
                delete(SnapshotPointer).where(
                    col(SnapshotPointer.snapshot_id).in_(snapshot_ids)
                )
            )
            session.execute(
                delete(SnapshotRelation).where(
                    col(SnapshotRelation.snapshot_id).in_(snapshot_ids)
                )
            )
            session.execute(
                delete(AnnotationSnapshot).where(
                    col(AnnotationSnapshot.snapshot_id).in_(snapshot_ids)
                )
            )
        session.commit()
