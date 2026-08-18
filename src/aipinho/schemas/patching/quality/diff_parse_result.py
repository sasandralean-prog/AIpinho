from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class ParsedDiffHunk(AIpinhoModel):
    file_path: str
    header: str
    old_start: int = 0
    old_count: int = 0
    new_start: int = 0
    new_count: int = 0
    added_lines: list[str] = Field(default_factory=list)
    removed_lines: list[str] = Field(default_factory=list)
    context_lines: list[str] = Field(default_factory=list)


class DiffParseResult(AIpinhoModel):
    status: str = "unknown"
    valid: bool = False
    affected_files: list[str] = Field(default_factory=list)
    hunks: list[ParsedDiffHunk] = Field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    binary_detected: bool = False
    rename_detected: bool = False
    delete_detected: bool = False
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
