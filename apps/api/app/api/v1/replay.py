"""Public, read-only playback of validated recording snapshots; never calls DB or LLM."""

import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import ValidationError

from app.api.v1.schemas import Recording, RecordingList, RecordingListItem
from app.core.config import get_settings
from app.core.errors import ApiError

router = APIRouter(prefix="/v1/replay/recordings", tags=["Replay"])
log = logging.getLogger("app.replay")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_BYTES = 2_000_000


def _enabled_folder() -> Path:
    settings = get_settings()
    if not settings.enable_replay:
        raise ApiError("NOT_FOUND", "replay is disabled")
    return settings.recordings_dir.resolve()


def _read(folder: Path, recording_id: str) -> Recording | None:
    if not _SAFE_ID.fullmatch(recording_id):
        return None
    file = folder / f"{recording_id}.json"
    if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(folder):
        return None
    try:
        if file.stat().st_size > _MAX_BYTES:
            return None
        recording = Recording.model_validate(json.loads(file.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError, ValidationError):
        log.warning("invalid replay snapshot: %s", recording_id)
        return None
    if (
        recording.recording_id != recording_id
        or recording.case.case_id != recording.case_id
        or recording.report.case.case_id != recording.case_id
        or recording.report.variant != recording.variant
        or recording.report.case.status != recording.case.status
        or recording.steps_count is not None
        and recording.steps_count != len(recording.steps)
    ):
        return None
    return recording


@router.get(
    "",
    response_model=RecordingList,
    response_model_exclude_none=True,
    operation_id="listRecordings",
)
def list_recordings() -> RecordingList:
    folder = _enabled_folder()
    if not folder.is_dir():
        return RecordingList(items=[])
    items: list[RecordingListItem] = []
    for file in sorted(folder.glob("*.json")):
        found = _read(folder, file.stem)
        if found is not None:
            items.append(
                RecordingListItem.model_validate(
                    {
                        **found.model_dump(),
                        "status": found.case.status,
                        "status_label_th": found.case.status_label_th,
                    }
                )
            )
    return RecordingList(items=items)


@router.get(
    "/{recording_id}",
    response_model=Recording,
    response_model_exclude_none=True,
    operation_id="getRecording",
)
def get_recording(recording_id: str) -> Recording:
    found = _read(_enabled_folder(), recording_id)
    if found is None:
        raise ApiError("NOT_FOUND", "recording not found")
    return found
