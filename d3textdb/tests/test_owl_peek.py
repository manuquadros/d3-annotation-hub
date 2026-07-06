"""Tests for peek_ontology_metadata and the helpers it delegates to."""

from d3textdb.owl import OntologyMetadata, peek_ontology_metadata

_OWL_NS = "http://www.w3.org/2002/07/owl#"
_XML_NS = "http://www.w3.org/XML/1998/namespace"


def owl_xml(
    *,
    ontology_iri: str = "",
    version_iri: str = "",
    xml_base: str = "",
    prefixes: list[tuple[str, str]] | None = None,
    label: str = "",
    version_info: str = "",
) -> bytes:
    """Build minimal OWL/XML bytes sufficient for peek tests."""
    attrs = f'xmlns="{_OWL_NS}"'
    if ontology_iri:
        attrs += f' ontologyIRI="{ontology_iri}"'
    if version_iri:
        attrs += f' versionIRI="{version_iri}"'
    if xml_base:
        attrs += f' xml:base="{xml_base}" xmlns:xml="{_XML_NS}"'

    body = ""
    for pfx_name, pfx_iri in (prefixes or []):
        body += f'<Prefix name="{pfx_name}" IRI="{pfx_iri}"/>\n'
    if label:
        body += (
            f"<Annotation>\n"
            f'  <AnnotationProperty abbreviatedIRI="rdfs:label"/>\n'
            f"  <Literal>{label}</Literal>\n"
            f"</Annotation>\n"
        )
    if version_info:
        body += (
            f"<Annotation>\n"
            f'  <AnnotationProperty abbreviatedIRI="owl:versionInfo"/>\n'
            f"  <Literal>{version_info}</Literal>\n"
            f"</Annotation>\n"
        )

    xml = f'<?xml version="1.0"?>\n<Ontology {attrs}>\n{body}</Ontology>'
    return xml.encode()


# ── OWL/XML path ──────────────────────────────────────────────────────────────


def test_peek_owl_xml_extracts_name_prefix_version_base_iri() -> None:
    content = owl_xml(
        ontology_iri="https://example.org/myonto/",
        prefixes=[("myonto", "https://example.org/myonto/")],
        label="My Test Ontology",
        version_info="1.2.3",
    )
    meta = peek_ontology_metadata(content)
    assert meta.name == "My Test Ontology"
    assert meta.prefix == "myonto"
    assert meta.base_iri == "https://example.org/myonto/"
    assert meta.version == "1.2.3"


def test_peek_owl_xml_iao_prefix_is_returned() -> None:
    """IAO was previously in _STANDARD_PREFIXES and produced prefix=None; now it must be returned."""
    content = owl_xml(
        ontology_iri="http://purl.obolibrary.org/obo/iao.owl",
        prefixes=[("IAO", "http://purl.obolibrary.org/obo/IAO_")],
        label="Information Artifact Ontology",
    )
    meta = peek_ontology_metadata(content)
    assert meta.prefix == "IAO"


def test_peek_owl_xml_prefers_iri_matching_prefix_over_first_declared() -> None:
    """When an imported ontology's <Prefix> is declared before the own prefix, pick the own one."""
    content = owl_xml(
        ontology_iri="https://example.org/myonto/",
        prefixes=[
            ("ENVO", "http://purl.obolibrary.org/obo/ENVO_"),  # imported, listed first
            ("myonto", "https://example.org/myonto/"),          # own, listed second
        ],
    )
    meta = peek_ontology_metadata(content)
    assert meta.prefix == "myonto"


def test_peek_owl_xml_reserved_xml_prefix_is_never_suggested() -> None:
    """The reserved xml namespace prefix must not be offered as an ontology prefix."""
    content = owl_xml(
        ontology_iri="https://purl.example.de/schema/",
        prefixes=[("xml", _XML_NS)],
    )
    meta = peek_ontology_metadata(content)
    assert meta.prefix is None


def test_peek_owl_xml_imported_prefixes_on_other_hosts_yield_no_suggestion() -> None:
    """When the own namespace is the unnamed default prefix, imported vocabularies
    (schema.org, the xml namespace) on other hosts must not be suggested."""
    content = owl_xml(
        ontology_iri="https://purl.dsmz.de/schema/",
        prefixes=[
            ("", "https://purl.dsmz.de/schema"),      # own namespace, unnamed
            ("xml", _XML_NS),                          # reserved
            ("schema", "http://schema.org/"),          # imported, other host
        ],
    )
    meta = peek_ontology_metadata(content)
    assert meta.prefix is None


