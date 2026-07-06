from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from d3textdb import D3TextDB, OntologyInUseError
from d3textdb.schema import (
    Entity,
    EntityAnnotation,
    Pointer,
    Reference,
    ReferenceAnnotation,
    Relation,
    User,
)

_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def ref_annotations(project_id: int):
    ref15117974 = Reference(
        authors=(
            "Bhakta, S.; Besra, G.S.; Upton, A.M.; Parish, T.; "
            "Sholto-Douglas-Vernon, C.; Gibson, K.J.; Knutton, S.; Gordon, S.;"
            " daSilva, R.P.; Anderton, M.C.; Sim, E."
        ),
        title=(
            "Arylamine N-acetyltransferase is required for synthesis of mycolic "
            "acids and complex lipids in Mycobacterium bovis BCG and represents "
            "a novel drug target"
        ),
        journal="J. Exp. Med.",
        volume="199",
        pages="1191-1199",
        year=2004,
        pubmed_id=15117974,
        pmc_id=2211905,
        pmc_open=True,
        doi="10.1084/jem.20031956",
        abstract=(
            "Mycolic acids represent a major component of the unique cell "
            "wall of mycobacteria. Mycolic acid biosynthesis is inhibited by "
            "isoniazid, a key frontline antitubercular drug that is"
            " inactivated by mycobacterial and human arylamine"
            " N-acetyltransferase (NAT). We show that an in-frame deletion"
            " of Mycobacterium bovis BCG nat results in delayed entry into"
            " log phase, altered morphology, altered cell wall lipid"
            " composition, and increased intracellular killing by"
            " macrophages. In particular, deletion of nat perturbs"
            " biosynthesis of mycolic acids and their derivatives and"
            " increases susceptibility of M. bovis BCG to antibiotics that"
            " permeate the cell wall. Phenotypic traits are fully"
            " complemented by introduction of Mycobacterium tuberculosis nat."
            " We infer from our findings that NAT is critical to normal "
            "mycolic acid synthesis and hence other derivative cell wall"
            " components and represents a novel target for antituberculosis "
            "therapy. In addition, this is the first report of an endogenous "
            "role for NAT in mycobacteria."
        ),
        body=(
            '<jats:body xmlns:jats="https://jats.nlm.nih.gov/ns/archiving/1.3/">'
            "<jats:sec><jats:p>Genes encoding NAT are present in a range of "
            'bacterial genomes (<jats:xref ref-type="bibr" rid="bib15">15'
            '</jats:xref>, <jats:xref ref-type="bibr" rid="bib16">16</jats:xref>). '
            "This observation first provoked intrigue because human NATs have long"
            " been identified as drug metabolizing enzymes (<jats:xref"
            ' ref-type="bibr" rid="bib17">17</jats:xref>). NAT represents one of'
            " the first examples of pharmacogenetic variation and its study "
            "revealed the role of acetyl-CoA as an acetyl donor. In particular, "
            "NAT2 in humans is known to be responsible for the inactivation of"
            ' INH through acetylation (<jats:xref ref-type="bibr"'
            ' rid="bib18">18</jats:xref>-<jats:xref ref-type="bibr" rid="bib20">20'
            "</jats:xref>). We have studied mycobacterial NATs in this laboratory "
            "as potential contributors to the variation in INH resistance among"
            " <jats:italic>M. tuberculosis</jats:italic> clinical isolates. It is"
            " now known that <jats:italic>nat</jats:italic> in <jats:italic>M."
            ' tuberculosis</jats:italic> is polymorphic (<jats:xref ref-type="bibr"'
            ' rid="bib14">14</jats:xref>). The expression product acetylates and'
            " inactivates INH in vitro, and it has been suggested that this"
            " activity and polymorphism might be a contributory factor to INH"
            ' resistance (<jats:xref ref-type="bibr" rid="bib14">14</jats:xref>, '
            '<jats:xref ref-type="bibr" rid="bib15">15</jats:xref>, <jats:xref'
            ' ref-type="bibr" rid="bib21">21</jats:xref>). We know that'
            " <jats:italic>nat</jats:italic> is expressed in <jats:italic>M."
            " tuberculosis</jats:italic> and <jats:italic>Mycobacterium bovis"
            "</jats:italic> BCG and the gene product is active"
            ' (<jats:xref ref-type="bibr" rid="bib14">14</jats:xref>). The genomes'
            " of <jats:italic>M. tuberculosis</jats:italic> (<jats:xref"
            ' ref-type="bibr" rid="bib22">22</jats:xref>) and <jats:italic>M. '
            'bovis</jats:italic> (<jats:xref ref-type="bibr" rid="bib23">23'
            "</jats:xref>) have been sequenced. <jats:italic>M. bovis</jats:italic>"
            " is a member of the <jats:italic>M. tuberculosis</jats:italic> "
            "complex. <jats:italic>M. bovis</jats:italic> BCG is an attenuated "
            "<jats:italic>M. bovis</jats:italic> strain in use as a vaccine. The"
            " <jats:italic>nat</jats:italic> gene is maintained in <jats:italic>"
            "M. bovis</jats:italic> BCG and is identical in sequence to that of"
            " <jats:italic>M. tuberculosis</jats:italic> (<jats:xref "
            'ref-type="bibr" rid="bib14">14</jats:xref>-<jats:xref'
            ' ref-type="bibr" rid="bib16">16</jats:xref>, <jats:xref'
            ' ref-type="bibr" rid="bib22">22</jats:xref>, <jats:xref'
            ' ref-type="bibr" rid="bib23">23</jats:xref>).</jats:p>'
            "</jats:sec></jats:body>"
        ),
    )
    ref11703656 = Reference(
        authors=(
            "Upton, A.M.; Mushtaq, A.; Victor, T.C.; Sampson, S.L.; Sandy, J.;"
            " Smith, D.M.; Van Helden, P.V.; Sim, E."
        ),
        title=(
            "Arylamine N-acetyltransferase of Mycobacterium tuberculosis is a "
            "polymorphic enzyme and a site of isoniazid metabolism"
        ),
        journal="Mol. Microbiol.",
        volume="42",
        pages="309-317",
        year=2001,
        pubmed_id=11703656,
        pmc_open=True,
        doi="10.1046/j.1365-2958.2001.02648.x",
        abstract=(
            "Arylamine N-acetyltransferases (NATs; E.C 2.3.1.5) N-acetylate "
            "arylhydralazine and arylamine substrates using acetyl coenzyme "
            "A. Human NAT2 acetylates and inactivates the antituberculosis "
            "drug, isoniazid (INH), and is polymorphic. We previously "
            "demonstrated that there is a homologue of human NAT2 in "
            "Mycobacterium tuberculosis, whose product N-acetylates INH in "
            "vitro. We now demonstrate that the nat gene is expressed in M. "
            "tuberculosis and M. bovis Bacille Calmette-Guerin (BCG), using "
            "reverse transcription-polymerase chain reaction and Western "
            "blotting. The NAT protein is active in M. bovis BCG in vivo, "
            "as detected by the presence of N-acetyl INH in M. bovis BCG "
            "lysates grown in INH. Sequence analysis of the M. tuberculosis "
            "nat coding region reveals a single nucleotide polymorphism in "
            "18% of a random cohort of M. tuberculosis clinical isolates, "
            "conferring a G to R change. The recombinant mutant protein "
            "appears less stable than the wild type, and has an apparent "
            "affinity for INH of 10-fold less than the wild type. Modelling "
            "the change in M. tuberculosis NAT shows that the G to R change "
            "is close to the active site, and supports the experimental "
            "findings. Minimum inhibitory concentration data suggest that "
            "this polymorphism in nat is linked to low-level changes in the "
            "INH susceptibility of M. tuberculosis clinical isolates."
        ),
    )

    enz = Entity(curie="enz56590", type="d3o:Enzyme")
    strain = Entity(curie="str4329", type="d3o:Strain")

    relations = [
        Relation(
            predicate="d3o:HasEnzyme", subject="str4329", object="enz56590"
        ),
    ]

    test_user = User(email="teste@dsmz.de")

    pointer1 = Pointer(
        entity_id="enz56590",
        offset=563,
        length=3,
        reference_id=11703656,
    )
    pointer2 = Pointer(
        entity_id="str4329",
        offset=588,
        length=13,
        reference_id=11703656,
    )
    pointer3 = Pointer(
        entity_id="enz56590",
        offset=867,
        length=3,
        reference_id=15117974,
    )
    pointer4 = Pointer(
        entity_id="str4329",
        offset=907,
        length=23,
        reference_id=15117974,
    )

    refannotations = [
        ReferenceAnnotation(
            user=test_user,
            reference=ref11703656,
            pointers=[pointer1, pointer2],
            relations=[],
            completed=False,
            last_updated=_NOW,
            project_id=project_id,
        ),
        ReferenceAnnotation(
            user=test_user,
            reference=ref15117974,
            pointers=[pointer3, pointer4],
            relations=relations,
            completed=False,
            last_updated=_NOW,
            project_id=project_id,
        ),
    ]

    return refannotations, [enz, strain]


