"""D3TextDB schema and utilities

This module provides the database layer used by D3Text text mining models and
by the D3 Annotation Hub.
"""

from .d3textdb import D3TextDB
from .owl import ParsedOntology, ParsedProperty, ParsedTriple, parse_owl

try:
    import stackprinter

    stackprinter.set_excepthook(style="darkbg2")
except ModuleNotFoundError:
    print("Initializing without stackprinter. Module not found.")

try:
    from beartype.claw import beartype_this_package

    beartype_this_package()
except ModuleNotFoundError:
    print("Initializing without beartype. Module not found.")

from icecream import ic, install

ic.configureOutput(includeContext=True)
install()

__all__ = ["D3TextDB", "ParsedOntology", "ParsedProperty", "ParsedTriple", "parse_owl"]
