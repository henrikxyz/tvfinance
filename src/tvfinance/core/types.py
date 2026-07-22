"""Shared structural types."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
Headers: TypeAlias = dict[str, str]
QueryScalar: TypeAlias = str | int | float | bool
QueryParams: TypeAlias = Mapping[str, QueryScalar] | Sequence[tuple[str, str]]