def test_db_schema() -> None:
    db = D3TextDB(echo=True)
    project_id = db.create_project("Test Project")
    refannotations, entities = ref_annotations(project_id)
    user_id = refannotations[1].user.user_id

    db.create_user(refannotations[0].user, "testpassword")
    db.store_items(entities)

    for ann in refannotations:
        db.store_annotation(ann)

    fromdb = db.get_reference_annotation(pubmed_id=15117974, user_id=user_id, project_id=project_id)
    original = refannotations[1]

    # User
    assert fromdb.user.user_id == original.user.user_id
    assert fromdb.user.email == original.user.email

    # Reference
    for field in ("pubmed_id", "doi", "title", "authors", "year"):
        assert getattr(fromdb.reference, field) == getattr(
            original.reference, field
        )

    # Pointers (order may differ — sort by offset)
    assert len(fromdb.pointers) == len(original.pointers)
    from_sorted = sorted(fromdb.pointers, key=lambda p: p.offset)
    orig_sorted = sorted(original.pointers, key=lambda p: p.offset)
    for fp, op in zip(from_sorted, orig_sorted):
        assert fp.entity_id == op.entity_id
        assert fp.offset == op.offset
        assert fp.length == op.length

    # Relations
    assert len(fromdb.relations) == len(original.relations)
    for fr, orr in zip(fromdb.relations, original.relations):
        assert fr.predicate == orr.predicate
        assert fr.subject == orr.subject
        assert fr.object == orr.object

    # Completion state
    assert fromdb.completed == original.completed


