"""Tests for parse_owl, the full-document OWL/XML import path.

Focuses on the security hardening of the OWL/XML parser: it must parse
legitimate OWL/XML while refusing to expand XML entities or resolve external
references on attacker-supplied uploads (billion-laughs / XXE).
"""

import pytest
from d3textdb.owl import parse_owl
from defusedxml.common import DefusedXmlException

_OWL_NS = "http://www.w3.org/2002/07/owl#"


def _owl_xml_class(curie_local: str = "Foo", label: str = "Foo Label") -> bytes:
    """Minimal OWL/XML declaring one named class with an rdfs:label."""
    iri = f"https://example.org/o/{curie_local}"
    return (
        b'<?xml version="1.0"?>\n'
        b'<Ontology xmlns="' + _OWL_NS.encode() + b'" '
        b'ontologyIRI="https://example.org/o/">\n'
        b'  <Prefix name="rdfs" IRI="http://www.w3.org/2000/01/rdf-schema#"/>\n'
        b'  <Prefix name="ex" IRI="https://example.org/o/"/>\n'
        b'  <Declaration><Class IRI="' + iri.encode() + b'"/></Declaration>\n'
        b'  <AnnotationAssertion>\n'
        b'    <AnnotationProperty abbreviatedIRI="rdfs:label"/>\n'
        b'    <IRI>' + iri.encode() + b'</IRI>\n'
        b'    <Literal>' + label.encode() + b'</Literal>\n'
        b'  </AnnotationAssertion>\n'
        b'</Ontology>'
    )


def test_parse_owl_xml_extracts_named_class() -> None:
    """Legitimate OWL/XML still parses through the defused reader."""
    parsed = parse_owl(_owl_xml_class(), "ex", "https://example.org/o/")
    assert [(e.entity_id, e.preferred_name) for e in parsed.entities] == [
        ("ex:Foo", "Foo Label")
    ]


def test_parse_owl_xml_rejects_entity_expansion_bomb() -> None:
    """A billion-laughs bomb must be refused, not expanded in memory."""
    bomb = (
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE lolz [\n'
        b'  <!ENTITY a "AAAAAAAAAA">\n'
        b'  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
        b'  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">\n'
        b']>\n'
        b'<Ontology xmlns="' + _OWL_NS.encode() + b'" '
        b'ontologyIRI="https://example.org/o/">\n'
        b'  <AnnotationAssertion>\n'
        b'    <AnnotationProperty abbreviatedIRI="rdfs:label"/>\n'
        b'    <IRI>https://example.org/o/Foo</IRI>\n'
        b'    <Literal>&c;</Literal>\n'
        b'  </AnnotationAssertion>\n'
        b'</Ontology>'
    )
    with pytest.raises(DefusedXmlException):
        parse_owl(bomb, "ex", "https://example.org/o/")


def test_parse_owl_xml_rejects_external_entity() -> None:
    """An external-entity (XXE) reference must be refused."""
    xxe = (
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE Ontology [\n'
        b'  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n'
        b']>\n'
        b'<Ontology xmlns="' + _OWL_NS.encode() + b'" '
        b'ontologyIRI="https://example.org/o/">\n'
        b'  <AnnotationAssertion>\n'
        b'    <AnnotationProperty abbreviatedIRI="rdfs:label"/>\n'
        b'    <IRI>https://example.org/o/Foo</IRI>\n'
        b'    <Literal>&xxe;</Literal>\n'
        b'  </AnnotationAssertion>\n'
        b'</Ontology>'
    )
    with pytest.raises(DefusedXmlException):
        parse_owl(xxe, "ex", "https://example.org/o/")
