"""D3TextDB schema and utilities

This module provides the database layer used by D3Text text mining models and
by the D3 Annotation Hub.
"""

try:
    from beartype.claw import beartype_this_package

    beartype_this_package()
except ModuleNotFoundError:
    pass

from .d3textdb import D3TextDB, DuplicateCurieError, OntologyInUseError
from .owl import MAX_PEEK_BYTES, OntologyMetadata, ParsedOntology, ParsedProperty, ParsedTriple, parse_owl, peek_ontology_metadata

try:
    import stackprinter

    stackprinter.set_excepthook(style="darkbg2")
except ModuleNotFoundError:
    pass

try:
    from icecream import ic, install

    ic.configureOutput(includeContext=True)
    install()
except ModuleNotFoundError:
    pass

__all__ = [
    "D3TextDB",
    "DuplicateCurieError",
    "MAX_PEEK_BYTES",
    "OntologyMetadata",
    "ParsedOntology",
    "ParsedProperty",
    "ParsedTriple",
    "parse_owl",
    "peek_ontology_metadata",
]