def get_test_payload():
    """Return a test payload for annotation testing."""
    return {
        "user": {
            "user_id": "f47f7e7b-3913-457e-911c-6da6275de3ec",
            "email": "teste@dsmz.de",
        },
        "reference": {
            "reference_id": 1,
            "pubmed_id": 15117974,
            "pmc_id": 2211905,
            "pmc_open": True,
            "doi": "10.1084/jem.20031956",
            "authors": "Bhakta, S.; Besra, G.S.; Upton, A.M.; Parish, T.; Sholto-Douglas-Vernon, C.; Gibson, K.J.; Knutton, S.; Gordon, S.; daSilva, R.P.; Anderton, M.C.; Sim, E.",
            "title": "Arylamine N-acetyltransferase is required for synthesis of mycolic acids and complex lipids in Mycobacterium bovis BCG and represents a novel drug target",
            "journal": "J. Exp. Med.",
            "volume": "199",
            "number": None,
            "pages": "1191-1199",
            "year": 2004,
            "abstract": "Mycolic acids represent a major component of the unique cell wall of mycobacteria. Mycolic acid biosynthesis is inhibited by isoniazid, a key frontline antitubercular drug that is inactivated by mycobacterial and human arylamine N-acetyltransferase (NAT). We show that an in-frame deletion of Mycobacterium bovis BCG nat results in delayed entry into log phase, altered morphology, altered cell wall lipid composition, and increased intracellular killing by macrophages. In particular, deletion of nat perturbs biosynthesis of mycolic acids and their derivatives and increases susceptibility of M. bovis BCG to antibiotics that permeate the cell wall. Phenotypic traits are fully complemented by introduction of Mycobacterium tuberculosis nat. We infer from our findings that NAT is critical to normal mycolic acid synthesis and hence other derivative cell wall components and represents a novel target for antituberculosis therapy. In addition, this is the first report of an endogenous role for NAT in mycobacteria.",
            "body": '<div class="jats-body"><sec><p>Genes encoding NAT are present in a range of bacterial genomes (<xref ref-type="bibr" rid="bib15">15</xref>, <xref ref-type="bibr" rid="bib16">16</xref>). This observation first provoked intrigue because human NATs have long been identified as drug metabolizing enzymes (<xref ref-type="bibr" rid="bib17">17</xref>). NAT represents one of the first examples of pharmacogenetic variation and its study revealed the role of acetyl-CoA as an acetyl donor. In particular, NAT2 in humans is known to be responsible for the inactivation of INH through acetylation (<xref ref-type="bibr" rid="bib18">18</xref>–<xref ref-type="bibr" rid="bib20">20</xref>). We have studied mycobacterial NATs in this laboratory as potential contributors to the variation in INH resistance among <italic>M. tuberculosis</italic> clinical isolates. It is now known that <italic>nat</italic> in <italic>M. tuberculosis</italic> is polymorphic (<xref ref-type="bibr" rid="bib14">14</xref>). The expression product acetylates and inactivates INH in vitro, and it has been suggested that this activity and polymorphism might be a contributory factor to INH resistance (<xref ref-type="bibr" rid="bib14">14</xref>, <xref ref-type="bibr" rid="bib15">15</xref>, <xref ref-type="bibr" rid="bib21">21</xref>). We know that <italic>nat</italic> is expressed in <italic>M. tuberculosis</italic> and <italic>Mycobacterium bovis</italic> BCG and the gene product is active (<xref ref-type="bibr" rid="bib14">14</xref>). The genomes of <italic>M. tuberculosis</italic> (<xref ref-type="bibr" rid="bib22">22</xref>) and <italic>M. bovis</italic> (<xref ref-type="bibr" rid="bib23">23</xref>) have been sequenced. <italic>M. bovis</italic> is a member of the <italic>M. tuberculosis</italic> complex. <italic>M. bovis</italic> BCG is an attenuated <italic>M. bovis</italic> strain in use as a vaccine. The <italic>nat</italic> gene is maintained in <italic>M. bovis</italic> BCG and is identical in sequence to that of <italic>M. tuberculosis</italic> (<xref ref-type="bibr" rid="bib14">14</xref>–<xref ref-type="bibr" rid="bib16">16</xref>, <xref ref-type="bibr" rid="bib22">22</xref>, <xref ref-type="bibr" rid="bib23">23</xref>).</p></sec></div>',
        },
        "entities": {
            "4329": {"curie": "4329", "type": "d3o:Strain"},
            "56590": {"curie": "56590", "type": "d3o:Enzyme"},
            "entity_1764076512192_3of2gf": {
                "curie": "entity_1764076512192_3of2gf",
                "type": "d3o:Enzyme",
            },
        },
        "pointers": [
            {
                "entity_id": "56590",
                "reference_id": 1,
                "offset": 867,
                "length": 3,
            },
            {
                "entity_id": "4329",
                "reference_id": 1,
                "offset": 907,
                "length": 23,
            },
            {
                "entity_id": "entity_1764076512192_3of2gf",
                "reference_id": 1,
                "offset": 345,
                "length": 4,
            },
        ],
        "relations": [
            {"predicate": "HasEnzyme", "subject": "4329", "object": "56590"}
        ],
    }


def _setup_from_payload(db: D3TextDB, payload: dict):
    """Create user, entities, and build a ReferenceAnnotation from payload."""
    from uuid import UUID

    user_data = payload["user"].copy()
    user_data["user_id"] = UUID(user_data["user_id"])
    user = User(**user_data)
    reference = Reference(**payload["reference"])
    entities = {k: Entity(**v) for k, v in payload["entities"].items()}
    pointers = [Pointer(**p) for p in payload["pointers"]]
    relations = [Relation(**r) for r in payload["relations"]]

    project_id = db.create_project("Test Project")
    db.create_user(user, "testpassword")
    db.store_items(list(entities.values()))

    annotation = ReferenceAnnotation(
        user=user,
        reference=reference,
        pointers=pointers,
        relations=relations,
        completed=False,
        last_updated=_NOW,
        project_id=project_id,
    )
    return annotation, user, reference, entities


