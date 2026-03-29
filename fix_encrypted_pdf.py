#!/usr/bin/env python3
"""
PDF Repair Tool - Fix encrypted or corrupted PDF files
"""

import os
import sys
from pathlib import Path
import hashlib
import shutil
from datetime import datetime

def analyze_pdf_file(file_path):
    """Analyze PDF file structure and detect issues"""
    print(f"🔍 Analyzing PDF: {file_path}")
    print("=" * 50)
    
    file_size = os.path.getsize(file_path)
    print(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # Read first few bytes to check PDF header
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
            print(f"📄 File header: {header}")
            
            # Check PDF signature
            if header.startswith(b'%PDF'):
                print("✅ Valid PDF signature found")
                
                # Try to read PDF version
                if b'-' in header:
                    version = header.split(b'-')[1].split(b'\n')[0].decode('utf-8', errors='ignore')
                    print(f"📖 PDF version: {version}")
                
                # Check for encryption
                f.seek(0)
                content = f.read(1024)  # Read first KB
                if b'/Encrypt' in content:
                    print("🔒 PDF appears to be encrypted")
                    return "encrypted"
                elif b'/ObjStm' in content:
                    print("🔄 PDF has object streams")
                else:
                    print("📝 Standard PDF structure")
                    
            else:
                print("❌ Invalid PDF signature")
                return "invalid_signature"
                
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return "read_error"
    
    return "valid"

def try_pdf_repair_methods(file_path):
    """Try different PDF repair methods"""
    print(f"\n🔧 Attempting PDF repair...")
    
    repaired_files = []
    
    # Method 1: Try to create a new PDF with header fix
    try:
        repaired_path = file_path.with_name(f"{file_path.stem}_repaired.pdf")
        
        with open(file_path, 'rb') as original:
            data = original.read()
        
        # Check if PDF header is missing or corrupted
        if not data.startswith(b'%PDF'):
            print("🔧 Fixing missing PDF header...")
            
            # Add PDF header
            if data.startswith(b'\x25\x50\x44\x46'):  # PDF bytes but no header
                fixed_data = b'%PDF-1.4\n' + data
            else:
                # Try to find PDF content and add header
                pdf_start = data.find(b'%PDF')
                if pdf_start != -1:
                    fixed_data = data[pdf_start:]
                else:
                    print("❌ Cannot find PDF content")
                    return repaired_files
            
            with open(repaired_path, 'wb') as repaired:
                repaired.write(fixed_data)
            
            repaired_files.append(repaired_path)
            print(f"✅ Created repaired file: {repaired_path}")
            
    except Exception as e:
        print(f"❌ Header repair failed: {e}")
    
    # Method 2: Try PyPDF2 repair if available
    try:
        import PyPDF2
        
        try:
            repaired_path = file_path.with_name(f"{file_path.stem}_pypdf2_repaired.pdf")
            
            with open(file_path, 'rb') as original:
                reader = PyPDF2.PdfReader(original)
                
                # Create new PDF
                writer = PyPDF2.PdfWriter()
                
                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)
                
                # Write repaired PDF
                with open(repaired_path, 'wb') as repaired:
                    writer.write(repaired)
            
            repaired_files.append(repaired_path)
            print(f"✅ PyPDF2 repaired file: {repaired_path}")
            
        except Exception as e:
            print(f"⚠️  PyPDF2 repair failed: {e}")
            
    except ImportError:
        print("⚠️  PyPDF2 not available for repair")
    
    # Method 3: Try pdfplumber for text extraction
    try:
        import pdfplumber
        
        try:
            repaired_path = file_path.with_name(f"{file_path.stem}_text_extracted.txt")
            
            with pdfplumber.open(file_path) as pdf:
                text_content = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                
                if text_content:
                    with open(repaired_path, 'w', encoding='utf-8') as text_file:
                        text_file.write('\n\n--- Page Separator ---\n\n'.join(text_content))
                    
                    repaired_files.append(repaired_path)
                    print(f"✅ Text extracted to: {repaired_path}")
                else:
                    print("⚠️  No text content extracted")
                    
        except Exception as e:
            print(f"⚠️  pdfplumber extraction failed: {e}")
            
    except ImportError:
        print("⚠️  pdfplumber not available for text extraction")
    
    return repaired_files

def check_file_permissions(file_path):
    """Check and try to fix file permissions"""
    try:
        # Check if file is readable
        with open(file_path, 'rb') as f:
            f.read(10)  # Try to read first 10 bytes
        
        print("✅ File is readable")
        return True
        
    except PermissionError:
        print("❌ Permission denied - trying to fix...")
        try:
            # Try to make file readable
            os.chmod(file_path, 0o644)
            print("✅ Fixed file permissions")
            return True
        except Exception as e:
            print(f"❌ Cannot fix permissions: {e}")
            return False
    except Exception as e:
        print(f"❌ File access error: {e}")
        return False

def create_backup(file_path):
    """Create backup of original file"""
    try:
        backup_path = file_path.with_name(f"{file_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return None

def main():
    """Main PDF repair function"""
    # Find the specific file
    uploads_dir = Path("uploads")
    target_file = uploads_dir / "20260317_202821_tmppp8sfhdr.pdf"
    
    if not target_file.exists():
        print(f"❌ File not found: {target_file}")
        print("Please check the file path and try again.")
        return
    
    print("🔧 PDF Repair Tool")
    print("=" * 40)
    print(f"📁 Target file: {target_file}")
    
    # Create backup
    print("\n📦 Creating backup...")
    backup_path = create_backup(target_file)
    
    # Check file permissions
    print("\n🔐 Checking file permissions...")
    if not check_file_permissions(target_file):
        print("❌ Cannot access file - please check file permissions")
        return
    
    # Analyze file
    print("\n📊 Analyzing file structure...")
    analysis_result = analyze_pdf_file(target_file)
    
    # Try repair methods
    if analysis_result in ["encrypted", "invalid_signature", "read_error"]:
        print(f"\n🔧 File issue detected: {analysis_result}")
        repaired_files = try_pdf_repair_methods(target_file)
        
        if repaired_files:
            print(f"\n✅ Successfully created {len(repaired_files)} repaired files:")
            for repaired in repaired_files:
                print(f"   📄 {repaired}")
        else:
            print(f"\n❌ Could not repair the file automatically")
            print("💡 Suggestions:")
            print("   1. Try opening the file in Adobe Acrobat and use 'Save As'")
            print("   2. Use an online PDF repair tool")
            print("   3. Check if the file is password protected")
    else:
        print(f"\n✅ File appears to be valid ({analysis_result})")
        print("💡 If you're still having issues, try:")
        print("   1. Opening in a different PDF viewer")
        print("   2. Checking if the file is password protected")
        print("   3. Using Adobe Acrobat's repair function")
    
    print(f"\n📋 Summary:")
    print(f"   Original file: {target_file}")
    if backup_path:
        print(f"   Backup file: {backup_path}")
    print(f"   File size: {target_file.stat().st_size:,} bytes")
    print(f"   Analysis result: {analysis_result}")

if __name__ == "__main__":
    main()
