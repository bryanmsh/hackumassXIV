"""Contract 2 types, shared by api/, pipeline/, render/ and checks/.

Frozen: fields may be added, never renamed or removed.
Every position here is in pixels of the master page image, from the top-left corner.
"""
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

HexColor = Annotated[
    str,
    StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$"),
    AfterValidator(str.upper),  # one spelling per color, so settings_hash is stable
]
Level = Literal[1, 2, 3, 4]  # 1 Tinted, 2 Cut-out, 3 Faded page, 4 Outlined
Status = Literal["pass", "warn", "fail"]


class PageAsset(BaseModel):
    page_number: int  # 1-based, matches pages/{n}.png
    image_path: str  # master
    view_path: str  # working copy
    width: int  # of the master
    height: int
    text: str
    text_source: Literal["layer", "none"]
    flags: list[str] = []  # known so far: "spread", "low_quality"


class Candidate(BaseModel):
    label: str
    synonyms: list[str] = []
    box: tuple[float, float, float, float]  # x0, y0, x1, y1
    confidence: float = Field(ge=0, le=1)
    mask_path: str
    mask_hash: str
    source: Literal["auto", "click", "manual"]


class PageResult(BaseModel):
    state: Literal["ready", "needs_subject", "no_clear_subject", "unsupported", "failed"]
    page_kind: Literal["single", "several", "scene"] | None
    candidates: list[Candidate]
    selected: int | None
    reason: str | None


class Settings(BaseModel):
    colors: list[HexColor] = Field(default=["#E53935"], min_length=1, max_length=3)  # first is the main color
    background: HexColor = "#000000"
    size: Literal["small", "medium", "large"] = "medium"
    position: Literal["center", "left", "right", "upper", "lower"] = "center"
    text_mode: Literal["off", "below"] = "off"
    outline: Literal["off", "thin", "thick"] = "off"


class Profile(BaseModel):
    id: str
    name: str
    level: Level
    settings: Settings
    settings_hash: str
    contrast_override_note: str | None = None


class CheckItem(BaseModel):
    status: Status
    value: float | None
    detail: str


class CheckResult(BaseModel):
    fidelity: CheckItem
    page_edge: CheckItem
    background: CheckItem | None = None  # not checked at level 4
    contrast: CheckItem
    size: CheckItem
    text_contrast: CheckItem | None = None  # only when text is shown


class SecondLook(BaseModel):
    status: Literal["pass", "warn", "pending"]
    answer: str | None = None
    detail: str | None = None