def test_store_annotation_with_existing_reference_id() -> None:
    """Test that store_annotation works when reference_id is already set."""
    db = D3TextDB(echo=True)
    payload = get_test_payload()
    annotation, user, reference, entities = _setup_from_payload(db, payload)

    db.store_annotation(annotation)

    fromdb = db.get_reference_annotation(
        pubmed_id=15117974, user_id=user.user_id, project_id=annotation.project_id
    )

    # Check that all pointers were stored
    assert len(fromdb.pointers) == 3
    entity_ids = {p.entity_id for p in fromdb.pointers}
    assert "4329" in entity_ids
    assert "56590" in entity_ids
    assert "entity_1764076512192_3of2gf" in entity_ids

    # Check that relations were stored
    assert len(fromdb.relations) == 1
    assert fromdb.relations[0].predicate == "HasEnzyme"


def test_update_entity_curie_with_snapshot_pointers() -> None:
    """Rename an entity referenced by a completed annotation's snapshot.

    Regression: state_pointer / snapshot_pointer / curated_annotation_pointer
    carry a composite FK to pointer without ON UPDATE CASCADE, so the cascade
    into pointer.entity_id would trip a FOREIGN KEY constraint mid-statement
    (surfaced as a spurious "already in use" 409). The rename defers FK checks
    and fixes up those child tables explicitly.
    """
    db = D3TextDB()
    payload = get_test_payload()
    annotation, user, _, _ = _setup_from_payload(db, payload)
    # completed=True records a snapshot, creating snapshot_pointer rows that
    # reference the proposed entity's pointer.
    db.store_annotation(annotation.model_copy(update={"completed": True}))

    old = "entity_1764076512192_3of2gf"
    new = "CHEBI:99999"
    db.update_entity_curie(old, new)

    assert db.get_entities_by_curies([old]) == []
    assert len(db.get_entities_by_curies([new])) == 1

    # Every pointer-family table moved from the old curie to the new one, with
    # no orphans left behind.
    with Session(db.engine) as session:
        for tbl in ("pointer", "state_pointer", "snapshot_pointer"):
            stale = session.execute(
                text(f"SELECT COUNT(*) FROM {tbl} WHERE entity_id = :o"),
                {"o": old},
            ).scalar_one()
            moved = session.execute(
                text(f"SELECT COUNT(*) FROM {tbl} WHERE entity_id = :n"),
                {"n": new},
            ).scalar_one()
            assert stale == 0, f"{tbl} still references the old curie"
            assert moved > 0, f"{tbl} was not updated to the new curie"
        assert session.execute(
            text("PRAGMA foreign_key_check")
        ).fetchall() == []


def test_get_reference_annotation() -> None:
    """Test retrieving a reference annotation by pubmed_id and user_id."""
    db = D3TextDB()
    payload = get_test_payload()
    annotation, user, reference, entities = _setup_from_payload(db, payload)

    db.store_annotation(annotation)

    retrieved = db.get_reference_annotation(
        pubmed_id=payload["reference"]["pubmed_id"], user_id=user.user_id, project_id=annotation.project_id
    )

    # Verify user
    assert retrieved.user.user_id == user.user_id
    assert retrieved.user.email == user.email

    # Verify reference
    assert retrieved.reference.pubmed_id == reference.pubmed_id
    assert retrieved.reference.pmc_id == reference.pmc_id
    assert retrieved.reference.doi == reference.doi
    assert retrieved.reference.title == reference.title
    assert retrieved.reference.authors == reference.authors
    assert retrieved.reference.journal == reference.journal
    assert retrieved.reference.volume == reference.volume
    assert retrieved.reference.pages == reference.pages
    assert retrieved.reference.year == reference.year
    assert retrieved.reference.abstract == reference.abstract
    assert retrieved.reference.body == reference.body

    # Verify pointers (should have 3)
    assert len(retrieved.pointers) == 3
    pointer_list = sorted(retrieved.pointers, key=lambda p: p.offset)

    assert pointer_list[0].entity_id == "entity_1764076512192_3of2gf"
    assert pointer_list[0].offset == 345
    assert pointer_list[0].length == 4

    assert pointer_list[1].entity_id == "56590"
    assert pointer_list[1].offset == 867
    assert pointer_list[1].length == 3

    assert pointer_list[2].entity_id == "4329"
    assert pointer_list[2].offset == 907
    assert pointer_list[2].length == 23

    # Verify relations
    assert len(retrieved.relations) == 1
    assert retrieved.relations[0].predicate == "HasEnzyme"
    assert retrieved.relations[0].subject == "4329"
    assert retrieved.relations[0].object == "56590"

    # Verify completion state
    assert retrieved.completed is False


def test_get_reference_annotation_user_not_found() -> None:
    """Test that get_reference_annotation raises ValueError when user doesn't exist."""
    from uuid import UUID
    import pytest

    db = D3TextDB()
    payload = get_test_payload()
    annotation, user, reference, entities = _setup_from_payload(db, payload)
    db.store_annotation(annotation)

    non_existent_user_id = UUID("00000000-0000-0000-0000-000000000000")

    with pytest.raises(
        ValueError,
        match=f"User with user_id {non_existent_user_id} not found",
    ):
        db.get_reference_annotation(
            pubmed_id=payload["reference"]["pubmed_id"],
            user_id=non_existent_user_id,
            project_id=annotation.project_id,
        )


