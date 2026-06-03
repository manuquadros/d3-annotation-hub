"""Utilities for parsing OWL ontology files into d3textdb schema objects."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from rdflib import OWL, RDF, RDFS, SKOS, Graph, Namespace, URIRef

from .schema import EntityAnnotation

OBO_BASE = "http://purl.obolibrary.org/obo/"
OBO_IN_OWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")

_OWL_NS = "http://www.w3.org/2002/07/owl#"
_RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
_XML_NS = "http://www.w3.org/XML/1998/namespace"

_STANDARD_PREFIXES = frozenset({
    "", "owl", "rdf", "rdfs", "xsd", "dc", "dcterms", "skos",
    "obo", "oboInOwl",
})

# Number of leading bytes that peek_ontology_metadata needs to find the header.
# Callers must upload/read exactly this many bytes; the frontend's PEEK_BYTES
# constant in OntologyImportForm.svelte must be kept in sync with this value.
PEEK_BYTES = 65536

# OBO synonym annotation properties, in roughly decreasing specificity
SYNONYM_PREDICATES = [
    OBO_IN_OWL.hasExactSynonym,
    OBO_IN_OWL.hasSynonym,
    OBO_IN_OWL.hasNarrowSynonym,
    OBO_IN_OWL.hasBroadSynonym,
    OBO_IN_OWL.hasRelatedSynonym,
    SKOS.altLabel,
]

_SYNONYM_IRIS: frozenset[str] = frozenset(str(p) for p in SYNONYM_PREDICATES)

# Named-class predicates extracted as Triples
TRIPLE_PREDICATES = [
    str(RDFS.subClassOf),
    str(OWL.equivalentClass),
    str(SKOS.exactMatch),
    str(SKOS.closeMatch),
]


@dataclass
class ParsedTriple:
    """An ontology triple whose subject and object are identified by CURIE."""

    subject_curie: str
    predicate: str
    object_curie: str | None = None
    object_literal: str | None = None


@dataclass
class ParsedProperty:
    """An OWL object property extracted from an ontology."""

    curie: str
    label: str
    domain_curie: str | None = None
    range_curie: str | None = None


@dataclass
class ParsedOntology:
    """Entities, triples, and object properties extracted from an OWL file."""

    entities: list[EntityAnnotation] = field(default_factory=list)
    triples: list[ParsedTriple] = field(default_factory=list)
    properties: list[ParsedProperty] = field(default_factory=list)


@dataclass
class OntologyMetadata:
    """Ontology-level metadata extracted from an OWL file header."""

    name: str | None = None
    prefix: str | None = None
    base_iri: str | None = None
    version: str | None = None


def iri_to_curie(iri: str, prefix: str, base_iri: str) -> str:
    """Convert an OWL class IRI to a CURIE string.

    For OBO Foundry IRIs (``http://purl.obolibrary.org/obo/``), the local
    segment already encodes the prefix: ``NCBITaxon_562`` → ``NCBITaxon:562``.

    For any other IRI, strips ``base_iri`` and prepends ``prefix``.
    Falls back to the last path/fragment component if neither matches.
    """
    if iri.startswith(OBO_BASE):
        local = iri[len(OBO_BASE) :]
        return local.replace("_", ":", 1)
    if base_iri and iri.startswith(base_iri):
        return f"{prefix}:{iri[len(base_iri) :]}"
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _is_owl_xml(content: bytes) -> bool:
    """Return True if ``content`` is OWL/XML (Functional Syntax in XML).

    OWL/XML has ``<Ontology xmlns="http://www.w3.org/2002/07/owl#">`` as root,
    as opposed to RDF/XML which has ``<rdf:RDF …>`` as root.
    """
    head = content[:4096]
    return (
        b'xmlns="http://www.w3.org/2002/07/owl#"' in head
        or b"xmlns='http://www.w3.org/2002/07/owl#'" in head
    )


def _rdflib_format(content: bytes) -> str:
    """Guess the rdflib format string for ``content``."""
    head = content[:256].lstrip()
    if head.startswith(b"{"):
        return "json-ld"
    if head.startswith(b"<"):
        return "xml"  # RDF/XML
    return "turtle"


def _parse_owl_xml(
    content: bytes, prefix: str, base_iri: str
) -> ParsedOntology:
    """Parse OWL/XML (Functional Syntax in XML serialization) using ElementTree.

    This handles the format written by Protégé and the OWL API, where the root
    element is ``<Ontology xmlns="http://www.w3.org/2002/07/owl#">``.
    """
    root = ET.fromstring(content)

    xml_base: str = root.get(f"{{{_XML_NS}}}base", base_iri) or base_iri

    # Collect prefix declarations: <Prefix name="d3o" IRI="https://…"/>
    ns_map: dict[str, str] = {}
    for elem in root.iter(f"{{{_OWL_NS}}}Prefix"):
        name = elem.get("name", "")
        iri = elem.get("IRI", "")
        if iri:
            ns_map[name] = iri

    def resolve_iri(short: str) -> str:
        if short.startswith("http://") or short.startswith("https://"):
            return short
        if ":" in short:
            pfx, local = short.split(":", 1)
            if pfx in ns_map:
                return ns_map[pfx] + local
        return xml_base.rstrip("/") + "/" + short if xml_base else short

    def elem_iri(elem: ET.Element) -> str | None:
        v = elem.get("IRI")
        if v is not None:
            return resolve_iri(v)
        v = elem.get("abbreviatedIRI")
        if v is not None:
            return resolve_iri(v)
        return None

    # Collect declared owl:Class IRIs and owl:ObjectProperty IRIs
    declared: set[str] = set()
    declared_properties: set[str] = set()
    for decl in root.iter(f"{{{_OWL_NS}}}Declaration"):
        cls_elem = decl.find(f"{{{_OWL_NS}}}Class")
        if cls_elem is not None:
            iri = elem_iri(cls_elem)
            if iri:
                declared.add(iri)
        prop_elem = decl.find(f"{{{_OWL_NS}}}ObjectProperty")
        if prop_elem is not None:
            iri = elem_iri(prop_elem)
            if iri:
                declared_properties.add(iri)

    # Collect rdfs:label and synonym annotations from <AnnotationAssertion>
    labels: dict[
        str, str
    ] = {}  # IRI → preferred label (classes and properties)
    synonyms: dict[str, list[str]] = {}
    annotated_iris = declared | declared_properties

    for ann in root.iter(f"{{{_OWL_NS}}}AnnotationAssertion"):
        prop = ann.find(f"{{{_OWL_NS}}}AnnotationProperty")
        subj = ann.find(f"{{{_OWL_NS}}}IRI")
        lit = ann.find(f"{{{_OWL_NS}}}Literal")
        if prop is None or subj is None or lit is None:
            continue

        prop_iri = elem_iri(prop)
        subj_iri = resolve_iri(subj.text or "")
        if subj_iri not in annotated_iris:
            continue

        value = lit.text or ""
        lang = lit.get(f"{{{_XML_NS}}}lang", "")

        if prop_iri == f"{_RDFS_NS}label":
            # Prefer English; accept any if no English label seen yet
            if subj_iri not in labels or lang in ("en", ""):
                labels[subj_iri] = value
        elif prop_iri in _SYNONYM_IRIS and subj_iri in declared:
            synonyms.setdefault(subj_iri, []).append(value)

    # Collect direct superclasses from <SubClassOf>
    superclass: dict[str, str] = {}  # IRI → first named superclass IRI
    for sc in root.iter(f"{{{_OWL_NS}}}SubClassOf"):
        children = list(sc)
        if len(children) < 2:
            continue
        sub_iri = (
            elem_iri(children[0])
            if children[0].tag == f"{{{_OWL_NS}}}Class"
            else None
        )
        sup_iri = (
            elem_iri(children[1])
            if children[1].tag == f"{{{_OWL_NS}}}Class"
            else None
        )
        if (
            sub_iri
            and sup_iri
            and sub_iri in declared
            and sub_iri not in superclass
        ):
            superclass[sub_iri] = sup_iri

    result = ParsedOntology()
    seen_curies: set[str] = set()

    for cls_iri in declared:
        label = labels.get(cls_iri)
        if label is None:
            continue

        curie = iri_to_curie(cls_iri, prefix, base_iri)
        sup_iri = superclass.get(cls_iri)
        kind = iri_to_curie(sup_iri, prefix, base_iri) if sup_iri else ""

        result.entities.append(
            EntityAnnotation(
                entity_id=curie,
                preferred_name=label,
                kind=kind,
                synonyms=synonyms.get(cls_iri, []),
                is_class=True,
            )
        )
        seen_curies.add(curie)

    for sc in root.iter(f"{{{_OWL_NS}}}SubClassOf"):
        children = list(sc)
        if len(children) != 2:
            continue
        if (
            children[0].tag != f"{{{_OWL_NS}}}Class"
            or children[1].tag != f"{{{_OWL_NS}}}Class"
        ):
            continue
        sub_iri = elem_iri(children[0])
        sup_iri = elem_iri(children[1])
        if sub_iri and sup_iri:
            s_curie = iri_to_curie(sub_iri, prefix, base_iri)
            if s_curie in seen_curies:
                result.triples.append(
                    ParsedTriple(
                        subject_curie=s_curie,
                        predicate=str(RDFS.subClassOf),
                        object_curie=iri_to_curie(sup_iri, prefix, base_iri),
                    )
                )

    prop_domain: dict[str, str] = {}
    prop_range: dict[str, str] = {}

    for elem in root.iter(f"{{{_OWL_NS}}}ObjectPropertyDomain"):
        children = list(elem)
        if len(children) < 2:
            continue
        prop_iri = (
            elem_iri(children[0])
            if children[0].tag == f"{{{_OWL_NS}}}ObjectProperty"
            else None
        )
        cls_iri = (
            elem_iri(children[1])
            if children[1].tag == f"{{{_OWL_NS}}}Class"
            else None
        )
        if prop_iri and cls_iri and prop_iri not in prop_domain:
            prop_domain[prop_iri] = cls_iri

    for elem in root.iter(f"{{{_OWL_NS}}}ObjectPropertyRange"):
        children = list(elem)
        if len(children) < 2:
            continue
        prop_iri = (
            elem_iri(children[0])
            if children[0].tag == f"{{{_OWL_NS}}}ObjectProperty"
            else None
        )
        cls_iri = (
            elem_iri(children[1])
            if children[1].tag == f"{{{_OWL_NS}}}Class"
            else None
        )
        if prop_iri and cls_iri and prop_iri not in prop_range:
            prop_range[prop_iri] = cls_iri

    for prop_iri in declared_properties:
        label = labels.get(prop_iri)
        if label is None:
            continue
        curie = iri_to_curie(prop_iri, prefix, base_iri)
        domain_iri = prop_domain.get(prop_iri)
        range_iri = prop_range.get(prop_iri)
        result.properties.append(
            ParsedProperty(
                curie=curie,
                label=label,
                domain_curie=iri_to_curie(domain_iri, prefix, base_iri)
                if domain_iri
                else None,
                range_curie=iri_to_curie(range_iri, prefix, base_iri)
                if range_iri
                else None,
            )
        )

    return result


def _direct_superclass_curie(
    g: Graph, cls: URIRef, prefix: str, base_iri: str
) -> str | None:
    """Return the CURIE of the first named (non-blank, non-owl:Thing) superclass."""
    for parent in g.objects(cls, RDFS.subClassOf):
        if isinstance(parent, URIRef) and parent != OWL.Thing:
            return iri_to_curie(str(parent), prefix, base_iri)
    return None


def _parse_owl_rdflib(
    content: bytes, prefix: str, base_iri: str, fmt: str
) -> ParsedOntology:
    """Parse an RDF serialization (RDF/XML, Turtle, JSON-LD, …) with rdflib."""
    import io

    g = Graph()
    g.parse(io.BytesIO(content), format=fmt)

    result = ParsedOntology()
    seen_curies: set[str] = set()

    for cls in g.subjects(RDF.type, OWL.Class):
        if not isinstance(cls, URIRef):
            continue

        curie = iri_to_curie(str(cls), prefix, base_iri)

        label: str | None = None
        for obj in g.objects(cls, RDFS.label):
            if label is None:
                label = str(obj)
            if getattr(obj, "language", None) in ("en", None, ""):
                label = str(obj)
                break

        if label is None:
            continue

        synonyms = [
            str(o) for pred in SYNONYM_PREDICATES for o in g.objects(cls, pred)
        ]
        kind = _direct_superclass_curie(g, cls, prefix, base_iri)

        result.entities.append(
            EntityAnnotation(
                entity_id=curie,
                preferred_name=label,
                kind=kind or "",
                synonyms=synonyms,
                is_class=True,
            )
        )
        seen_curies.add(curie)

    for predicate_iri in TRIPLE_PREDICATES:
        predicate_ref = URIRef(predicate_iri)
        for subj, obj in g.subject_objects(predicate_ref):
            if not isinstance(subj, URIRef) or not isinstance(obj, URIRef):
                continue
            s_curie = iri_to_curie(str(subj), prefix, base_iri)
            if s_curie not in seen_curies:
                continue
            o_curie = iri_to_curie(str(obj), prefix, base_iri)
            result.triples.append(
                ParsedTriple(
                    subject_curie=s_curie,
                    predicate=predicate_iri,
                    object_curie=o_curie,
                )
            )

    # Extract owl:ObjectProperty declarations with domain and range
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not isinstance(prop, URIRef):
            continue
        label: str | None = None
        for obj in g.objects(prop, RDFS.label):
            if label is None:
                label = str(obj)
            if getattr(obj, "language", None) in ("en", None, ""):
                label = str(obj)
                break
        if label is None:
            continue
        prop_curie = iri_to_curie(str(prop), prefix, base_iri)
        domains = [
            o for o in g.objects(prop, RDFS.domain) if isinstance(o, URIRef)
        ]
        ranges = [
            o for o in g.objects(prop, RDFS.range) if isinstance(o, URIRef)
        ]
        result.properties.append(
            ParsedProperty(
                curie=prop_curie,
                label=label,
                domain_curie=iri_to_curie(str(domains[0]), prefix, base_iri)
                if domains
                else None,
                range_curie=iri_to_curie(str(ranges[0]), prefix, base_iri)
                if ranges
                else None,
            )
        )

    return result


def _peek_owl_xml_meta(content: bytes) -> OntologyMetadata:
    # Tags that signal the end of the header section (start of class/property body)
    _HEADER_END_TAGS = frozenset({
        f"{{{_OWL_NS}}}Declaration",
        f"{{{_OWL_NS}}}SubClassOf",
        f"{{{_OWL_NS}}}EquivalentClasses",
        f"{{{_OWL_NS}}}DisjointClasses",
        f"{{{_OWL_NS}}}AnnotationAssertion",
        f"{{{_OWL_NS}}}ObjectPropertyDomain",
        f"{{{_OWL_NS}}}ObjectPropertyRange",
    })

    base_iri: str | None = None
    version_iri: str | None = None
    name: str | None = None
    version: str | None = None
    candidates: list[tuple[str, str]] = []

    depth = 0
    in_top_annotation = False
    current_prop: str | None = None
    current_literal: str | None = None

    try:
        for event, elem in ET.iterparse(io.BytesIO(content), events=("start", "end")):
            tag = elem.tag
            if event == "start":
                depth += 1
                if depth == 1 and tag == f"{{{_OWL_NS}}}Ontology":
                    base_iri = elem.get("ontologyIRI") or elem.get(f"{{{_XML_NS}}}base") or None
                    version_iri = elem.get("versionIRI") or None
                elif depth == 2:
                    if tag in _HEADER_END_TAGS:
                        break  # past the header — no more metadata to find
                    if tag == f"{{{_OWL_NS}}}Prefix":
                        pfx_name = elem.get("name", "")
                        pfx_iri = elem.get("IRI", "")
                        if pfx_name and pfx_name not in _STANDARD_PREFIXES:
                            candidates.append((pfx_name, pfx_iri))
                    elif tag == f"{{{_OWL_NS}}}Annotation":
                        in_top_annotation = True
                        current_prop = None
                        current_literal = None
                elif in_top_annotation:
                    if tag == f"{{{_OWL_NS}}}AnnotationProperty":
                        prop_iri = elem.get("abbreviatedIRI") or elem.get("IRI", "")
                        if prop_iri in ("rdfs:label", f"{_RDFS_NS}label"):
                            current_prop = "label"
                        elif prop_iri in ("owl:versionInfo", f"{_OWL_NS}versionInfo"):
                            current_prop = "version"
            elif event == "end":
                if in_top_annotation:
                    if tag == f"{{{_OWL_NS}}}Literal" and current_prop:
                        current_literal = elem.text
                    elif tag == f"{{{_OWL_NS}}}Annotation" and depth == 2:
                        in_top_annotation = False
                        if current_prop == "label" and current_literal and name is None:
                            name = current_literal
                        elif current_prop == "version" and current_literal and version is None:
                            version = current_literal
                depth -= 1
    except ET.ParseError:
        pass  # truncated input — use whatever was extracted before the cut

    if version is None and version_iri:
        m = re.search(r"(\d{4}-\d{2}-\d{2}|\d+\.\d+(?:\.\d+)*)", version_iri)
        if m:
            version = m.group(1)

    prefix: str | None = None
    if candidates:
        if base_iri:
            # Prefer the candidate whose IRI is the longest prefix of the ontology IRI
            # (finds the ontology's own namespace rather than an imported one)
            iri_match = max(
                ((n, i) for n, i in candidates if i and base_iri.startswith(i)),
                key=lambda x: len(x[1]),
                default=None,
            )
            prefix = iri_match[0] if iri_match else candidates[0][0]
        else:
            prefix = candidates[0][0]

    return OntologyMetadata(name=name, prefix=prefix, base_iri=base_iri, version=version)


def _peek_owl_rdflib_meta(content: bytes, fmt: str) -> OntologyMetadata:
    g = Graph()
    g.parse(io.BytesIO(content), format=fmt)

    onto_iri: str | None = None
    for subj in g.subjects(RDF.type, OWL.Ontology):
        if isinstance(subj, URIRef):
            onto_iri = str(subj)
            break

    name: str | None = None
    version: str | None = None

    if onto_iri:
        onto_ref = URIRef(onto_iri)
        for obj in g.objects(onto_ref, RDFS.label):
            name = str(obj)
            break
        for obj in g.objects(onto_ref, OWL.versionInfo):
            version = str(obj)
            break

    # Longest-match: prefer the most specific namespace IRI that is a prefix of
    # the ontology IRI, to avoid false positives from parent namespaces.
    prefix: str | None = None
    if onto_iri:
        best_pfx: str | None = None
        best_ns_len = 0
        for pfx, ns in g.namespaces():
            pfx_str = str(pfx)
            ns_str = str(ns)
            if (pfx_str and pfx_str not in _STANDARD_PREFIXES
                    and onto_iri.startswith(ns_str)
                    and len(ns_str) > best_ns_len):
                best_pfx = pfx_str
                best_ns_len = len(ns_str)
        prefix = best_pfx

    return OntologyMetadata(name=name, prefix=prefix, base_iri=onto_iri, version=version)


def peek_ontology_metadata(content: bytes) -> OntologyMetadata:
    """Extract ontology-level metadata from an OWL file without full parsing.

    Returns best-effort results; any field may be ``None`` if not found.
    Never raises — returns an empty :class:`OntologyMetadata` on any error.
    """
    try:
        if _is_owl_xml(content):
            return _peek_owl_xml_meta(content)
        return _peek_owl_rdflib_meta(content, _rdflib_format(content))
    except Exception:
        return OntologyMetadata()


def parse_owl(
    source: str | Path | BinaryIO | bytes,
    prefix: str,
    base_iri: str,
) -> ParsedOntology:
    """Parse an OWL file and extract classes, names, synonyms, and triples.

    :param source: Path to an OWL file, a file-like object, or raw bytes.
        Supported serializations: OWL/XML (Functional Syntax in XML), RDF/XML,
        Turtle, N-Triples, JSON-LD.
    :param prefix: Short namespace prefix used for CURIE generation
        (e.g. ``"NCBITaxon"``).  Ignored for OBO Foundry IRIs.
    :param base_iri: Namespace IRI for non-OBO ontologies.  For OBO Foundry
        ontologies this can be left as an empty string.
    :return: :class:`ParsedOntology` with entities and triples ready for
        loading into the database via :meth:`D3TextDB.load_ontology_entities`
        and :meth:`D3TextDB.load_ontology_triples`.

    Each entity's ``kind`` is set to the CURIE of its direct named superclass
    in the OWL hierarchy (``rdfs:subClassOf``).  Root classes (no named
    superclass other than ``owl:Thing``) get an empty ``kind``.
    """
    if isinstance(source, bytes):
        content = source
    elif isinstance(source, (str, Path)):
        content = Path(source).read_bytes()
    else:
        content = source.read()

    if _is_owl_xml(content):
        return _parse_owl_xml(content, prefix, base_iri)

    return _parse_owl_rdflib(content, prefix, base_iri, _rdflib_format(content))
