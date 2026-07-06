"""Utilities for parsing OWL ontology files into d3textdb schema objects."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

import pyoxigraph as ox
from defusedxml.ElementTree import fromstring as _safe_fromstring
from defusedxml.ElementTree import iterparse as _safe_iterparse
from rdflib import OWL, RDF, RDFS, SKOS, Graph, Namespace, URIRef

from .schema import EntityAnnotation

OBO_BASE = "http://purl.obolibrary.org/obo/"
OBO_IN_OWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")

_OWL_NS = "http://www.w3.org/2002/07/owl#"
_RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
_XML_NS = "http://www.w3.org/XML/1998/namespace"

_STANDARD_PREFIXES = frozenset({
    "", "xml", "owl", "rdf", "rdfs", "xsd", "dc", "dcterms", "skos",
    "obo", "oboInOwl",
})

# Upper bound on how many bytes peek_ontology_metadata will read and parse.
# OWL/XML metadata lives in the header and is streamed cheaply (parsing stops at
# the first body element), but the rdflib formats (RDF/XML, Turtle, JSON-LD)
# require a complete, well-formed document, so the whole file up to this size is
# parsed. Larger files skip the peek and the user fills the import fields
# manually. The frontend's MAX_PEEK_BYTES constant in OntologyImportForm.svelte
# must be kept in sync with this value.
MAX_PEEK_BYTES = 50 * 1024 * 1024

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
_TRIPLE_PREDICATE_IRIS: frozenset[str] = frozenset(TRIPLE_PREDICATES)

# Predicate/type IRIs compared as plain strings in the streaming RDF parser.
_RDF_TYPE = str(RDF.type)
_OWL_CLASS = str(OWL.Class)
_OWL_OBJECT_PROPERTY = str(OWL.ObjectProperty)
_OWL_THING = str(OWL.Thing)
_RDFS_LABEL = str(RDFS.label)
_RDFS_SUBCLASSOF = str(RDFS.subClassOf)
_RDFS_DOMAIN = str(RDFS.domain)
_RDFS_RANGE = str(RDFS.range)

# _rdflib_format() guess → pyoxigraph format for the streaming RDF path.
_OX_RDF_FORMATS = {
    "xml": ox.RdfFormat.RDF_XML,
    "turtle": ox.RdfFormat.TURTLE,
    "json-ld": ox.RdfFormat.JSON_LD,
}


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
    # _safe_fromstring forbids entity expansion and external references
    # (billion-laughs / XXE) on the attacker-supplied upload; the plain
    # ET.fromstring this replaced was vulnerable to both.
    root = _safe_fromstring(content)

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


# How far into the upload we scan for a DTD internal subset. The subset (if
# present) always precedes the root element; a DTD larger than this is itself
# abnormal and rejected. pyoxigraph — like the rdflib parser it replaced —
# expands XML entities and has no expansion-limit knob, so this guard is the
# only defence against billion-laughs on the RDF/XML path.
_DTD_SCAN_LIMIT = 1024 * 1024

_ENTITY_DECL_RE = re.compile(rb"<!ENTITY\s[^>]*?(\"[^\"]*\"|'[^']*')\s*>")
# A general (&name;) or parameter (%name;) entity reference — not a numeric
# character reference (&#123;), which cannot recurse.
_ENTITY_REF_RE = re.compile(rb"[&%]([A-Za-z_][\w.-]*);")
_PREDEFINED_ENTITIES = frozenset({b"amp", b"lt", b"gt", b"quot", b"apos"})


def _dtd_internal_subset(data: bytes) -> bytes | None:
    """Return the bytes inside a DTD internal subset ``[...]``, if any.

    Returns ``b""`` when a subset is opened but not closed within ``data`` —
    the caller treats an unterminated subset as suspicious.
    """
    doctype = data.find(b"<!DOCTYPE")
    if doctype == -1:
        return None
    opening = data.find(b"[", doctype)
    if opening == -1:
        return None
    closing = data.find(b"]", opening)
    if closing == -1:
        return b""  # subset larger than the scan window
    return data[opening + 1 : closing]


def _reject_entity_expansion_bomb(data: bytes) -> None:
    """Raise if the DTD declares a recursive/nested entity (billion-laughs).

    Flat entity declarations (e.g. OBO namespace abbreviations such as
    ``<!ENTITY obo "http://purl.obolibrary.org/obo/">``) are allowed; only
    declarations whose value references another non-predefined entity — the
    ingredient of an expansion bomb — are refused.
    """
    subset = _dtd_internal_subset(data)
    if subset is None:
        return
    for decl in _ENTITY_DECL_RE.finditer(subset):
        value = decl.group(1)[1:-1]
        if any(
            ref.group(1) not in _PREDEFINED_ENTITIES
            for ref in _ENTITY_REF_RE.finditer(value)
        ):
            raise ValueError(
                "ontology DTD declares nested XML entities (possible "
                "expansion bomb); refusing to parse"
            )
    if subset == b"" and data.find(b"[", data.find(b"<!DOCTYPE")) != -1:
        raise ValueError(
            "ontology DTD internal subset exceeds the scan limit; "
            "refusing to parse"
        )


class _SubjectAcc:
    """Mutable per-subject accumulator used during one streaming RDF pass."""

    __slots__ = (
        "is_class",
        "is_property",
        "label",
        "label_locked",
        "synonyms",
        "kind_iri",
        "domain_iri",
        "range_iri",
    )

    def __init__(self) -> None:
        self.is_class = False
        self.is_property = False
        self.label: str | None = None
        self.label_locked = False
        self.synonyms: list[str] = []
        self.kind_iri: str | None = None
        self.domain_iri: str | None = None
        self.range_iri: str | None = None

    def offer_label(self, value: str, language: str | None) -> None:
        # Mirror the previous rdflib behaviour: the first label seen wins
        # tentatively, and the first English/untagged label locks in.
        if self.label is None:
            self.label = value
        if not self.label_locked and language in ("en", None, ""):
            self.label = value
            self.label_locked = True


class OntologyStreamParser:
    """Extract classes, synonyms, triples, and object properties from an
    ontology without materializing the whole graph.

    RDF serializations (RDF/XML, Turtle, JSON-LD, N-Triples) are streamed with
    pyoxigraph, so peak memory is O(number of labelled subjects) for the
    in-flight index rather than O(number of triples) for a full in-memory
    graph — the difference between ~1 GB and tens of GB on ontologies the size
    of NCBITaxon. OWL/XML (Functional Syntax) still uses the in-memory
    ElementTree parse (it is a distinct serialization pyoxigraph does not read).

    The source is re-read on each ``iter_*`` call, so prefer constructing with a
    file ``path`` (streamed from disk) over ``content`` bytes for large files.
    ``iter_entities`` must be consumed before reading ``properties`` (they are
    produced by the same pass); ``parse_owl`` and the import endpoint call them
    in that order.
    """

    def __init__(
        self,
        *,
        prefix: str,
        base_iri: str,
        path: str | Path | None = None,
        content: bytes | None = None,
    ) -> None:
        if (path is None) == (content is None):
            raise ValueError("provide exactly one of path or content")
        self._prefix = prefix
        self._base_iri = base_iri
        self._path = str(path) if path is not None else None
        self._content = content
        head = self._read_head()
        self._is_owl_xml = _is_owl_xml(head)
        if self._is_owl_xml:
            self._ox_format = None
        else:
            self._ox_format = _OX_RDF_FORMATS[_rdflib_format(head)]
            # The OWL/XML path is guarded by defusedxml; the RDF/XML path is
            # not (pyoxigraph expands entities), so screen the DTD here.
            _reject_entity_expansion_bomb(self._read_head(_DTD_SCAN_LIMIT))
        self._materialized: ParsedOntology | None = None
        self._properties: list[ParsedProperty] | None = None

    def _read_head(self, n: int = 4096) -> bytes:
        if self._content is not None:
            return self._content[:n]
        with open(self._path, "rb") as f:  # noqa: PTH123
            return f.read(n)

    def _rdf_quads(self) -> Iterator[ox.Quad]:
        base = self._base_iri or None
        if self._path is not None:
            return ox.parse(
                path=self._path, format=self._ox_format, base_iri=base
            )
        return ox.parse(self._content, format=self._ox_format, base_iri=base)

    def _curie(self, iri: str) -> str:
        return iri_to_curie(iri, self._prefix, self._base_iri)

    def _owl_xml(self) -> ParsedOntology:
        if self._materialized is None:
            content = (
                self._content
                if self._content is not None
                else Path(self._path).read_bytes()
            )
            self._materialized = _parse_owl_xml(
                content, self._prefix, self._base_iri
            )
        return self._materialized

    def iter_entities(self) -> Iterator[EntityAnnotation]:
        """Yield the ontology's named classes (those with a label)."""
        if self._is_owl_xml:
            self._properties = self._owl_xml().properties
            yield from self._owl_xml().entities
            return
        yield from self._iter_rdf_entities()

    def iter_triples(self) -> Iterator[ParsedTriple]:
        """Yield subClassOf / equivalentClass / exact- & closeMatch triples.

        Triples whose subject or object is not a loaded entity are dropped
        later by :meth:`D3TextDB.load_ontology_triples`.
        """
        if self._is_owl_xml:
            yield from self._owl_xml().triples
            return
        for quad in self._rdf_quads():
            predicate = quad.predicate.value
            if predicate not in _TRIPLE_PREDICATE_IRIS:
                continue
            subject, obj = quad.subject, quad.object
            if isinstance(subject, ox.NamedNode) and isinstance(
                obj, ox.NamedNode
            ):
                yield ParsedTriple(
                    subject_curie=self._curie(subject.value),
                    predicate=predicate,
                    object_curie=self._curie(obj.value),
                )

    @property
    def properties(self) -> list[ParsedProperty]:
        """Object properties; valid once ``iter_entities`` has been consumed."""
        if self._is_owl_xml:
            return self._owl_xml().properties
        if self._properties is None:
            for _ in self._iter_rdf_entities():
                pass
        return self._properties or []

    def _iter_rdf_entities(self) -> Iterator[EntityAnnotation]:
        acc: dict[str, _SubjectAcc] = {}
        for quad in self._rdf_quads():
            subject = quad.subject
            if not isinstance(subject, ox.NamedNode):
                continue
            predicate = quad.predicate.value
            obj = quad.object
            if predicate == _RDF_TYPE and isinstance(obj, ox.NamedNode):
                if obj.value == _OWL_CLASS:
                    acc.setdefault(subject.value, _SubjectAcc()).is_class = True
                elif obj.value == _OWL_OBJECT_PROPERTY:
                    acc.setdefault(
                        subject.value, _SubjectAcc()
                    ).is_property = True
            elif predicate == _RDFS_LABEL and isinstance(obj, ox.Literal):
                acc.setdefault(subject.value, _SubjectAcc()).offer_label(
                    obj.value, obj.language
                )
            elif predicate in _SYNONYM_IRIS and isinstance(obj, ox.Literal):
                acc.setdefault(subject.value, _SubjectAcc()).synonyms.append(
                    obj.value
                )
            elif predicate == _RDFS_SUBCLASSOF and isinstance(
                obj, ox.NamedNode
            ):
                if obj.value != _OWL_THING:
                    entry = acc.setdefault(subject.value, _SubjectAcc())
                    if entry.kind_iri is None:
                        entry.kind_iri = obj.value
            elif predicate == _RDFS_DOMAIN and isinstance(obj, ox.NamedNode):
                entry = acc.setdefault(subject.value, _SubjectAcc())
                if entry.domain_iri is None:
                    entry.domain_iri = obj.value
            elif predicate == _RDFS_RANGE and isinstance(obj, ox.NamedNode):
                entry = acc.setdefault(subject.value, _SubjectAcc())
                if entry.range_iri is None:
                    entry.range_iri = obj.value

        self._properties = [
            ParsedProperty(
                curie=self._curie(iri),
                label=entry.label,
                domain_curie=self._curie(entry.domain_iri)
                if entry.domain_iri
                else None,
                range_curie=self._curie(entry.range_iri)
                if entry.range_iri
                else None,
            )
            for iri, entry in acc.items()
            if entry.is_property and entry.label is not None
        ]

        for iri, entry in acc.items():
            if entry.is_class and entry.label is not None:
                yield EntityAnnotation(
                    entity_id=self._curie(iri),
                    preferred_name=entry.label,
                    kind=self._curie(entry.kind_iri) if entry.kind_iri else "",
                    synonyms=entry.synonyms,
                    is_class=True,
                )