def test_get_reference_annotation_reference_not_found() -> None:
    """Test that get_reference_annotation raises ValueError when reference doesn't exist."""
    import pytest

    db = D3TextDB()
    payload = get_test_payload()

    from uuid import UUID

    user_data = payload["user"].copy()
    user_data["user_id"] = UUID(user_data["user_id"])
    user = User(**user_data)
    db.create_user(user, "testpassword")

    non_existent_pubmed_id = 99999999

    project_id = db.create_project("Test Project")

    with pytest.raises(
        ValueError,
        match=f"Reference with pubmed_id {non_existent_pubmed_id} not found",
    ):
        db.get_reference_annotation(
            pubmed_id=non_existent_pubmed_id, user_id=user.user_id, project_id=project_id
        )


def test_store_annotation_idempotent() -> None:
    """Test that storing the same annotation multiple times is idempotent."""
    db = D3TextDB()
    payload = get_test_payload()
    annotation, user, reference, entities = _setup_from_payload(db, payload)

    db.store_annotation(annotation)
    db.store_annotation(annotation)
    db.store_annotation(annotation)

    retrieved = db.get_reference_annotation(
        pubmed_id=payload["reference"]["pubmed_id"], user_id=user.user_id, project_id=annotation.project_id
    )

    assert len(retrieved.pointers) == 3
    assert len(retrieved.relations) == 1


def test_store_annotation_new_state_supersedes_old() -> None:
    """Test that a subsequent store_annotation supersedes the previous state."""
    db = D3TextDB()
    payload = get_test_payload()
    initial_annotation, user, reference, entities = _setup_from_payload(
        db, payload
    )

    db.store_annotation(initial_annotation)

    # Verify initial state
    retrieved = db.get_reference_annotation(
        pubmed_id=payload["reference"]["pubmed_id"], user_id=user.user_id, project_id=initial_annotation.project_id
    )
    assert len(retrieved.pointers) == 3
    assert len(retrieved.relations) == 1

    # Store the new entity required by the updated annotation
    new_entity = Entity(curie="new_entity_123", type="d3o:NewKind")
    db.store_item(new_entity)

    reference_id = retrieved.reference.reference_id
    updated_annotation = ReferenceAnnotation(
        user=user,
        reference=reference,
        pointers=[
            Pointer(
                entity_id="new_entity_123",
                reference_id=reference_id,
                offset=100,
                length=5,
            ),
            Pointer(
                entity_id="4329",
                reference_id=reference_id,
                offset=200,
                length=10,
            ),
        ],
        relations=[
            Relation(
                predicate="d3o:NewRelation",
                subject="new_entity_123",
                object="4329",
            )
        ],
        completed=False,
        last_updated=_NOW,
        project_id=initial_annotation.project_id,
    )

    db.store_annotation(updated_annotation)

    retrieved = db.get_reference_annotation(
        pubmed_id=payload["reference"]["pubmed_id"], user_id=user.user_id, project_id=initial_annotation.project_id
    )

    # Only the new pointers should be in the latest state
    assert len(retrieved.pointers) == 2
    pointer_list = sorted(retrieved.pointers, key=lambda p: p.offset)
    assert pointer_list[0].entity_id == "new_entity_123"
    assert pointer_list[0].offset == 100
    assert pointer_list[0].length == 5
    assert pointer_list[1].entity_id == "4329"
    assert pointer_list[1].offset == 200
    assert pointer_list[1].length == 10

    assert len(retrieved.relations) == 1
    assert retrieved.relations[0].predicate == "d3o:NewRelation"
    assert retrieved.relations[0].subject == "new_entity_123"
    assert retrieved.relations[0].object == "4329"


def test_store_annotation_transaction_rollback() -> None:
    """Test that store_annotation is fully transactional.

    If a pointer references a non-existent entity the entire transaction must
    roll back, leaving the previous state intact.
    """
    import pytest

    db = D3TextDB()
    payload = get_test_payload()
    initial_annotation, user, reference, entities = _setup_from_payload(
        db, payload
    )

    db.store_annotation(initial_annotation)

    retrieved = db.get_reference_annotation(
        pubmed_id=payload["reference"]["pubmed_id"], user_id=user.user_id, project_id=initial_annotation.project_id
    )
    initial_pointer_count = len(retrieved.pointers)
    initial_relation_count = len(retrieved.relations)
    assert initial_pointer_count == 3
    assert initial_relation_count == 1

    # Pointer references an entity that does not exist → FK violation
    bad_annotation = ReferenceAnnotation(
        user=user,
        reference=reference,
        pointers=[
            Pointer(
                entity_id="non_existent_entity_xyz",
                reference_id=retrieved.reference.reference_id,
                offset=300,
                length=7,
            )
        ],
        relations=[],
        completed=False,
        last_updated=_NOW,
        project_id=initial_annotation.project_id,
    )

    with pytest.raises(Exception):  # IntegrityError
        db.store_annotation(bad_annotation)

    # Old state must still be returned
    retrieved = db.get_reference_annotation(
        pubmed_id=payload["reference"]["pubmed_id"], user_id=user.user_id, project_id=initial_annotation.project_id
    )
    assert len(retrieved.pointers) == initial_pointer_count
    assert len(retrieved.relations) == initial_relation_count



