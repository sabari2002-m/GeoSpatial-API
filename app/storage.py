from dataclasses import dataclass
from threading import Lock

from .models import FileDetail


@dataclass(frozen=True)
class StoredFile:
    detail: FileDetail


class FileStore:
    def __init__(self) -> None:
        self._files: dict[str, StoredFile] = {}
        self._lock = Lock()

    def save(self, detail: FileDetail) -> None:
        with self._lock:
            self._files[detail.id] = StoredFile(detail=detail)

    def get(self, file_id: str) -> StoredFile | None:
        with self._lock:
            return self._files.get(file_id)


store = FileStore()
