"""Contract 2 types used by render/ and checks/.

The real models live in contracts/types.py (Owner C). Until that lands, the
local mirrors below are used. Inputs are accepted as either a model or a
plain dict, and results are converted to the contract classes when available.
"""
from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

Status = Literal["pass", "warn", "fail"]


class LocalSettings(BaseModel):
    colors: List[str] = Field(default_factory=lambda: ["#E53935"])
    background: str = "#000000"
    size: Literal["small", "medium", "large"] = "medium"
    position: Literal["center", "left", "right", "upper", "lower"] = "center"
    text_mode: Literal["off", "below"] = "off"
    outline: Literal["off", "thin", "thick"] = "off"

    @field_validator("colors")
    @classmethod
    def _colors_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            return ["#E53935"]
        return v[:3]


class LocalCheck(BaseModel):
    status: Status
    value: Optional[float] = None
    detail: str = ""


class LocalCheckResult(BaseModel):
    fidelity: LocalCheck
    page_edge: LocalCheck
    background: Optional[LocalCheck] = None  # not checked at level 4
    contrast: LocalCheck
    size: LocalCheck
    text_contrast: Optional[LocalCheck] = None  # only when text is shown


class LocalSecondLook(BaseModel):
    status: Literal["pass", "warn", "pending"]
    answer: str = ""
    detail: str = ""


try:  # pragma: no cover - depends on Owner C's folder being present
    from contracts.types import CheckResult as _ContractCheckResult  # type: ignore
except Exception:  # noqa: BLE001
    _ContractCheckResult = None

try:  # pragma: no cover
    from contracts.types import SecondLook as _ContractSecondLook  # type: ignore
except Exception:  # noqa: BLE001
    _ContractSecondLook = None


def coerce_settings(settings: Union[BaseModel, dict, None]) -> LocalSettings:
    if settings is None:
        return LocalSettings()
    if isinstance(settings, LocalSettings):
        return settings
    if isinstance(settings, BaseModel):
        settings = settings.model_dump()
    return LocalSettings.model_validate(settings)


def to_contract_check_result(result: LocalCheckResult) -> Any:
    if _ContractCheckResult is None:
        return result
    try:
        return _ContractCheckResult.model_validate(result.model_dump())
    except Exception:  # noqa: BLE001
        return result


def to_contract_second_look(result: LocalSecondLook) -> Any:
    if _ContractSecondLook is None:
        return result
    try:
        return _ContractSecondLook.model_validate(result.model_dump())
    except Exception:  # noqa: BLE001
        return result
