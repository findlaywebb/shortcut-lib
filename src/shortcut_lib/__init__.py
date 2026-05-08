"""Decode and author Apple Shortcuts files."""

from shortcut_lib.decode import DecodedShortcut, decode_file
from shortcut_lib.encode import EncodeError, encode_to_bplist, sign_to_file

__all__ = [
    "DecodedShortcut",
    "EncodeError",
    "decode_file",
    "encode_to_bplist",
    "sign_to_file",
]
