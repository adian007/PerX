"""Request/response schemas for cv-service analyze API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

VisionTask = Literal["lifestyle", "receipt", "ocr", "catalog_tag", "visual_search"]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    task: VisionTask
    image_url: str | None = None
    image_base64: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("image_base64")
    @classmethod
    def _strip_b64(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    task: VisionTask
    result: dict[str, Any]
    meta: dict[str, Any]

