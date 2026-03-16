import pathlib
import uuid
from collections.abc import Iterable, Iterator
from importlib import resources
from typing import Any, Optional

from d3textdb import D3TextDB, ParsedOntology
from d3textdb.schema import (
    AnnotationSnapshot,
    EntityAnnotation,
    Ontology,
    Reference,
    ReferenceAnnotation,
    User,
    UserAuth,
)
from multimethod import multimethod
from pydantic import EmailStr
from rich import print
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.functions import random
from sqlmodel import Session, col, create_engine, select
from tokenizers.normalizers import BertNormalizer
from xmlparser import transform_article

db_path = resources.files("ahbackend.db") / "database.db"
annodb = D3TextDB(db_path, echo=True)


def get_user(email: EmailStr) -> User | None:
    return annodb.get_user(email)


def get_user_auth(user_id: uuid.UUID) -> UserAuth | None:
    return annodb.get_user_auth(user_id)


def create_user(user: User, role: str = "annotator") -> None:
    annodb.create_user(user, role)


def search_entities(
    query: str, limit: int = 20, project_id: int | None = None
) -> list[EntityAnnotation]:
    return annodb.search_entities(query, limit, project_id)


def get_entity_types(query: str = "") -> list[EntityAnnotation]:
    return annodb.get_entity_types(query)


def list_ontologies() -> list[Ontology]:
    return annodb.list_ontologies()


def get_ontology_entities(
    ontology_id: int, limit: int = 50, offset: int = 0
) -> tuple[list[EntityAnnotation], int]:
    return annodb.get_ontology_entities(ontology_id, limit, offset)


def delete_ontology(ontology_id: int) -> None:
    annodb.delete_ontology(ontology_id)


def run_ontology_import(
    parsed: ParsedOntology,
    name: str,
    prefix: str,
    base_iri: str,
    version: str | None,
) -> dict[str, int]:
    """Store ontology metadata, bulk-load entities and triples.

    Returns a summary dict with ``ontology_id``, ``entities``, ``triples``.
    """
    ontology_id = annodb.store_ontology(
        name=name, prefix=prefix, uri=base_iri, version=version
    )
    entity_count = annodb.load_ontology_entities(ontology_id, parsed.entities)
    triple_count = annodb.load_ontology_triples(parsed.triples)
    return {
        "ontology_id": ontology_id,
        "entities": entity_count,
        "triples": triple_count,
    }


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


@query.register
def _(ref_identifier: str, user: str) -> ReferenceAnnotation:
    return annodb.get_reference_annotation(int(ref_identifier), uuid.UUID(user))


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
