import pathlib
import uuid
from collections.abc import Iterable, Iterator
from importlib import resources
from typing import Any, Optional

from d3textdb import D3TextDB
from d3textdb.schema import Reference, ReferenceAnnotation, User
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


def create_user(user: User) -> None:
    annodb.create_user(user)


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