def test_search_entities_matches_fts_token_prefix() -> None:
    """search_entities matches via the name_fts index on per-word prefixes.

    A query token matches names containing a *word* that starts with it,
    including non-leading words, but not mid-word substrings. Dropping mid-word
    matching is the intended trade-off of routing search through FTS (TICKET-19).
    """
    from d3textdb.schema import EntityAnnotation as EA

    db = D3TextDB()
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")

    db.load_ontology_entities(
        ontology_id,
        [
            EA(entity_id="T:1", preferred_name="Bacterium acidiphilum", kind="d3o:Bacteria", synonyms=[]),
            EA(entity_id="T:2", preferred_name="Escherichia coli", kind="d3o:Bacteria", synonyms=[]),
            EA(entity_id="T:3", preferred_name="Mycobacterium bovis", kind="d3o:Bacteria", synonyms=[]),
        ],
    )

    bacterium = [r.preferred_name for r in db.search_entities("bacterium")]
    assert "Bacterium acidiphilum" in bacterium, bacterium
    # "bacterium" is a mid-word substring of "Mycobacterium", not a token prefix.
    assert "Mycobacterium bovis" not in bacterium, bacterium

    # A non-leading word ("coli") is still matched by prefix.
    coli = [r.preferred_name for r in db.search_entities("coli")]
    assert "Escherichia coli" in coli, coli

    # Punctuation-only queries yield no usable tokens.
    assert db.search_entities("...") == []


def test_search_entities_ranks_prefix_before_contains() -> None:
    from d3textdb.schema import EntityAnnotation as EA

    db = D3TextDB()
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")

    db.load_ontology_entities(
        ontology_id,
        [
            EA(entity_id="T:1", preferred_name="Coli phage", kind="d3o:Bacteria", synonyms=[]),
            EA(entity_id="T:2", preferred_name="Escherichia coli", kind="d3o:Bacteria", synonyms=[]),
        ],
    )

    names = [r.preferred_name for r in db.search_entities("coli")]

    assert names.index("Coli phage") < names.index("Escherichia coli"), (
        f"Preferred-name prefix match should rank before contains match, got: {names}"
    )


def test_load_ontology_entities_suppresses_then_restores_fts_triggers() -> None:
    """Bulk load runs with the sync triggers dropped, then restores + rebuilds.

    After a load the imported names are searchable (the one rebuild ran) and the
    row-level triggers are back, so a subsequent single-row name change stays
    indexed without another rebuild.
    """
    from sqlalchemy import text as sa_text

    from d3textdb.schema import EntityAnnotation as EA

    db = D3TextDB()
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")
    db.load_ontology_entities(
        ontology_id,
        [
            EA(entity_id="T:1", preferred_name="Escherichia coli", kind="d3o:Bacteria", synonyms=[]),
        ],
    )

    assert any(r.preferred_name == "Escherichia coli" for r in db.search_entities("coli"))

    with db.engine.connect() as conn:
        triggers = set(
            conn.execute(
                sa_text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='trigger' AND name LIKE 'name_a%'"
                )
            ).scalars()
        )
    assert {"name_ai", "name_au", "name_ad"} <= triggers

    # The restored trigger keeps a direct single-row update in the index.
    with db.engine.begin() as conn:
        conn.execute(
            sa_text(
                "UPDATE name SET label='Escherichia coli K12' "
                "WHERE label='Escherichia coli'"
            )
        )
    assert any(
        r.preferred_name == "Escherichia coli K12"
        for r in db.search_entities("k12")
    )


def test_get_entity_types_ranks_prefix_match_before_contains_match() -> None:
    from d3textdb.schema import EntityAnnotation as EA

    db = D3TextDB()
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")

    db.load_ontology_entities(
        ontology_id,
        [
            EA(entity_id="T:1", preferred_name="Bacteria", kind="d3o:Bacteria", synonyms=[], is_class=True),
            EA(entity_id="T:2", preferred_name="Anaerobic Bacteria", kind="d3o:Bacteria", synonyms=[], is_class=True),
            EA(entity_id="T:3", preferred_name="16S (Bacterial)", kind="d3o:Bacteria", synonyms=[], is_class=True),
        ],
    )

    results = db.get_entity_types("bact")
    names = [r.preferred_name for r in results]

    assert names[0] == "Bacteria", f"Expected 'Bacteria' first, got: {names}"
    assert "Anaerobic Bacteria" in names
    assert "16S (Bacterial)" in names


def _make_ontology_with_annotations(db: D3TextDB) -> tuple[int, int]:
    """Create an ontology with two entities, store an annotation using one of them.

    Returns (ontology_id, project_id).
    """
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")
    db.load_ontology_entities(
        ontology_id,
        [
            EntityAnnotation(entity_id="TEST:1", preferred_name="Alpha", kind="d3o:Enzyme", synonyms=[]),
            EntityAnnotation(entity_id="TEST:2", preferred_name="Beta",  kind="d3o:Strain", synonyms=[]),
        ],
    )

    user = User(email="tester@example.com")
    db.create_user(user, "password")
    project_id = db.create_project("Test Project")

    ref = Reference(
        pubmed_id=99999,
        pmc_open=False,
        authors="A. Test",
        title="Test Paper",
        journal="Test J.",
        volume="1",
        pages="1-2",
        year=2024,
        abstract="Abstract.",
    )
    annotation = ReferenceAnnotation(
        user=user,
        reference=ref,
        pointers=[Pointer(entity_id="TEST:1", reference_id=None, offset=0, length=5)],
        relations=[],
        completed=False,
        last_updated=_NOW,
        project_id=project_id,
    )
    db.store_annotation(annotation)

    return ontology_id, project_id


