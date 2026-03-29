from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List, Optional

class TagAnalysisWorker(QThread):
    finished = pyqtSignal(list) # list of tags
    error = pyqtSignal(str)

    def __init__(self, tag_analyzer, api_manager, file_path: str, locale: str = "en"):
        super().__init__()
        self.tag_analyzer = tag_analyzer
        self.api_manager = api_manager
        self.file_path = file_path
        self.locale = locale

    def run(self):
        if not self.file_path:
            self.finished.emit([])
            return

        try:
            # 1. OCR/Text analysis with correct locale
            tags = self.tag_analyzer.analyze_file(self.file_path, locale=self.locale)

            # 2. Similarity analysis (requires network call)
            try:
                recent_docs = self.api_manager.list_documents(limit=50)
                similar_tags = self.tag_analyzer.suggest_tags_by_similarity(
                    Path(self.file_path).name,
                    recent_docs
                )
                if similar_tags:
                    # Tags from similarity should also respect locale
                    tags.extend(similar_tags)
            except Exception as e:
                print(f"Similarity analysis failed (non-critical): {e}")

            # Deduplicate and sort
            unique_tags = sorted(list(set(t.strip() for t in tags if t)))
            self.finished.emit(unique_tags)

        except Exception as e:
            self.error.emit(str(e))
