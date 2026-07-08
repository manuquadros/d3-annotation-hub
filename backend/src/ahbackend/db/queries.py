import uuid

from d3textdb.schema import (
    AnnotationSnapshot,
    AnnotatorSnapshot,
    EntityAnnotation,
    Ontology,
    OntologyProperty,
    Pointer,
    Project,
    ProjectReference,
    Reference,
    ReferenceAnnotation,
    Relation,
    SnapshotPointer,
    SnapshotRelation,
    User,
    UserAuth,
    Verdict,
)
from multimethod import multimethod
from sqlmodel import Session, col, select

from ..utils import cse_citation
from ._annodb import annodb


def _clamp_limit(limit: int) -> int:
    """Guard against SQLite's ``LIMIT -1`` (== unbounded) footgun.

    A zero or negative ``limit`` reaching ``.limit()`` returns the entire table.
    This is defense in depth behind the API-layer ``Query(ge=1, le=…)`` bounds:
    the page-size *cap* stays at the boundary (a 422 there tells the caller),
    so this only enforces the non-negative floor for any internal caller.
    """
    return max(1, limit)


def _clamp_offset(offset: int) -> int:
    return max(0, offset)


def get_user(email: str) -> User | None:
    return annodb.get_user(email)


def search_users(query: str, limit: int = 20) -> list[tuple[User, UserAuth]]:
    with Session(annodb.engine) as session:
        rows = session.execute(
            select(User, UserAuth)
            .join(UserAuth, UserAuth.user_id == User.user_id)
            .where(col(User.email).ilike(f"%{query}%"))
            .limit(_clamp_limit(limit))
        ).all()
        return [(u, a) for u, a in rows]


def get_user_auth(user_id: uuid.UUID) -> UserAuth | None:
    return annodb.get_user_auth(user_id)


def user_has_references(user_id: uuid.UUID) -> bool:
    return annodb.user_has_references(user_id)


def get_reference_by_pubmed_id(pubmed_id: int) -> Reference | None:
    return annodb.get_article_by_pubmed_id(pubmed_id)


def get_reference_by_doi(doi: str) -> Reference | None:
    return annodb.get_reference_by_doi(doi)


def get_reference_by_id(reference_id: int) -> Reference | None:
    with Session(annodb.engine) as session:
        return session.get(Reference, reference_id)


def get_project_reference_ids(project_id: int) -> set[int]:
    return annodb.get_project_reference_ids(project_id)


def list_project_references(project_id: int) -> list[Reference]:
    return annodb.list_project_references(project_id)


def search_entities(
    query: str,
    limit: int = 20,
    project_id: int | None = None,
    is_class: bool = False,
) -> list[EntityAnnotation]:
    return annodb.search_entities(
        query, _clamp_limit(limit), project_id, is_class
    )


def get_entities_by_curies(curies: list[str]) -> list[EntityAnnotation]:
    return annodb.get_entities_by_curies(curies)


def get_entity_project_id(curie: str) -> int | None:
    return annodb.get_entity_project_id(curie)


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
        ontology_id,
        _clamp_limit(limit),
        _clamp_offset(offset),
        curie_filter,
        name_filter,
        type_filter,
    )


def get_ontology_triples(
    ontology_id: int,
    limit: int = 50,
    offset: int = 0,
    subject_filter: str = "",
    predicate_filter: str = "",
    object_filter: str = "",
) -> tuple[list[dict], int]:
    return annodb.get_ontology_triples(
        ontology_id,
        _clamp_limit(limit),
        _clamp_offset(offset),
        subject_filter,
        predicate_filter,
        object_filter,
    )


def get_ontology_properties_by_id(ontology_id: int) -> list[OntologyProperty]:
    return annodb.get_ontology_properties_by_id(ontology_id)


def get_project_properties(project_id: int) -> list[OntologyProperty]:
    return annodb.get_project_properties(project_id)


def list_proposed_properties(
    project_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[dict], int]:
    return annodb.list_proposed_properties(
        project_id, _clamp_limit(limit), _clamp_offset(offset)
    )


def list_proposed_entities(
    project_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[dict], int]:
    return annodb.list_proposed_entities(
        project_id, _clamp_limit(limit), _clamp_offset(offset)
    )


def get_project(project_id: int) -> Project | None:
    return annodb.get_project(project_id)


def list_projects() -> list[Project]:
    return annodb.list_projects()


def list_user_projects(user_id: uuid.UUID) -> list[Project]:
    return annodb.list_user_projects(user_id)


def is_project_creator(user_id: uuid.UUID) -> bool:
    return annodb.is_project_creator(user_id)


def list_users() -> list[tuple[User, UserAuth]]:
    with Session(annodb.engine) as session:
        rows = session.execute(
            select(User, UserAuth).join(
                UserAuth, UserAuth.user_id == User.user_id
            )
        ).all()
        return [(u, a) for u, a in rows]


def get_project_members(project_id: int) -> list[tuple[User, list[str]]]:
    return annodb.get_project_members(project_id)


def get_user_project_roles(user_id: uuid.UUID, project_id: int) -> list[str]:
    return annodb.get_user_project_roles(user_id, project_id)


def get_project_ontologies(project_id: int) -> list[Ontology]:
    return annodb.get_project_ontologies(project_id)