def test_delete_ontology_raises_when_annotations_exist() -> None:
    """Deleting an ontology whose entities are referenced by Pointer rows must raise."""
    db = D3TextDB()
    ontology_id, _ = _make_ontology_with_annotations(db)

    with pytest.raises(OntologyInUseError):
        db.delete_ontology(ontology_id)


def test_delete_ontology_raises_when_relation_references_entity() -> None:
    """Deleting an ontology whose entities are referenced by Relation rows must raise."""
    db = D3TextDB()
    ontology_id = db.store_ontology("Rel Ontology", "REL", "http://rel.org/")
    db.load_ontology_entities(
        ontology_id,
        [
            EntityAnnotation(entity_id="REL:1", preferred_name="Subject", kind="d3o:Enzyme", synonyms=[]),
            EntityAnnotation(entity_id="REL:2", preferred_name="Object",  kind="d3o:Strain", synonyms=[]),
        ],
    )

    user = User(email="reltest@example.com")
    db.create_user(user, "password")
    project_id = db.create_project("Rel Project")

    ref = Reference(
        pubmed_id=88888,
        pmc_open=False,
        authors="B. Test",
        title="Relation Test",
        journal="Test J.",
        volume="1",
        pages="1-2",
        year=2024,
        abstract="Abstract.",
    )
    annotation = ReferenceAnnotation(
        user=user,
        reference=ref,
        pointers=[
            Pointer(entity_id="REL:1", reference_id=None, offset=0, length=3),
            Pointer(entity_id="REL:2", reference_id=None, offset=10, length=3),
        ],
        relations=[Relation(predicate="d3o:HasEnzyme", subject="REL:1", object="REL:2")],
        completed=False,
        last_updated=_NOW,
        project_id=project_id,
    )
    db.store_annotation(annotation)

    with pytest.raises(OntologyInUseError):
        db.delete_ontology(ontology_id)


def test_delete_ontology_succeeds_without_annotations() -> None:
    """An ontology with no annotations must be deleted cleanly."""
    db = D3TextDB()
    ontology_id = db.store_ontology("Clean Ontology", "CLN", "http://clean.org/")
    db.load_ontology_entities(
        ontology_id,
        [EntityAnnotation(entity_id="CLN:1", preferred_name="Gamma", kind="d3o:Enzyme", synonyms=[])],
    )

    db.delete_ontology(ontology_id)  # must not raise


