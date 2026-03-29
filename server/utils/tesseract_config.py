import os
import pytesseract

def setup_tesseract():
    """
    Configures pytesseract to use the bundled Tesseract executable in the server directory.
    Returns the path to the tessdata directory.
    """
    # Calculate the base directory relative to this file
    # This file is in server/utils/
    # We want to reach server/bin/tesseract/tesseract.exe
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to 'server'
    server_dir = os.path.dirname(current_dir)
    
    tesseract_dir = os.path.join(server_dir, 'bin', 'tesseract')
    executable_path = os.path.join(tesseract_dir, 'tesseract.exe')
    
    # Check if the local executable exists
    if os.path.exists(executable_path):
        pytesseract.pytesseract.tesseract_cmd = executable_path
    else:
        # Fallback or warning
        print(f"Warning: Bundled Tesseract not found at {executable_path}. Using system default.")
    
    # Return the tessdata path
    tessdata_path = os.path.join(tesseract_dir, 'tessdata')
    return tessdata_path

def get_tesseract_config():
    """
    Returns the config string for pytesseract including tessdata-dir.
    """
    tessdata_path = setup_tesseract()
    return f'--tessdata-dir "{tessdata_path}"'
