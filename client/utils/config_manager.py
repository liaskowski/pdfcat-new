import json
import os
import sys
from typing import Any, Dict
from PyQt6.QtCore import QStandardPaths

def safe_serialize(obj):
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except:
            return str(obj)
    if isinstance(obj, dict):
        return {str(k): safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [safe_serialize(i) for i in obj]
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return str(obj)

class ConfigManager:
    _instance = None
    
    DEFAULT_CONFIG = {
        "theme": "Dark",     # Light, Dark, System
        "scale": 100,        # 100, 125, 150
        "font_size": 10,     # 10, 12, 14
        "language": "en"     # en, ru, pl
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            # Initialize path
            app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
            if not os.path.exists(app_data):
                os.makedirs(app_data, exist_ok=True)
            cls._instance.CONFIG_FILE = os.path.join(app_data, "client_config.json")
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            # Try to migrate from old location if exists (root of project)
            old_config = "client_config.json"
            if os.path.exists(old_config):
                try:
                    with open(old_config, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                    self._save_config()
                    # Optional: remove old config? User might want to keep it for portability.
                    # For now, just keep it but use the new one.
                except:
                    self.config = self.DEFAULT_CONFIG.copy()
            else:
                self.config = self.DEFAULT_CONFIG.copy()
                self._save_config()
        else:
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                # Ensure all keys exist
                for k, v in self.DEFAULT_CONFIG.items():
                    if k not in self.config:
                        self.config[k] = v
            except Exception:
                self.config = self.DEFAULT_CONFIG.copy()

    def save(self):
        """Public method to force saving configuration to disk."""
        self._save_config()

    def _save_config(self):
        try:
            # Recursive deep cleanup
            clean_config = safe_serialize(self.config)
            
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(clean_config, f, indent=4, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
        except Exception as e:
            sys.stderr.write(f"CRITICAL ERROR: Failed to save config: {e}\n")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default if default is not None else self.DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any):
        self.config[key] = value
        self._save_config()

    def get_all(self) -> Dict[str, Any]:
        return self.config.copy()