def test_update_entity_curie_cascades_to_referencing_rows() -> None:
    """Renaming an entity's CURIE cascades to its pointer and relation rows via
    ON UPDATE CASCADE, with foreign-key enforcement left on throughout (a
    dangling reference is still rejected afterwards)."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlmodel import Session

    db = D3TextDB()
    project_id = db.create_project("P", required_annotators=1)
    db.store_proposed_entity(project_id, "Beta", "PROP:1", "Strain")
    db.store_proposed_entity(project_id, "Obj", "OBJ:1", "Enzyme")
    ref_id = db.store_reference(
        Reference(
            pubmed_id=1,
            title="t",
            authors="a",
            journal="J",
            volume="1",
            pages="1",
            year=2024,
            abstract="x",
        )
    )
    with Session(db.engine) as session:
        session.add(
            Pointer(
                reference_id=ref_id,
                entity_id="PROP:1",
                offset=0,
                length=3,
                field="abstract",
            )
        )
        session.add(Relation(predicate="d3o:x", subject="PROP:1", object="OBJ:1"))
        session.commit()

    db.update_entity_curie("PROP:1", "CHEBI:2")

    with Session(db.engine) as session:
        assert (
            session.execute(text("SELECT entity_id FROM pointer")).scalar()
            == "CHEBI:2"
        )
        assert (
            session.execute(text("SELECT subject FROM relation")).scalar()
            == "CHEBI:2"
        )
        # Enforcement stayed on: a dangling reference is still rejected.
        assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1
        session.add(
            Pointer(
                reference_id=ref_id,
                entity_id="MISSING:9",
                offset=5,
                length=3,
                field="abstract",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_get_entity_project_id() -> None:
    """The authz lookup returns the owning project for a proposed entity, and
    None for both an unscoped row and a non-existent CURIE."""
    db = D3TextDB()
    project_id = db.create_project("P", required_annotators=1)
    db.store_proposed_entity(project_id, "Beta", "PROP:1", "Strain")

    assert db.get_entity_project_id("PROP:1") == project_id
    assert db.get_entity_project_id("NOPE:9999") is None

    db.backfill_entity_project("PROP:1", project_id)  # no-op when already set
    with Session(db.engine) as session:
        row = session.exec(
            select(Entity).where(Entity.curie == "PROP:1")
        ).one()
        row.project_id = None
        session.add(row)
        session.commit()
    assert db.get_entity_project_id("PROP:1") is None


def _downgrade_entity_fk_to_no_action(db, table: str) -> None:
    """Rebuild ``table`` with the legacy NO ACTION entity FK, to emulate a
    database created before ON UPDATE CASCADE was introduced. Uses the same raw
    autocommit + explicit BEGIN dance as the production rebuild, because
    pysqlite implicitly commits before DDL inside a SQLAlchemy transaction."""
    with db.engine.connect() as conn:
        legacy_sql = conn.exec_driver_sql(
            f"SELECT sql FROM sqlite_master "
            f"WHERE type='table' AND name='{table}'"
        ).scalar()
    legacy_sql = legacy_sql.replace(" ON UPDATE CASCADE", "")
    raw = db.engine.raw_connection()
    try:
        dbapi = raw.dbapi_connection
        prior_isolation = dbapi.isolation_level
        dbapi.isolation_level = None
        cursor = dbapi.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("PRAGMA legacy_alter_table = ON")
        cursor.execute("BEGIN")
        try:
            cursor.execute(f'ALTER TABLE "{table}" RENAME TO "{table}__x"')
            cursor.execute(legacy_sql)
            cursor.execute(f'INSERT INTO "{table}" SELECT * FROM "{table}__x"')
            cursor.execute(f'DROP TABLE "{table}__x"')
            cursor.execute("COMMIT")
        except BaseException:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.execute("PRAGMA legacy_alter_table = OFF")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
            dbapi.isolation_level = prior_isolation
    finally:
        raw.close()


def test_fk_cascade_migration_upgrades_legacy_database(tmp_path) -> None:
    """A database whose entity FKs predate ON UPDATE CASCADE is upgraded on
    open, preserving rows, so later renames cascade with FK enforcement on."""
    from sqlalchemy import text
    from sqlmodel import Session

    db_path = tmp_path / "legacy.db"
    db = D3TextDB(db_path)
    project_id = db.create_project("P", required_annotators=1)
    db.store_proposed_entity(project_id, "Beta", "PROP:1", "Strain")
    db.store_proposed_entity(project_id, "Obj", "OBJ:1", "Enzyme")
    ref_id = db.store_reference(
        Reference(
            pubmed_id=1,
            title="t",
            authors="a",
            journal="J",
            volume="1",
            pages="1",
            year=2024,
            abstract="x",
        )
    )
    with Session(db.engine) as session:
        session.add(
            Pointer(
                reference_id=ref_id,
                entity_id="PROP:1",
                offset=0,
                length=3,
                field="abstract",
            )
        )
        session.add(Relation(predicate="d3o:x", subject="PROP:1", object="OBJ:1"))
        session.commit()

    for table in ("pointer", "relation"):
        _downgrade_entity_fk_to_no_action(db, table)
        assert db._entity_fk_needs_cascade(table)
    db.engine.dispose()

    # Reopening runs the migration in __init__.
    db = D3TextDB(db_path)
    for table in ("pointer", "relation"):
        assert not db._entity_fk_needs_cascade(table)
    with Session(db.engine) as session:
        assert session.execute(text("SELECT count(*) FROM pointer")).scalar() == 1
        assert (
            session.execute(text("SELECT count(*) FROM relation")).scalar() == 1
        )

    # The rename now cascades to pointer and relation with FK enforcement on.
    db.update_entity_curie("PROP:1", "ZZZ:9")
    with Session(db.engine) as session:
        assert (
            session.execute(text("SELECT entity_id FROM pointer")).scalar()
            == "ZZZ:9"
        )
        assert (
            session.execute(text("SELECT subject FROM relation")).scalar()
            == "ZZZ:9"
        )
        assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_delete_entity_with_curation_rows_succeeds() -> None:
    """Deleting a proposed entity whose pointer/relation has been curated must
    cascade through the curation child rows instead of raising IntegrityError
    (FK enforcement is on). Regression for TICKET-13."""
    from sqlalchemy import text
    from sqlmodel import Session

    from d3textdb.schema import (
        CuratedAnnotation,
        CuratedAnnotationPointer,
        CuratedAnnotationRelation,
        CurationDecision,
        Verdict,
    )

    db = D3TextDB()
    project_id = db.create_project("P", required_annotators=1)
    curator_id = db.create_user(User(email="c@example.com"), "pw")
    db.store_proposed_entity(project_id, "Beta", "PROP:1", "Strain")
    db.store_proposed_entity(project_id, "Obj", "OBJ:1", "Enzyme")
    ref_id = db.store_reference(
        Reference(
            pubmed_id=1,
            title="t",
            authors="a",
            journal="J",
            volume="1",
            pages="1",
            year=2024,
            abstract="x",
        )
    )
    with Session(db.engine) as session:
        session.add(
            Pointer(
                reference_id=ref_id,
                entity_id="PROP:1",
                offset=0,
                length=3,
                field="abstract",
            )
        )
        rel = Relation(predicate="d3o:x", subject="PROP:1", object="OBJ:1")
        session.add(rel)
        session.flush()
        rel_id = rel.relation_id
        session.add(
            CuratedAnnotation(
                project_id=project_id,
                reference_id=ref_id,
                curator_id=curator_id,
                content_hash="h",
                created_at=_NOW,
            )
        )
        session.flush()
        curated_id = session.execute(
            text("SELECT curated_id FROM curated_annotation")
        ).scalar()
        session.add(
            CuratedAnnotationPointer(
                curated_id=curated_id,
                reference_id=ref_id,
                entity_id="PROP:1",
                offset=0,
                length=3,
                field="abstract",
            )
        )
        session.add(
            CuratedAnnotationRelation(curated_id=curated_id, relation_id=rel_id)
        )
        session.add(
            CurationDecision(
                project_id=project_id,
                relation_id=rel_id,
                curator_id=curator_id,
                verdict=Verdict.accepted,
                decided_at=_NOW,
            )
        )
        session.commit()

    db.delete_entity("PROP:1")

    with Session(db.engine) as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM entity WHERE curie = 'PROP:1'")
            ).scalar()
            == 0
        )
        assert (
            session.execute(
                text("SELECT count(*) FROM curated_annotation_pointer")
            ).scalar()
            == 0
        )
        assert (
            session.execute(
                text("SELECT count(*) FROM curated_annotation_relation")
            ).scalar()
            == 0
        )
        assert (
            session.execute(
                text("SELECT count(*) FROM curation_decision")
            ).scalar()
            == 0
        )