def get_user_last_project(user_id: uuid.UUID) -> int | None:
    return annodb.get_user_last_project(user_id)


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


def get_curation_claims(  # noqa: C901
    project_id: int,
) -> tuple[
    dict[tuple[str, str, str], dict[int, dict[str, set[tuple[int, int]]]]],
    dict[int, Reference],
    set[str],
    dict[tuple[str, str, str], int],
]:
    """Return unique relations from all annotator snapshots for a project.

    Returns a 4-tuple:
    - claims_map: (subject, predicate, object) -> {reference_id -> {
          'subject_pointers': set of (offset, length),
          'object_pointers': set of (offset, length)
      }}
    - refs: reference_id -> Reference
    - entity_curies: CURIEs appearing in any claim
    - relation_ids: (subject, predicate, object) -> relation_id
    """
    with Session(annodb.engine) as session:
        snapshots = session.scalars(
            select(AnnotationSnapshot).where(
                AnnotationSnapshot.project_id == project_id
            )
        ).all()

        if not snapshots:
            return {}, {}, set(), {}

        snapshot_ids = [s.snapshot_id for s in snapshots]
        snap_to_ref: dict[int, int] = {
            s.snapshot_id: s.reference_id for s in snapshots
        }

        rel_rows = session.execute(
            select(Relation, SnapshotRelation.snapshot_id)
            .join(
                SnapshotRelation,
                Relation.relation_id == SnapshotRelation.relation_id,
            )
            .where(col(SnapshotRelation.snapshot_id).in_(snapshot_ids))
        ).all()

        ptr_rows = session.scalars(
            select(SnapshotPointer).where(
                col(SnapshotPointer.snapshot_id).in_(snapshot_ids)
            )
        ).all()

        ptrs_by_snapshot: dict[int, list[SnapshotPointer]] = {}
        for p in ptr_rows:
            ptrs_by_snapshot.setdefault(p.snapshot_id, []).append(p)

        claims_map: dict[
            tuple[str, str, str], dict[int, dict[str, set[tuple[int, int]]]]
        ] = {}
        relation_ids: dict[tuple[str, str, str], int] = {}
        entity_curies: set[str] = set()

        for relation, snap_id in rel_rows:
            key = (relation.subject, relation.predicate, relation.object)
            ref_id = snap_to_ref[snap_id]
            entity_curies.update([relation.subject, relation.object])

            if key not in claims_map:
                claims_map[key] = {}
                relation_ids[key] = relation.relation_id
            if ref_id not in claims_map[key]:
                claims_map[key][ref_id] = {
                    "subject_pointers": set(),
                    "object_pointers": set(),
                }

            for p in ptrs_by_snapshot.get(snap_id, []):
                ptr = (p.offset, p.length)
                if p.entity_id == relation.subject:
                    claims_map[key][ref_id]["subject_pointers"].add(ptr)
                elif p.entity_id == relation.object:
                    claims_map[key][ref_id]["object_pointers"].add(ptr)

        ref_ids = {
            ref_id for evidence in claims_map.values() for ref_id in evidence
        }
        refs: dict[int, Reference] = {}
        if ref_ids:
            for ref in session.scalars(
                select(Reference).where(
                    col(Reference.reference_id).in_(ref_ids)
                )
            ).all():
                refs[ref.reference_id] = ref

        return claims_map, refs, entity_curies, relation_ids


def get_curation_decisions(
    project_id: int, curator_id: uuid.UUID
) -> dict[int, Verdict]:
    return annodb.get_curation_decisions(project_id, curator_id)


def get_reference_annotation(
    ref_identifier: str, user_id: str, project_id: int
) -> ReferenceAnnotation:
    return annodb.get_reference_annotation(
        int(ref_identifier), uuid.UUID(user_id), project_id
    )


def get_project_queue_with_status(
    project_id: int, user_id: uuid.UUID
) -> list[tuple[str, str, bool]]:
    """Return all project references with completion status for the user.

    Returns a list of (identifier, citation, completed) tuples where identifier
    is the pubmed_id string when available, otherwise the doi, and citation is
    a CSE-style key (e.g. "Smith et al. 2004").
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
            select(
                Reference.pubmed_id,
                Reference.doi,
                Reference.reference_id,
                Reference.authors,
                Reference.year,
            )
            .join(
                ProjectReference,
                ProjectReference.reference_id == Reference.reference_id,
            )
            .where(ProjectReference.project_id == project_id)
        ).all()
        return [
            (
                str(pubmed_id) if pubmed_id is not None else doi,
                cse_citation(authors, year),
                ref_id in completed_ref_ids,
            )
            for pubmed_id, doi, ref_id, authors, year in rows
        ]


def get_curated_annotation(
    project_id: int, reference_id: int, curator_id: uuid.UUID
) -> tuple[list[Pointer], list[Relation]]:
    result = annodb.get_curated_annotation(project_id, reference_id, curator_id)
    if result is None:
        return [], []
    return result.pointers, result.relations


@multimethod
def query(pmid: int) -> Reference:
    return annodb.get_article_by_pubmed_id(pmid)


@multimethod
def query(predicate: str, subject: str, object: str) -> str:  # noqa: F811
    relation = annodb.get_relation(
        predicate=predicate, subject=subject, object=object
    )
    if relation is None:
        return ""
    return relation.model_dump_json()
