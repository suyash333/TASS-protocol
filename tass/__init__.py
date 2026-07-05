"""
TASS — Tokeniser-Aware Structured Shorthand

A stenography-inspired output format for reducing LLM inference costs
by 75–85%% in structured extraction pipelines.

White paper: https://doi.org/10.5281/zenodo.20403219
License    : MIT
"""

from .parser import TASSParser, SchemaCompiler, TASSParseError, TASSValidationError
from .file_parser import TASSFileParser, TASSFile, TASSFileError
from .crypto import TASSSigner, TASSIntegrityError, hash_record, derive_key, canonicalize

__version__ = "0.1.0"
__author__ = "Suyash Sharma"
__doi__ = "10.5281/zenodo.20403219"

__all__ = [
    # Core parser
    "TASSParser",
    "SchemaCompiler",
    "TASSParseError",
    "TASSValidationError",
    # File format
    "TASSFileParser",
    "TASSFile",
    "TASSFileError",
    # Crypto
    "TASSSigner",
    "TASSIntegrityError",
    "hash_record",
    "derive_key",
    "canonicalize",
]
