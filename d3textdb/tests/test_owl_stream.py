"""Tests for the streaming ontology parser (OntologyStreamParser / parse_owl).

Covers the pyoxigraph-backed RDF path used for large ontologies: class /
synonym / kind extraction, triples, object properties, OBO DOCTYPE-entity
handling, streaming from a file path, and resistance to entity-expansion bombs.
"""

import tempfile
from pathlib import Path

import pytest
from d3textdb.owl import (
    OntologyStreamParser,
    _reject_entity_expansion_bomb,
    parse_owl,
)

_RDFXML = b"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
 xmlns:owl="http://www.w3.org/2002/07/owl#"
 xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#">
  <owl:Class rdf:about="http://purl.obolibrary.org/obo/NCBITaxon_9606">
    <rdfs:label xml:lang="fr">Homme</rdfs:label>
    <rdfs:label xml:lang="en">Homo sapiens</rdfs:label>
    <oboInOwl:hasExactSynonym>human</oboInOwl:hasExactSynonym>
    <rdfs:subClassOf rdf:resource="http://purl.obolibrary.org/obo/NCBITaxon_9605"/>
  </owl:Class>
  <owl:Class rdf:about="http://purl.obolibrary.org/obo/NCBITaxon_9605">
    <rdfs:label>Homo</rdfs:label>
    <rdfs:subClassOf rdf:resource="http://www.w3.org/2002/07/owl#Thing"/>
  </owl:Class>
  <owl:ObjectProperty rdf:about="http://example.org/hasHost">
    <rdfs:label>has host</rdfs:label>
    <rdfs:domain rdf:resource="http://purl.obolibrary.org/obo/NCBITaxon_9606"/>
    <rdfs:range rdf:resource="http://purl.obolibrary.org/obo/NCBITaxon_9605"/>
  </owl:ObjectProperty>
