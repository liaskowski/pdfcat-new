import os
import pytesseract
from pathlib import Path

def setup_tesseract():
    """
    Configures pytesseract to use the bundled Tesseract executable.
    In this portable environment, it's located in server/bin/tesseract.
    """
    # Base directory is the project root (where .env, main.py are)
    # This file is in client/utils/
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    tesseract_dir = base_dir / 'server' / 'bin' / 'tesseract'
    executable_path = tesseract_dir / 'tesseract.exe'
    
    # Check if the local executable exists
    if executable_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(executable_path)
        # Also set TESSDATA_PREFIX for completeness
        os.environ["TESSDATA_PREFIX"] = str(tesseract_dir / 'tessdata')
    else:
        # Fallback or warning
        print(f"Warning: Bundled Tesseract not found at {executable_path}. Using system default.")
    
    # Return the tessdata path
    return str(tesseract_dir / 'tessdata')

def get_tesseract_config():
    """
    Returns the config string for pytesseract including tessdata-dir.
    """
    tessdata_path = setup_tesseract()
    return f'--tessdata-dir "{tessdata_path}"'