def test_peek_owl_xml_same_host_prefix_used_when_no_iri_prefix_match() -> None:
    """A candidate under the ontology's own host is chosen even when its IRI is not
    a literal prefix of the ontology IRI (e.g. obo/iao.owl vs obo/IAO_)."""
    content = owl_xml(
        ontology_iri="http://purl.obolibrary.org/obo/iao.owl",
        prefixes=[
            ("schema", "http://schema.org/"),                    # imported, other host
            ("IAO", "http://purl.obolibrary.org/obo/IAO_"),      # own host, no prefix match
        ],
    )
    meta = peek_ontology_metadata(content)
    assert meta.prefix == "IAO"


def test_peek_owl_xml_xml_base_fallback_when_no_ontology_iri_attr() -> None:
    """base_iri is recovered from xml:base when the ontologyIRI attribute is absent."""
    content = owl_xml(
        xml_base="https://example.org/baseonto/",
        prefixes=[("myonto", "https://example.org/baseonto/")],
    )
    meta = peek_ontology_metadata(content)
    assert meta.base_iri == "https://example.org/baseonto/"


def test_peek_owl_xml_version_extracted_from_version_iri() -> None:
    """A date-formatted version is extracted from versionIRI when owl:versionInfo is absent."""
    content = owl_xml(
        ontology_iri="https://example.org/myonto/",
        version_iri="https://example.org/myonto/releases/2024-07-03/myonto.owl",
    )
    meta = peek_ontology_metadata(content)
    assert meta.version == "2024-07-03"


def test_peek_owl_xml_explicit_version_info_takes_priority_over_version_iri() -> None:
    content = owl_xml(
        version_iri="https://example.org/releases/2000-01-01/onto.owl",
        version_info="2.0",
    )
    meta = peek_ontology_metadata(content)
    assert meta.version == "2.0"


# ── rdflib path ───────────────────────────────────────────────────────────────


def test_peek_rdflib_longest_prefix_match_wins_over_parent_namespace() -> None:
    """The most specific namespace IRI (longest match) is returned, not a broader parent."""
    turtle = (
        b"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        b"@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        b"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        b"@prefix parent: <https://example.org/> .\n"
        b"@prefix child: <https://example.org/specific/> .\n"
        b"\n"
        b'<https://example.org/specific/> a owl:Ontology ;\n'
        b'    rdfs:label "Specific Ontology" .\n'
    )
    meta = peek_ontology_metadata(turtle)
    assert meta.prefix == "child"  # not "parent"
    assert meta.name == "Specific Ontology"


def test_peek_rdflib_turtle_extracts_name_and_version() -> None:
    turtle = (
        b"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        b"@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
        b"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        b"@prefix myonto: <https://example.org/myonto/> .\n"
        b"\n"
        b'<https://example.org/myonto/> a owl:Ontology ;\n'
        b'    rdfs:label "My Turtle Ontology" ;\n'
        b'    <http://www.w3.org/2002/07/owl#versionInfo> "3.1" .\n'
    )
    meta = peek_ontology_metadata(turtle)
    assert meta.name == "My Turtle Ontology"
    assert meta.version == "3.1"
    assert meta.base_iri == "https://example.org/myonto/"
    assert meta.prefix == "myonto"


# ── error handling ────────────────────────────────────────────────────────────


def test_peek_owl_xml_truncated_after_root_tag_returns_iri_but_not_label() -> None:
    """Root-element attributes survive truncation; child annotations do not."""
    full = owl_xml(ontology_iri="https://example.org/myonto/", label="Full Label")
    # Slice right after the <Ontology ...> opening line, before any child elements
    cut = full.index(b"\n", full.index(b"<Ontology")) + 1
    meta = peek_ontology_metadata(full[:cut])
    assert meta.base_iri == "https://example.org/myonto/"
    assert meta.name is None


def test_peek_corrupt_bytes_returns_empty_metadata() -> None:
    """Corrupt or non-OWL bytes must not raise; an empty OntologyMetadata is returned."""
    meta = peek_ontology_metadata(b"this is not owl at all !!!")
    assert meta == OntologyMetadata()


def test_peek_empty_bytes_returns_empty_metadata() -> None:
    meta = peek_ontology_metadata(b"")
    assert meta == OntologyMetadata()


def test_peek_rejects_entity_expansion_bomb() -> None:
    """A billion-laughs entity bomb must not be expanded; metadata comes back empty."""
    bomb = (
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE lolz [\n'
        b'  <!ENTITY a "AAAAAAAAAA">\n'
        b'  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
        b'  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">\n'
        b']>\n'
        b'<Ontology xmlns="http://www.w3.org/2002/07/owl#" ontologyIRI="https://example.org/o/">\n'
        b'  <Annotation>\n'
        b'    <AnnotationProperty abbreviatedIRI="rdfs:label"/>\n'
        b'    <Literal>&c;</Literal>\n'
        b'  </Annotation>\n'
        b'</Ontology>'
    )
    meta = peek_ontology_metadata(bomb)
    assert meta == OntologyMetadata()
