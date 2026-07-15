"""Declaration of the database schema."""

import enum
from datetime import UTC, datetime
from typing import TypedDict
from uuid import UUID, uuid4

import pendulum
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.types import BINARY, String, TypeDecorator
from sqlmodel import (
    Column,
    Field,
    ForeignKey,
    Index,
    Relationship,
    SQLModel,
    UniqueConstraint,
)


class Verdict(str, enum.Enum):
    accepted = "accepted"
    rejected = "rejected"


class PdfIngestStatus(str, enum.Enum):
    pending = "pending"
    leased = "leased"
    done = "done"
    failed = "failed"


class SqliteUUID(TypeDecorator):
    impl = BINARY(16)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.bytes if isinstance(value, UUID) else UUID(value).bytes

    def process_result_value(self, value, dialect):
        return None if value is None else UUID(bytes=bytes(value))


class SqliteDatetime(TypeDecorator):
    """Stores a pendulum.DateTime as an ISO 8601 string in SQLite."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else value.isoformat()

    def process_result_value(self, value, dialect):
        return None if value is None else pendulum.parse(value)


class Ontology(SQLModel, table=True):
    """An ontology whose entities are available for annotation."""

    ontology_id: int | None = Field(default=None, primary_key=True)
    name: str
    prefix: str = Field(index=True, unique=True)  # e.g. "NCBITaxon"
    uri: str  # canonical IRI / namespace
    version: str | None = None


class Project(SQLModel, table=True):
    """An annotation project grouping references, users, and ontologies.

    :cvar required_annotators: Number of independent annotator completions
        required before a reference becomes available for curation. Default 2.
    """

    project_id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    required_annotators: int = Field(default=2)
    archived_at: datetime | None = Field(default=None, index=True)


class ProjectMembership(SQLModel, table=True):
    """Project-scoped role assignment for a user.

    Roles are not mutually exclusive: a user may have multiple rows for the
    same (project, user) pair with different roles. Current roles are
    ``"manager"``, ``"annotator"``, and ``"curator"``.
    """

    __tablename__ = "project_membership"

    project_id: int = Field(foreign_key="project.project_id", primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            SqliteUUID,
            ForeignKey("user.user_id"),
            nullable=False,
            primary_key=True,
        )
    )
    role: str = Field(primary_key=True)


class ProjectOntology(SQLModel, table=True):
    """Association table: which ontologies are available in a project."""

    __tablename__ = "project_ontology"

    project_id: int = Field(foreign_key="project.project_id", primary_key=True)
    ontology_id: int = Field(
        foreign_key="ontology.ontology_id", primary_key=True
    )


class ProjectReference(SQLModel, table=True):
    """Association table: which references belong to a project."""

    __tablename__ = "project_reference"

    project_id: int = Field(foreign_key="project.project_id", primary_key=True)
    reference_id: int = Field(
        foreign_key="reference.reference_id", primary_key=True
    )


class UserLastProject(SQLModel, table=True):
    """Tracks the most recently active project for each user."""

    __tablename__ = "user_last_project"

    user_id: UUID = Field(
        sa_column=Column(
            SqliteUUID,
            ForeignKey("user.user_id"),
            nullable=False,
            primary_key=True,
        )
    )
    project_id: int = Field(foreign_key="project.project_id")


class Entity(SQLModel, table=True):
    """A canonical entity (gene, taxon, chemical, …) or an annotator proposal.

    ``curie`` is the compact URI used as a stable public identifier
    (e.g. ``"NCBITaxon:562"``). Annotation-facing tables (Pointer, Relation,
    …) reference Entity by curie (str), not by the internal integer PK.

    Confirmed ontology entities have ``confirmed=True`` and a non-null
    ``ontology_id``.  Annotator-proposed entities have ``confirmed=False``,
    ``ontology_id=None``, and carry project-scoping metadata in
    ``project_id``, ``proposed_by``, ``proposal_status``, and
    ``proposed_at``.
    """

    entity_id: int | None = Field(default=None, primary_key=True)
    curie: str | None = Field(index=True, unique=True)
    type: str
    ontology_id: int | None = Field(
        default=None, foreign_key="ontology.ontology_id", index=True
    )
    confirmed: bool = Field(default=True, index=True)
    is_class: bool = Field(default=False, index=True)
    # Proposal metadata — only set for unconfirmed (annotator-coined) entities.
    project_id: int | None = Field(
        default=None, foreign_key="project.project_id", index=True
    )
    proposed_by: str | None = None
    proposal_status: str | None = Field(
        default=None, index=True
    )  # 'pending' | 'accepted' | 'rejected' | None for confirmed
    proposed_at: datetime | None = None


class Name(SQLModel, table=True):
    """A normalised name/synonym string, shared across entities."""

    id: int | None = Field(default=None, primary_key=True)
    label: str = Field(index=True, unique=True)


class EntityName(SQLModel, table=True):
    """Association table mapping names/synonyms to entities.

    The same Name can belong to multiple entities (homonyms). The
    ``is_preferred`` flag marks the single preferred display name.
    """

    __table_args__ = (UniqueConstraint("entity_id", "name_id"),)

    id: int | None = Field(default=None, primary_key=True)
    entity_id: int = Field(foreign_key="entity.entity_id")
    # Standalone index (the composite unique is led by entity_id, so it can't
    # serve name_id lookups) — search_entities joins Name -> EntityName by
    # name_id off the FTS match set on every search-as-you-type keystroke.
    name_id: int = Field(foreign_key="name.id", index=True)
    is_preferred: bool = False


class OntologyProperty(SQLModel, table=True):
    """An OWL object property defined in an ontology.

    Stores the property's CURIE, a human-readable label, and optional
    ``rdfs:domain`` / ``rdfs:range`` class CURIEs extracted from the OWL file.
    """

    __tablename__ = "ontology_property"
    __table_args__ = (UniqueConstraint("ontology_id", "curie"),)

    property_id: int | None = Field(default=None, primary_key=True)
    ontology_id: int = Field(foreign_key="ontology.ontology_id", index=True)
    curie: str = Field(index=True)  # e.g. "d3o:hasSpecies"
    label: str  # human-readable label, e.g. "has species"
    domain_curie: str | None = None  # e.g. "d3o:Strain"
    range_curie: str | None = None  # e.g. "d3o:Bacteria"


class ProposedProperty(SQLModel, table=True):
    """An object property proposed by an annotator within a project.

    Project-scoped; never touches the ontology tables until a manager
    explicitly promotes it via an ontology-modification workflow.
    """

    __tablename__ = "proposed_property"

    proposal_id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", index=True)
    label: str
    curie: str | None = None
    domain_curie: str | None = None
    range_curie: str | None = None
    proposed_by: str | None = None  # user e-mail / username
    status: str = Field(
        default="pending", index=True
    )  # pending|accepted|rejected
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Triple(SQLModel, table=True):
    """An ontology-defined fact (hierarchy, equivalence, data property, …).

    Both ``object_id`` and ``object_literal`` may be null for existential
    restrictions; for data properties only ``object_literal`` is set.
    """

    __table_args__ = (UniqueConstraint("subject_id", "predicate", "object_id"),)

    triple_id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="entity.entity_id", index=True)
    predicate: str = Field(
        index=True
    )  # e.g. "rdfs:subClassOf", "skos:exactMatch"
    object_id: int | None = Field(
        default=None, foreign_key="entity.entity_id", index=True
    )
    object_literal: str | None = None  # for data properties / definitions


class Reference(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("pubmed_id"),
        UniqueConstraint("doi"),
    )

    reference_id: int | None = Field(default=None, primary_key=True)
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


class PdfIngestJob(SQLModel, table=True):
    """One parse of a distinct PDF into a (global) Reference, run by the worker.

    Keyed on ``pdf_sha256`` (one job per distinct PDF, ever): a Reference is
    shared across projects, so the article is OCR'd once, not once per project.
    Which projects requested it lives in ``PdfJobProject``; the worker links the
    resulting Reference to all of them on completion, and every subscribed
    manager sees this one shared status. Keys on the *source* bytes, never the
    parsed HTML — OCR output is non-deterministic, so hashing the render would
    never dedup.
    """

    __tablename__ = "pdf_ingest_job"

    job_id: int | None = Field(default=None, primary_key=True)
    pdf_sha256: str = Field(unique=True)
    source_path: str
    status: PdfIngestStatus = Field(default=PdfIngestStatus.pending)
    attempts: int = Field(default=0)
    error: str | None = None
    reference_id: int | None = Field(
        default=None, foreign_key="reference.reference_id"
    )
    leased_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # onupdate so a status transition advances updated_at on its own —
    # the worker never has to remember to set it.
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )


class PdfJobProject(SQLModel, table=True):
    """Association: which projects requested a given PDF ingest job."""

    __tablename__ = "pdf_job_project"

    job_id: int = Field(foreign_key="pdf_ingest_job.job_id", primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", primary_key=True)


class Pointer(SQLModel, table=True):
    """Text span identifying an entity within a reference.

    The composite primary key ensures the same (reference, entity, span)
    triple is stored only once regardless of how many users annotate it.
    User attribution lives at the AnnotationState / AnnotationSnapshot level.

    ``entity_id`` stores the entity's CURIE (FK → entity.curie).
    ``field`` is either ``"abstract"`` or ``"body"``, scoping the offset to the
    corresponding HTML field of the reference.
    ``exact_text``, ``prefix_text``, and ``suffix_text`` implement the W3C
    TextQuoteSelector, allowing re-anchoring if the HTML is regenerated
    differently.
    """

    reference_id: int = Field(
        foreign_key="reference.reference_id", primary_key=True
    )
    # ON UPDATE CASCADE so renaming entity.curie propagates here with FK
    # enforcement left on (no PRAGMA foreign_keys toggling in the rename).
    entity_id: str = Field(
        sa_column=Column(
            String,
            ForeignKey("entity.curie", onupdate="CASCADE"),
            primary_key=True,
        )
    )
    offset: int = Field(primary_key=True)
    length: int = Field(primary_key=True)
    field: str = Field(default="body", primary_key=True)
    exact_text: str = ""
    prefix_text: str = ""
    suffix_text: str = ""


class Relation(SQLModel, table=True):
    """Represents a user-annotated relation between two entities."""

    __table_args__ = (UniqueConstraint("predicate", "subject", "object"),)
    model_config = ConfigDict(coerce_numbers_to_str=True)

    relation_id: int | None = Field(default=None, primary_key=True)
    predicate: str
    # ON UPDATE CASCADE — see Pointer.entity_id.
    subject: str = Field(
        sa_column=Column(String, ForeignKey("entity.curie", onupdate="CASCADE"))
    )
    object: str = Field(
        sa_column=Column(String, ForeignKey("entity.curie", onupdate="CASCADE"))
    )
    relation_references: list["UserRelationReference"] = Relationship()


class UserRelationReference(SQLModel, table=True):
    """Association table mapping users and literature references to
    relations."""

    __tablename__ = "user_relation_reference"
    user_id: UUID = Field(
        sa_column=Column(
            SqliteUUID,
            ForeignKey("user.user_id"),
            nullable=False,
            primary_key=True,
        ),
    )
    relation_id: int = Field(
        foreign_key="relation.relation_id", primary_key=True
    )
    reference_id: int = Field(
        foreign_key="reference.reference_id", primary_key=True
    )
    relation: Relation = Relationship(back_populates="relation_references")


class User(SQLModel, table=True):
    """Represents a user (annotator, curator, or project manager)."""

    user_id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(SqliteUUID, primary_key=True),
    )
    email: EmailStr = Field(unique=True)


class UserAuth(SQLModel, table=True):
    """Authentication credentials and system-level permissions.

    Two independent permission flags govern system-level access:

    - ``is_super_user`` — full system access: user management and everything
      ``can_manage`` implies.
    - ``can_manage`` — can create projects and access the administration
      interface before any project is assigned.

    Project-scoped roles (``"annotator"``, ``"curator"``, ``"manager"``)
    are stored separately in :class:`ProjectMembership` and govern
    per-project permissions.
    """

    user_id: UUID = Field(
        sa_column=Column(
            SqliteUUID,
            ForeignKey(column="user.user_id"),
            primary_key=True,
        )
    )
    hashed_password: str
    is_super_user: bool = Field(default=False)
    can_manage: bool = Field(default=False)
    disabled: bool = Field(default=False)


class Annotation(TypedDict):
    """A single annotation state: the complete set of pointers and relations
    at one point in the editing history."""

    pointers: tuple[Pointer, ...]
    relations: tuple[Relation, ...]


class AnnotationHistory(TypedDict):
    """In-memory annotation history for a (user, reference) pair.

    ``states`` grows as the user makes edits. ``saved`` is the timestamp of
    the last sync to the persistent database; ``None`` if never synced.
    """

    user_id: UUID
    reference_id: int
    states: list[Annotation]
    saved: pendulum.DateTime | None


class AnnotationState(SQLModel, table=True):
    """One row per annotation state persisted to the database.

    The auto-incrementing ``state_id`` doubles as an ordering key: the
    highest ``state_id`` for a given (user, reference, project) triple is
    the most recently persisted state.
    """

    __tablename__ = "annotation_state"
    # Latest-state lookup (annotation-open, mark-complete) seeks this triple
    # and takes the highest state_id; the implicit trailing rowid means the
    # ORDER BY state_id DESC LIMIT 1 is a seek, not a sort.
    __table_args__ = (
        Index(
            "ix_annotation_state_project_id_user_id_reference_id",
            "project_id",
            "user_id",
            "reference_id",
        ),
    )

    state_id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", index=True)
    user_id: UUID = Field(
        sa_column=Column(SqliteUUID, ForeignKey("user.user_id"), nullable=False)
    )
    reference_id: int = Field(foreign_key="reference.reference_id")
    content_hash: str
    recorded_at: datetime = Field(
        sa_column=Column(SqliteDatetime, nullable=False)
    )


class StatePointer(SQLModel, table=True):
    """Association table recording which Pointers belong to an
    AnnotationState."""

    __tablename__ = "state_pointer"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reference_id", "entity_id", "offset", "length", "field"],
            [
                "pointer.reference_id",
                "pointer.entity_id",
                "pointer.offset",
                "pointer.length",
                "pointer.field",
            ],
        ),
    )

    state_id: int = Field(
        foreign_key="annotation_state.state_id", primary_key=True
    )
    reference_id: int = Field(primary_key=True)
    entity_id: str = Field(primary_key=True)
    offset: int = Field(primary_key=True)
    length: int = Field(primary_key=True)
    field: str = Field(default="body", primary_key=True)


class StateRelation(SQLModel, table=True):
    """Association table recording which Relations belong to an
    AnnotationState."""

    __tablename__ = "state_relation"

    state_id: int = Field(
        foreign_key="annotation_state.state_id", primary_key=True
    )
    relation_id: int = Field(
        foreign_key="relation.relation_id", primary_key=True
    )


class AnnotationSnapshot(SQLModel, table=True):
    """Immutable record created when a user marks their annotation as complete,
    provided the content hash differs from the previous snapshot for the same
    (user, reference, project) triple.
    """

    __tablename__ = "annotation_snapshot"
    # Latest-snapshot lookup (completion check) seeks this triple and takes the
    # highest snapshot_id; the trailing rowid keeps it a seek, not a sort.
    __table_args__ = (
        Index(
            "ix_annotation_snapshot_project_id_user_id_reference_id",
            "project_id",
            "user_id",
            "reference_id",
        ),
    )

    snapshot_id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", index=True)
    user_id: UUID = Field(
        sa_column=Column(SqliteUUID, ForeignKey("user.user_id"), nullable=False)
    )
    reference_id: int = Field(foreign_key="reference.reference_id")
    content_hash: str
    created_at: datetime = Field(
        sa_column=Column(SqliteDatetime, nullable=False)
    )


class SnapshotPointer(SQLModel, table=True):
    """Association table recording which Pointers belong to an
    AnnotationSnapshot."""

    __tablename__ = "snapshot_pointer"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reference_id", "entity_id", "offset", "length", "field"],
            [
                "pointer.reference_id",
                "pointer.entity_id",
                "pointer.offset",
                "pointer.length",
                "pointer.field",
            ],
        ),
    )

    snapshot_id: int = Field(
        foreign_key="annotation_snapshot.snapshot_id", primary_key=True
    )
    reference_id: int = Field(primary_key=True)
    entity_id: str = Field(primary_key=True)
    offset: int = Field(primary_key=True)
    length: int = Field(primary_key=True)
    field: str = Field(default="body", primary_key=True)


class SnapshotRelation(SQLModel, table=True):
    """Association table recording which Relations belong to an
    AnnotationSnapshot."""

    __tablename__ = "snapshot_relation"

    snapshot_id: int = Field(
        foreign_key="annotation_snapshot.snapshot_id", primary_key=True
    )
    relation_id: int = Field(
        foreign_key="relation.relation_id", primary_key=True
    )


class CuratedAnnotation(SQLModel, table=True):
    """Immutable curated annotation produced by a curator for a given
    (project, reference) pair.

    Each curator produces their own curated annotation independently; it is
    possible for curators to disagree on their final products.
    """

    __tablename__ = "curated_annotation"

    curated_id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.project_id", index=True)
    reference_id: int = Field(foreign_key="reference.reference_id")
    curator_id: UUID = Field(
        sa_column=Column(SqliteUUID, ForeignKey("user.user_id"), nullable=False)
    )
    content_hash: str
    created_at: datetime = Field(
        sa_column=Column(SqliteDatetime, nullable=False)
    )


class CuratedAnnotationPointer(SQLModel, table=True):
    """Association table recording which Pointers belong to a
    CuratedAnnotation."""

    __tablename__ = "curated_annotation_pointer"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reference_id", "entity_id", "offset", "length", "field"],
            [
                "pointer.reference_id",
                "pointer.entity_id",
                "pointer.offset",
                "pointer.length",
                "pointer.field",
            ],
        ),
    )

    curated_id: int = Field(
        foreign_key="curated_annotation.curated_id", primary_key=True
    )
    reference_id: int = Field(primary_key=True)
    entity_id: str = Field(primary_key=True)
    offset: int = Field(primary_key=True)
    length: int = Field(primary_key=True)
    field: str = Field(default="body", primary_key=True)


class CuratedAnnotationRelation(SQLModel, table=True):
    """Association table recording which Relations belong to a
    CuratedAnnotation."""

    __tablename__ = "curated_annotation_relation"

    curated_id: int = Field(
        foreign_key="curated_annotation.curated_id", primary_key=True
    )
    relation_id: int = Field(
        foreign_key="relation.relation_id", primary_key=True
    )


class CurationDecision(SQLModel, table=True):
    """Curator's accept/reject verdict on a relation triple within a project.

    Composite PK (project_id, relation_id, curator_id) — one verdict per
    curator per triple per project; repeated calls upsert in place.
    """

    __tablename__ = "curation_decision"

    project_id: int = Field(foreign_key="project.project_id", primary_key=True)
    relation_id: int = Field(
        foreign_key="relation.relation_id", primary_key=True
    )
    curator_id: UUID = Field(
        sa_column=Column(
            SqliteUUID,
            ForeignKey("user.user_id"),
            nullable=False,
            primary_key=True,
        )
    )
    verdict: Verdict = Field(sa_column=Column(SAEnum(Verdict), nullable=False))
    decided_at: datetime = Field(
        sa_column=Column(SqliteDatetime, nullable=False)
    )


class EntityAnnotation(BaseModel):
    """Entity as returned to / accepted from the frontend.

    ``entity_id`` maps to ``Entity.curie`` (the stable public identifier).
    ``preferred_name`` is derived from the EntityName row where
    ``is_preferred=True``. ``synonyms`` are all other EntityName labels for
    this entity.
    """

    entity_id: str  # CURIE, e.g. "NCBITaxon:562"
    preferred_name: str
    uri: str | None = None
    kind: str
    synonyms: list[str] = []
    confirmed: bool = True
    is_class: bool = False


class ReferenceAnnotation(BaseModel):
    """Represents the annotations made to a literature reference."""

    user: User
    reference: Reference
    entities: list[EntityAnnotation] = []
    pointers: list[Pointer] = []
    relations: list[Relation] = []
    completed: bool = False
    # Set by the database on write; None for a brand-new annotation.
    last_updated: datetime | None = None
    project_id: int


class AnnotatorSnapshot(BaseModel):
    """All completed annotations for one annotator on a reference.

    Used during curator review to compare annotations across annotators.
    Disagreements in pointer coverage are identified by the caller.
    """

    user: User
    reference_id: int
    pointers: list[Pointer] = []
    relations: list[Relation] = []
    created_at: datetime
