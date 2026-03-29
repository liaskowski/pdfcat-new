import json
import os

def check_i18n():
    lang_dir = "client/assets/lang"
    files = ["en.json", "ru.json", "pl.json"]
    
    data = {}
    for f in files:
        with open(os.path.join(lang_dir, f), "r", encoding="utf-8") as j:
            data[f] = json.load(j)
            
    en_keys = set()
    def get_keys(d, prefix=""):
        keys = set()
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(get_keys(v, full_key))
            else:
                keys.add(full_key)
        return keys

    all_en_keys = get_keys(data["en.json"])
    
    for f in ["ru.json", "pl.json"]:
        f_keys = get_keys(data[f])
        missing = all_en_keys - f_keys
        extra = f_keys - all_en_keys
        
        print(f"--- {f} ---")
        if missing:
            print(f"Missing keys ({len(missing)}):")
            for m in sorted(list(missing)):
                print(f"  - {m}")
        else:
            print("No missing keys.")
            
        if extra:
            print(f"Extra keys ({len(extra)}):")
            for e in sorted(list(extra)):
                print(f"  - {e}")
        print()

if __name__ == "__main__":
    check_i18n()
