"""Shared structural types."""

from __future__ import annotations

from typing import TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
Headers: TypeAlias = dict[str, str]
QueryParams: TypeAlias = dict[str, str | int | float | bool]
