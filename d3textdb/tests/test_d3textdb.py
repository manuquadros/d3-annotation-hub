from datetime import datetime, timezone

from d3textdb import D3TextDB
from d3textdb.schema import (
    Entity,
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



def test_search_entities_contains_fallback() -> None:
    from d3textdb.schema import EntityAnnotation as EA

    db = D3TextDB()
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")

    db.load_ontology_entities(
        ontology_id,
        [
            EA(entity_id="T:1", preferred_name="Mycobacterium bovis", kind="d3o:Bacteria", synonyms=[]),
            EA(entity_id="T:2", preferred_name="Bacterium acidiphilum", kind="d3o:Bacteria", synonyms=[]),
        ],
    )

    results = db.search_entities("bacterium")
    names = [r.preferred_name for r in results]

    assert "Mycobacterium bovis" in names, f"Contains match missing from results: {names}"
    assert names.index("Bacterium acidiphilum") < names.index("Mycobacterium bovis"), (
        f"Prefix match should rank before contains match, got: {names}"
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
