"""Schemas for backend vision endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

VisionTask = Literal["lifestyle", "receipt", "ocr", "catalog_tag", "visual_search"]
VisionJobStatus = Literal["queued", "processing", "completed", "failed"]


class VisionAnalyzeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    task: VisionTask
    image_url: str | None = None
    image_base64: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    async_mode: bool = Field(default=True)


class VisionJobData(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    task: VisionTask
    status: VisionJobStatus
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime | None = None


class VisionAnalyzeResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    job: VisionJobData
    source: str