def _select_own_prefix(
    candidates: list[tuple[str, str]], base_iri: str | None
) -> str | None:
    """Pick the prefix that names the ontology's own namespace, or None.

    ``candidates`` are ``(name, IRI)`` pairs of non-standard ``<Prefix>``
    declarations, in document order. The goal is the prefix for the ontology's
    own entities, not an imported vocabulary (schema.org, ENVO, the reserved
    ``xml`` namespace, …).
    """
    if not candidates:
        return None
    if not base_iri:
        return candidates[0][0]

    # Prefer the candidate whose IRI is the longest prefix of the ontology IRI —
    # the ontology's own namespace declared with a matching IRI.
    iri_match = max(
        ((n, i) for n, i in candidates if i and base_iri.startswith(i)),
        key=lambda x: len(x[1]),
        default=None,
    )
    if iri_match:
        return iri_match[0]

    # No IRI-prefix match: an ontology's own entity namespace can diverge from
    # its ontology IRI (e.g. obo/iao.owl vs obo/IAO_). Fall back to a candidate
    # under the same authority as the ontology IRI, so imported vocabularies on
    # other hosts are never suggested.
    base_host = urlsplit(base_iri).netloc
    if base_host:
        for name, iri in candidates:
            if urlsplit(iri).netloc == base_host:
                return name
    return None


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
        # _safe_iterparse forbids entity expansion (billion-laughs / XXE) on
        # the uploaded file, which a plain ET.iterparse would be vulnerable to.
        for event, elem in _safe_iterparse(io.BytesIO(content), events=("start", "end")):
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

    prefix = _select_own_prefix(candidates, base_iri)

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

    This materializes the whole result in memory; for large ontologies prefer
    :class:`OntologyStreamParser` and load its ``iter_*`` output in batches.
    """
    if isinstance(source, (str, Path)):
        parser = OntologyStreamParser(
            path=source, prefix=prefix, base_iri=base_iri
        )
    else:
        content = source if isinstance(source, bytes) else source.read()
        parser = OntologyStreamParser(
            content=content, prefix=prefix, base_iri=base_iri
        )

    result = ParsedOntology()
    result.entities = list(parser.iter_entities())
    result.properties = parser.properties
    result.triples = list(parser.iter_triples())
    return result