</rdf:RDF>"""


def test_rdfxml_entities_prefer_english_label_and_extract_kind() -> None:
    parsed = parse_owl(_RDFXML, "NCBITaxon", "")
    by_id = {e.entity_id: e for e in parsed.entities}
    assert set(by_id) == {"NCBITaxon:9606", "NCBITaxon:9605"}
    assert by_id["NCBITaxon:9606"].preferred_name == "Homo sapiens"  # not "Homme"
    assert by_id["NCBITaxon:9606"].kind == "NCBITaxon:9605"
    assert by_id["NCBITaxon:9606"].synonyms == ["human"]
    # owl:Thing is not a named superclass.
    assert by_id["NCBITaxon:9605"].kind == ""


def test_rdfxml_triples_and_properties() -> None:
    parsed = parse_owl(_RDFXML, "NCBITaxon", "")
    subclass_pairs = {
        (t.subject_curie, t.object_curie)
        for t in parsed.triples
        if t.predicate.endswith("subClassOf")
    }
    assert ("NCBITaxon:9606", "NCBITaxon:9605") in subclass_pairs

    assert len(parsed.properties) == 1
    prop = parsed.properties[0]
    assert prop.curie == "hasHost"
    assert prop.label == "has host"
    assert prop.domain_curie == "NCBITaxon:9606"
    assert prop.range_curie == "NCBITaxon:9605"


def test_turtle_is_parsed() -> None:
    ttl = (
        b"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        b"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        b"@prefix ex: <https://example.org/o/> .\n"
        b'ex:Foo a owl:Class ; rdfs:label "Foo" ; rdfs:subClassOf ex:Bar .\n'
        b'ex:Bar a owl:Class ; rdfs:label "Bar" .\n'
    )
    parsed = parse_owl(ttl, "ex", "https://example.org/o/")
    assert {(e.entity_id, e.kind) for e in parsed.entities} == {
        ("ex:Foo", "ex:Bar"),
        ("ex:Bar", ""),
    }


def test_obo_doctype_entities_are_expanded() -> None:
    """OBO ontologies abbreviate namespaces with XML DOCTYPE entities."""
    obo = (
        b'<?xml version="1.0"?>\n'
        b"<!DOCTYPE rdf:RDF [\n"
        b'  <!ENTITY obo "http://purl.obolibrary.org/obo/" >\n'
        b'  <!ENTITY rdfs "http://www.w3.org/2000/01/rdf-schema#" >\n'
        b'  <!ENTITY owl "http://www.w3.org/2002/07/owl#" >\n'
        b"]>\n"
        b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        b' xmlns:rdfs="&rdfs;" xmlns:owl="&owl;">\n'
        b'  <owl:Class rdf:about="&obo;NCBITaxon_9606">\n'
        b"    <rdfs:label>Homo sapiens</rdfs:label>\n"
        b"  </owl:Class>\n"
        b"</rdf:RDF>"
    )
    parsed = parse_owl(obo, "NCBITaxon", "")
    assert [(e.entity_id, e.preferred_name) for e in parsed.entities] == [
        ("NCBITaxon:9606", "Homo sapiens")
    ]


def test_stream_from_file_path() -> None:
    with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as handle:
        handle.write(
            b"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
            b"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
            b"@prefix ex: <https://example.org/o/> .\n"
            b'ex:Foo a owl:Class ; rdfs:label "Foo" .\n'
            b"ex:Rel a owl:ObjectProperty ; "
            b'rdfs:label "rel" ; rdfs:domain ex:Foo .\n'
        )
        path = handle.name
    try:
        parser = OntologyStreamParser(
            path=path, prefix="ex", base_iri="https://example.org/o/"
        )
        entities = list(parser.iter_entities())
        assert [e.entity_id for e in entities] == ["ex:Foo"]
        # properties populated by the entity pass.
        assert [p.curie for p in parser.properties] == ["ex:Rel"]
    finally:
        Path(path).unlink()


def test_properties_available_without_pre_consuming_entities() -> None:
    parser = OntologyStreamParser(
        content=_RDFXML, prefix="NCBITaxon", base_iri=""
    )
    # Accessing properties first triggers the entity pass internally.
    assert [p.curie for p in parser.properties] == ["hasHost"]


# ── entity-expansion-bomb guard ───────────────────────────────────────────────
# These use tiny, non-amplifying declarations and assert rejection happens at
# construction — the parser never runs, so nothing is ever expanded.


def test_reject_bomb_allows_flat_namespace_entities() -> None:
    flat = (
        b"<!DOCTYPE rdf:RDF [\n"
        b'  <!ENTITY obo "http://purl.obolibrary.org/obo/" >\n'
        b'  <!ENTITY owl "http://www.w3.org/2002/07/owl#" >\n'
        b"]>"
    )
    _reject_entity_expansion_bomb(flat)  # must not raise


def test_reject_bomb_flags_recursive_entities() -> None:
    recursive = (
        b"<!DOCTYPE rdf:RDF [\n"
        b'  <!ENTITY a "AAAA">\n'
        b'  <!ENTITY b "&a;&a;">\n'
        b"]>"
    )
    with pytest.raises(ValueError, match="expansion bomb"):
        _reject_entity_expansion_bomb(recursive)


def test_reject_bomb_ignores_predefined_entity_references() -> None:
    _reject_entity_expansion_bomb(b'<!DOCTYPE x [ <!ENTITY q "a &amp; b"> ]>')


def test_reject_bomb_flags_parameter_entities() -> None:
    param = b'<!DOCTYPE x [ <!ENTITY % p "x"> <!ENTITY e "%p;"> ]>'
    with pytest.raises(ValueError, match="expansion bomb"):
        _reject_entity_expansion_bomb(param)


def test_parse_owl_rejects_bomb_before_parsing() -> None:
    # 2-level declaration: harmless (~16 chars) even if the guard were absent,
    # but it must be refused at construction, before pyoxigraph sees it.
    small_bomb = (
        b'<?xml version="1.0"?>\n'
        b"<!DOCTYPE rdf:RDF [\n"
        b'  <!ENTITY a "AAAA">\n'
        b'  <!ENTITY b "&a;&a;">\n'
        b"]>\n"
        b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        b' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
        b' xmlns:owl="http://www.w3.org/2002/07/owl#">\n'
        b'  <owl:Class rdf:about="https://x/1"><rdfs:label>&b;</rdfs:label>'
        b"</owl:Class>\n"
        b"</rdf:RDF>"
    )
    with pytest.raises(ValueError, match="expansion bomb"):
        parse_owl(small_bomb, "x", "https://x/")
