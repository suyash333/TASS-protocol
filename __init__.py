# Backwards-compatibility shim — the tass/ package is the canonical location.
from tass import (  # noqa: F401
    TASSParser,
    SchemaCompiler,
    TASSParseError,
    TASSValidationError,
    TASSFileParser,
    TASSFile,
    TASSFileError,
)

__version__ = "0.1.0"
