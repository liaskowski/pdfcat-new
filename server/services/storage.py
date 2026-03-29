from abc import ABC, abstractmethod
import os
import shutil
import hashlib
from typing import BinaryIO, Optional
from pathlib import Path
from ..config import settings

class IStorageProvider(ABC):
    @abstractmethod
    def save(self, file_obj: BinaryIO, filename: str) -> str:
        """Save file and return the stored path/identifier"""
        pass

    @abstractmethod
    def get(self, file_path: str) -> BinaryIO:
        """Get file stream"""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete file"""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass

    @abstractmethod
    def copy(self, source_path: str, dest_filename: str) -> str:
        """Copy file and return new path"""
        pass

class LocalStorageProvider(IStorageProvider):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, filename: str) -> Path:
        """
        Flat storage structure: uploads/filename.pdf
        """
        return self.base_path / filename

    def save(self, file_obj: BinaryIO, filename: str) -> str:
        target_path = self._get_file_path(filename)

        with target_path.open("wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        return str(target_path)

    def get(self, file_path: str) -> BinaryIO:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
        return open(file_path, "rb")

    def delete(self, file_path: str) -> bool:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)

    def copy(self, source_path: str, dest_filename: str) -> str:
        target_path = self._get_file_path(dest_filename)
        if not os.path.exists(source_path):
             raise FileNotFoundError(f"Source file {source_path} missing")

        shutil.copy2(source_path, target_path)
        return str(target_path)

# Singleton instance
storage = LocalStorageProvider(settings.UPLOAD_DIR)
