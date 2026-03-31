import unittest
import os
import json
from client.utils.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.config_file = "test_client_config.json"
        # Monkey patch the file path
        ConfigManager.CONFIG_FILE = self.config_file
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        # Clear singleton instance for each test
        ConfigManager._instance = None

    def tearDown(self):
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

    def test_default_config(self):
        cm = ConfigManager()
        self.assertEqual(cm.get("theme"), "Dark")
        self.assertEqual(cm.get("scale"), 100)
        self.assertEqual(cm.get("font_size"), 10)

    def test_save_and_load(self):
        cm = ConfigManager()
        cm.set("scale", 150)
        cm.set("theme", "Light")
        
        # New instance should load from file
        ConfigManager._instance = None
        cm2 = ConfigManager()
        self.assertEqual(cm2.get("scale"), 150)
        self.assertEqual(cm2.get("theme"), "Light")

    def test_missing_keys_fill_with_defaults(self):
        with open(self.config_file, "w") as f:
            json.dump({"theme": "Light"}, f)
        
        cm = ConfigManager()
        self.assertEqual(cm.get("theme"), "Light")
        self.assertEqual(cm.get("scale"), 100) # Default value

if __name__ == "__main__":
    unittest.main()
