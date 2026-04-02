from typing import Any
import requests
from pathlib import Path
from .base import APIBase, APIError

class OCRAPI(APIBase):
    def recognize_document(self, file_path: str, lang: str = "rus+eng") -> str:
        """
        Sends a file to the server for OCR and returns the recognized text.
        """
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = f"{self.base_url}/ocr/recognize"
        
        with open(file_path, "rb") as f:
            filename = Path(file_path).name
            resp = self._session.post(
                url,
                files={"file": (filename, f, "application/octet-stream")},
                data={"lang": lang},
                timeout=120, # Long timeout for OCR
            )

        if resp.status_code != 200:
            raise APIError(resp.status_code, "OCR failed", resp.text)

        data = resp.json()
        return data.get("text", "")
