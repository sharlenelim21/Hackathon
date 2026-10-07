"""Pydantic models that validate (and gently repair) the LLM's JSON output."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _as_list(v: Any) -> list[str]:
    if v is None or v == "":
        return []
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v if x not in (None, "")]


def _as_text(v: Any) -> str | None:
    if v is None or v == "":
        return None
    return v if isinstance(v, str) else str(v)


class Facts(_Base):
    activity: str | None = None
    location: str | None = None
    area_ha: float | None = None
    land_status: str | None = None

    @field_validator("area_ha", mode="before")
    @classmethod
    def _number(cls, v: Any) -> float | None:
        if v in (None, ""):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        m = re.search(r"\d+(?:\.\d+)?", str(v))
        return float(m.group()) if m else None

    @field_validator("activity", "location", "land_status", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str | None:
        return _as_text(v)


class PickedSection(_Base):
    key: str
    reason: str = ""


class PlanOut(_Base):
    facts: Facts = Field(default_factory=Facts)
    missing_facts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    laws: list[str] = Field(default_factory=list)
    sections: list[PickedSection] = Field(default_factory=list)

    @field_validator("missing_facts", "tags", "laws", mode="before")
    @classmethod
    def _lists(cls, v: Any) -> list[str]:
        return _as_list(v)

    @field_validator("sections", mode="before")
    @classmethod
    def _sections(cls, v: Any) -> list:
        return [{"key": x} if isinstance(x, str) else x for x in (v or [])]

    @field_validator("facts", mode="before")
    @classmethod
    def _facts(cls, v: Any) -> Any:
        return v or {}


class CondOut(_Base):
    key: str
    subsection: str | None = None
    requirement: str = ""
    why: str = ""
    quote: str = ""

    @field_validator("subsection", mode="before")
    @classmethod
    def _sub(cls, v: Any) -> str | None:
        return _as_text(v)


class ConditionsOut(_Base):
    conditions: list[CondOut] = Field(default_factory=list)
    explanation: str = ""

    @field_validator("conditions", mode="before")
    @classmethod
    def _conds(cls, v: Any) -> list:
        return v or []
