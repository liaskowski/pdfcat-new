#!/usr/bin/env python3
"""
Simple PDF decrypt tool - try to read encrypted PDF
"""

import os
from pathlib import Path

def try_decrypt_pdf(file_path):
    """Try to decrypt PDF with common passwords"""
    try:
        import PyPDF2
        
        # Common passwords to try
        passwords = [
            "",  # No password
            "password", "admin", "123456", "qwerty", "test",
            "pdf", "document", "file", "1234", "abc123"
        ]
        
        print(f"🔍 Trying to decrypt: {file_path}")
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            if reader.is_encrypted:
                print("🔒 PDF is encrypted - trying passwords...")
                
                for password in passwords:
                    try:
                        if reader.decrypt(password):
                            print(f"✅ SUCCESS! Password: '{password}'")
                            
                            # Extract text from first page
                            page = reader.pages[0]
                            text = page.extract_text()
                            
                            if text.strip():
                                print(f"📝 Text sample: {text[:200]}...")
                                return True, password, text[:500]
                            else:
                                print("⚠️  Password worked but no text extracted")
                                return True, password, "No text extracted"
                        else:
                            print(f"❌ Password '{password}' failed")
                    except Exception as e:
                        print(f"❌ Error with password '{password}': {e}")
                        continue
                
                print("❌ All passwords failed")
                return False, None, None
            else:
                print("✅ PDF is not encrypted")
                
                # Try to extract text
                try:
                    page = reader.pages[0]
                    text = page.extract_text()
                    
                    if text.strip():
                        print(f"📝 Text sample: {text[:200]}...")
                        return True, None, text[:500]
                    else:
                        print("⚠️  No text extracted from first page")
                        return True, None, "No text extracted"
                except Exception as e:
                    print(f"❌ Text extraction failed: {e}")
                    return False, None, None
                    
    except ImportError:
        print("❌ PyPDF2 not available")
        return False, None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None, None

def try_pymupdf(file_path):
    """Try with PyMuPDF (more robust)"""
    try:
        import fitz  # PyMuPDF
        
        print(f"🔍 Trying PyMuPDF on: {file_path}")
        
        doc = fitz.open(file_path)
        
        if doc.is_encrypted:
            print("🔒 PDF is encrypted - PyMuPDF can handle it")
            
            # Try to authenticate without password
            try:
                auth = doc.authenticate("")
                if auth:
                    print("✅ SUCCESS! No password needed")
                else:
                    print("⚠️  Password required")
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False, None, None
        else:
            print("✅ PDF is not encrypted")
        
        # Extract text from first page
        try:
            page = doc[0]
            text = page.get_text()
            
            if text.strip():
                print(f"📝 Text sample: {text[:200]}...")
                
                # Check for images
                images = page.get_images()
                if images:
                    print(f"🖼️  Images found: {len(images)}")
                
                return True, None, text[:500]
            else:
                print("⚠️  No text extracted from first page")
                return True, None, "No text extracted"
                
        except Exception as e:
            print(f"❌ Text extraction failed: {e}")
            return False, None, None
        finally:
            doc.close()
            
    except ImportError:
        print("❌ PyMuPDF not available")
        return False, None, None
    except Exception as e:
        print(f"❌ PyMuPDF error: {e}")
        return False, None, None

def main():
    """Main function"""
    target_file = Path("uploads/20260317_202821_tmppp8sfhdr.pdf")
    
    if not target_file.exists():
        print(f"❌ File not found: {target_file}")
        return
    
    print("🔐 PDF Decryption Tool")
    print("=" * 30)
    print(f"📁 Target: {target_file}")
    print(f"📊 Size: {target_file.stat().st_size:,} bytes")
    
    # Try PyMuPDF first (more robust)
    print("\n🔬 Trying PyMuPDF...")
    success, password, text = try_pymupdf(target_file)
    
    if success:
        print("\n✅ PyMuPDF SUCCESS!")
        if password:
            print(f"🔑 Password: {password}")
        print(f"📝 Text extracted: {len(text) if text else 0} characters")
        
        # Save extracted text
        if text and text.strip():
            output_file = target_file.with_name(f"{target_file.stem}_extracted.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"💾 Text saved to: {output_file}")
        return
    
    # Try PyPDF2 as fallback
    print("\n🔬 Trying PyPDF2...")
    success, password, text = try_decrypt_pdf(target_file)
    
    if success:
        print("\n✅ PyPDF2 SUCCESS!")
        if password:
            print(f"🔑 Password: {password}")
        print(f"📝 Text extracted: {len(text) if text else 0} characters")
        
        # Save extracted text
        if text and text.strip():
            output_file = target_file.with_name(f"{target_file.stem}_extracted.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"💾 Text saved to: {output_file}")
    else:
        print("\n❌ Both methods failed")
        print("💡 Suggestions:")
        print("   1. The PDF may be password protected with unknown password")
        print("   2. The PDF may be corrupted")
        print("   3. Try opening in Adobe Acrobat")
        print("   4. Use online PDF repair tools")

if __name__ == "__main__":
    main()
