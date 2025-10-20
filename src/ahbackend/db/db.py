import pathlib
from collections.abc import Iterable, Iterator
from importlib import resources
from typing import Any, Optional

from ahbackend.datamodel import (
    Annotation,
    HtmlChunk,
    Response,
    SQLModel,
    Text,
    TextChunk,
)
from d3textdb import D3TextDB
from d3textdb.schema import ReferenceAnnotation, User
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


def add_annotation(
    ann: str,
    force: bool = False,
) -> None:
    annotation = ReferenceAnnotation.model_validate_json(ann)
    try:
        annodb.store_annotation(annotation)
    except IntegrityError:
        if force:
            annodb.update_annotation(annotation)
        else:
            raise


def add_annotations(
    annotations: Iterable[Annotation], force: bool = False
) -> int:
    how_many: int = 0
    for ann in annotations:
        try:
            add_annotation(ann, force=force)
            how_many += 1
        except IntegrityError:
            pass

    return how_many


def get_unannotated(
    annotator: Optional[EmailStr] = None, batch_size: Optional[int] = None
) -> Iterator[Response]:
    if annotator is not None:
        annotated = select(Annotation.chunk).where(
            Annotation.annotator == annotator
        )
    else:
        annotated = select(Annotation.chunk)

    query = (
        select(TextChunk, Text)
        .join(Text)
        .where(col(TextChunk.id).not_in(annotated))
    )

    if batch_size is not None:
        query = query.limit(batch_size)

    with Session(engine) as session:
        results = session.exec(query).all()

    for result in results:
        article = result[1]
        chunk = result[0]
        yield Response(
            article=article,
            chunk=chunk,
            content=chunk.content,
        )


@multimethod
def query(pmid: int, pos: int) -> Response:
    with Session(engine) as session:
        chunk, article = next(
            session.exec(
                select(TextChunk, Text)
                .join(Text)
                .where(Text.pmid == pmid)
                .where(TextChunk.pos == pos)
            )
        )

    return Response(
        article=article,
        chunk=chunk,
        content=chunk.content,
    )


@query.register
def _(predicate: str, subject: str, object: str) -> str:
    relation = annodb.get_relation(
        predicate=predicate, subject=subject, object=object
    )
    if relation is None:
        return ""
    return relation.model_dump_json()


@query.register
def _(annotator: str, annotation_id: int) -> Response:
    """Retrieve the annotated chunk `annotation_id` for `annotator`"""
    with Session(engine) as session:
        annotation, chunk, article = next(
            session.exec(
                select(Annotation, TextChunk, Text)
                .join(TextChunk, TextChunk.id == Annotation.chunk)
                .join(Text, Text.id == TextChunk.source)
                .where(Annotation.id == annotation_id)
            )
        )

    return Response(article=article, chunk=chunk, content=annotation.annotation)


@query.register
def _(pmid: int) -> Response:
    with Session(engine) as session:
        article = next(session.exec(select(Text).where(Text.pmid == pmid)))

    return Response(article=article, chunk=None, content=compile_text(article))


@query.register
def _() -> Response:
    with Session(engine) as session:
        annotation = next(
            session.exec(select(Annotation).order_by(random()).limit(1))
        )
        chunk = next(
            session.exec(
                select(TextChunk)
                .where(TextChunk.id == annotation.chunk)
                .limit(1)
            )
        )
        article = next(
            session.exec(select(Text).where(Text.id == chunk.source).limit(1))
        )

    return Response(article=article, chunk=chunk, content=annotation.annotation)


def compile_text(text: Text) -> str:
    with Session(engine) as session:
        chunks = session.exec(
            select(TextChunk)
            .where(TextChunk.source == text.id)
            .order_by(TextChunk.pos.asc())
        ).all()

    content = "\n".join(ck.content for ck in chunks[1:])
    print(content)

    return transform_article(f"<article>\n{text.meta}\n{content}</article>")


def get_batch(
    annotator_email: EmailStr, batch_size: int
) -> Iterator[HtmlChunk]:
    for item in get_unannotated(annotator_email, batch_size):
        yield response_to_article(item)


def response_to_article(item: Response) -> HtmlChunk:
    content = BertNormalizer(lowercase=False).normalize_str(item.content)

    return HtmlChunk(
        article_id=item.article.id,
        chunk_id=item.chunk.id if item.chunk else None,
        metadata=item.article.meta,
        body=content,
    )
