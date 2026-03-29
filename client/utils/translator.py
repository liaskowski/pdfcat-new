import json
import os
from pathlib import Path
from .config_manager import ConfigManager

class Translator:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translator, cls).__new__(cls)
            cls._instance._load_translations()
        return cls._instance

    def _load_translations(self):
        self.config = ConfigManager()
        lang_code = self.config.get("language", "en")
        
        # Determine path to assets/lang using absolute directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # client/utils -> client/assets/lang
        base_path = os.path.abspath(os.path.join(current_dir, "..", "assets", "lang"))
        file_path = os.path.join(base_path, f"{lang_code}.json")
        
        print(f"DEBUG: Translator absolute path: {file_path}")
        
        self.translations = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                print(f"DEBUG: Successfully loaded {len(self.translations)} top-level categories for {lang_code}")
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to load translations for {lang_code}: {e}")
        else:
            print(f"CRITICAL ERROR: Translation file NOT FOUND at: {file_path}")

    def tr(self, key: str) -> str:
        """Supports nested keys via dot notation, e.g., 'common.save'."""
        if not key:
            return ""
            
        parts = key.split(".")
        val = self.translations
        
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                if key != "": # Avoid spamming empty keys
                    print(f"DEBUG: Missing translation for: {key}")
                return key
        
        return str(val)

    def get_locale(self) -> str:
        return self.config.get("language", "en")

    def reload(self):
        self._load_translations()