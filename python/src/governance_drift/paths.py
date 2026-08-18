"""Resolve ``$.a[0].b`` index paths against decoded JSON or YAML payloads.

Evidence cites a field path, and §8.1 check (a) requires that path to be
machine-resolvable. This is deliberately a tiny subset of JSONPath: keys,
integer indices, and the ``$`` root. Nothing else is supported, because
nothing else is needed to cite a field.
"""

from __future__ import annotations

import re
from typing import Final, cast

_SEGMENT: Final = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


class FieldPathError(Exception):
    """Raised when a field path is malformed or does not resolve."""


def resolve(payload: object, field_path: str) -> object:
    """Resolve ``field_path`` against ``payload``.

    Args:
        payload: Decoded JSON or YAML.
        field_path: A path such as ``$.data[0].id``. ``$`` returns the root.

    Returns:
        The value at the path.

    Raises:
        FieldPathError: If the path is malformed or does not resolve.
    """
    if not field_path.startswith("$"):
        msg = f"field path must start with '$': {field_path!r}"
        raise FieldPathError(msg)

    current = payload
    for key, index in _SEGMENT.findall(field_path[1:]):
        if index:
            current = _index(current, int(index), field_path)
        else:
            current = _key(current, key, field_path)
    return current


def _key(current: object, key: str, field_path: str) -> object:
    """Step into a mapping by key.

    Args:
        current: The value being traversed.
        key: The key to read.
        field_path: The full path, for error messages.

    Returns:
        The value at ``key``.

    Raises:
        FieldPathError: If ``current`` is not a mapping or lacks ``key``.
    """
    if not isinstance(current, dict):
        msg = f"cannot read key {key!r} from a non-mapping in {field_path!r}"
        raise FieldPathError(msg)
    # cast, not a declared annotation: pyright strict narrows to
    # dict[Unknown, Unknown] and reportUnknownVariableType rejects the
    # annotated-assignment form. The isinstance guard makes this safe.
    typed = cast("dict[str, object]", current)
    if key not in typed:
        msg = f"key {key!r} not found in {field_path!r}"
        raise FieldPathError(msg)
    return typed[key]


def _index(current: object, index: int, field_path: str) -> object:
    """Step into a sequence by index.

    Args:
        current: The value being traversed.
        index: The index to read.
        field_path: The full path, for error messages.

    Returns:
        The value at ``index``.

    Raises:
        FieldPathError: If ``current`` is not a list or the index is invalid.
    """
    if not isinstance(current, list):
        msg = f"cannot index [{index}] into a non-sequence in {field_path!r}"
        raise FieldPathError(msg)
    typed = cast("list[object]", current)
    if index >= len(typed):
        msg = f"index [{index}] out of range in {field_path!r}"
        raise FieldPathError(msg)
    return typed[index]
