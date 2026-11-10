"""Bounded, validated video uploads to avoid uncontrolled memory use."""
import os
import uuid
from pathlib import Path
from fastapi import UploadFile


class FileManager:
    ALLOWED_CONTENT_TYPES = {
        ".mp4": {"video/mp4"},
        ".webm": {"video/webm"},
        ".mov": {"video/quicktime"},
    }

    @staticmethod
    def _max_bytes() -> int:
        try:
            max_mb = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
        except ValueError as exc:
            raise ValueError("MAX_VIDEO_SIZE_MB must be an integer") from exc
        if max_mb <= 0:
            raise ValueError("MAX_VIDEO_SIZE_MB must be positive")
        return max_mb * 1024 * 1024

    @staticmethod
    async def validate_video_file(file: UploadFile):
        extension = Path(file.filename or "").suffix.lower()
        content_type = (file.content_type or "").split(";", 1)[0].lower().strip()
        if content_type not in FileManager.ALLOWED_CONTENT_TYPES.get(extension, set()):
            raise ValueError("Unsupported video format. Use MP4, WebM, or MOV.")
        if file.size is not None and file.size > FileManager._max_bytes():
            raise ValueError("Video exceeds configured upload size limit")
        return True

    @staticmethod
    async def read_video_file(file: UploadFile) -> bytes:
        await FileManager.validate_video_file(file)
        limit = FileManager._max_bytes()
        data = bytearray()
        while True:
            chunk = await file.read(min(1024 * 1024, limit - len(data) + 1))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError("Video exceeds configured upload size limit")
        if not data:
            raise ValueError("Video cannot be empty")
        return bytes(data)

    @staticmethod
    def generate_filename(original_filename: str) -> str:
        extension = Path(original_filename or "").suffix.lower()
        if extension not in FileManager.ALLOWED_CONTENT_TYPES:
            raise ValueError("Unsupported video file extension")
        return f"{uuid.uuid4()}{extension}"
