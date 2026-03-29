#!/usr/bin/env python3
"""
Advanced PDF Analysis - Deep dive into PDF structure
"""

import os
import sys
from pathlib import Path

def try_multiple_pdf_libraries(file_path):
    """Try different PDF libraries to read the file"""
    print("🔍 Testing with different PDF libraries...")
    
    results = {}
    
    # Test 1: PyPDF2
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            info = {
                'pages': len(reader.pages),
                'encrypted': reader.is_encrypted,
                'metadata': dict(reader.metadata) if reader.metadata else {},
                'has_outlines': reader.outline is not None,
                'has_form': '/AcroForm' in reader._objects,
            }
            
            results['PyPDF2'] = {
                'status': 'success',
                'info': info,
                'error': None
            }
            
            print(f"✅ PyPDF2: {info['pages']} pages, encrypted: {info['encrypted']}")
            
            # Try to extract text from first page
            try:
                page = reader.pages[0]
                text = page.extract_text()
                results['PyPDF2']['text_sample'] = text[:200] + "..." if len(text) > 200 else text
                print(f"   📝 Text extraction: {len(text)} characters")
            except Exception as e:
                results['PyPDF2']['text_error'] = str(e)
                print(f"   ❌ Text extraction failed: {e}")
                
    except ImportError:
        results['PyPDF2'] = {'status': 'not_available', 'error': 'PyPDF2 not installed'}
        print("❌ PyPDF2 not available")
    except Exception as e:
        results['PyPDF2'] = {'status': 'error', 'error': str(e)}
        print(f"❌ PyPDF2 error: {e}")
    
    # Test 2: pdfplumber
    try:
        import pdfplumber
        
        with pdfplumber.open(file_path) as pdf:
            info = {
                'pages': len(pdf.pages),
                'metadata': pdf.metadata or {},
            }
            
            results['pdfplumber'] = {
                'status': 'success',
                'info': info,
                'error': None
            }
            
            print(f"✅ pdfplumber: {info['pages']} pages")
            
            # Try to extract text from first page
            try:
                page = pdf.pages[0]
                text = page.extract_text()
                results['pdfplumber']['text_sample'] = text[:200] + "..." if len(text) > 200 else text
                print(f"   📝 Text extraction: {len(text)} characters")
                
                # Try to extract tables
                tables = page.extract_tables()
                if tables:
                    print(f"   📊 Tables found: {len(tables)}")
                    results['pdfplumber']['has_tables'] = True
                
            except Exception as e:
                results['pdfplumber']['text_error'] = str(e)
                print(f"   ❌ Text extraction failed: {e}")
                
    except ImportError:
        results['pdfplumber'] = {'status': 'not_available', 'error': 'pdfplumber not installed'}
        print("❌ pdfplumber not available")
    except Exception as e:
        results['pdfplumber'] = {'status': 'error', 'error': str(e)}
        print(f"❌ pdfplumber error: {e}")
    
    # Test 3: PyMuPDF (fitz)
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(file_path)
        
        info = {
            'pages': doc.page_count,
            'metadata': doc.metadata,
            'is_pdf': True,
            'is_encrypted': doc.is_encrypted,
            'has_annots': len(doc.annots()) > 0,
        }
        
        results['PyMuPDF'] = {
            'status': 'success',
            'info': info,
            'error': None
        }
        
        print(f"✅ PyMuPDF: {info['pages']} pages, encrypted: {info['is_encrypted']}")
        
        # Try to extract text from first page
        try:
            page = doc[0]
            text = page.get_text()
            results['PyMuPDF']['text_sample'] = text[:200] + "..." if len(text) > 200 else text
            print(f"   📝 Text extraction: {len(text)} characters")
            
            # Check for images
            images = page.get_images()
            if images:
                print(f"   🖼️  Images found: {len(images)}")
                results['PyMuPDF']['has_images'] = True
                
        except Exception as e:
            results['PyMuPDF']['text_error'] = str(e)
            print(f"   ❌ Text extraction failed: {e}")
        
        doc.close()
        
    except ImportError:
        results['PyMuPDF'] = {'status': 'not_available', 'error': 'PyMuPDF not installed'}
        print("❌ PyMuPDF not available")
    except Exception as e:
        results['PyMuPDF'] = {'status': 'error', 'error': str(e)}
        print(f"❌ PyMuPDF error: {e}")
    
    return results

def analyze_pdf_structure(file_path):
    """Deep analysis of PDF structure"""
    print("\n🔬 Deep PDF Structure Analysis")
    print("=" * 40)
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Count PDF objects
        obj_count = content.count(b'obj')
        stream_count = content.count(b'stream')
        endobj_count = content.count(b'endobj')
        
        print(f"📊 PDF Objects: {obj_count}")
        print(f"📊 Streams: {stream_count}")
        print(f"📊 End Objects: {endobj_count}")
        
        # Look for potential issues
        issues = []
        
        if b'/Encrypt' in content:
            issues.append("PDF contains encryption")
        
        if b'/Font' in content:
            font_count = content.count(b'/Font')
            print(f"🔤 Fonts found: {font_count}")
        
        if b'/Image' in content or b'/XObject' in content:
            issues.append("PDF contains images")
        
        if b'/AcroForm' in content:
            issues.append("PDF contains forms")
        
        if b'/Annot' in content:
            issues.append("PDF contains annotations")
        
        if issues:
            print("⚠️  Special features detected:")
            for issue in issues:
                print(f"   • {issue}")
        
        # Check file structure integrity
        if obj_count != endobj_count:
            print("❌ Object count mismatch - possible corruption")
        else:
            print("✅ Object structure appears intact")
            
    except Exception as e:
        print(f"❌ Structure analysis failed: {e}")

def suggest_solutions(results):
    """Suggest solutions based on analysis results"""
    print("\n💡 Suggested Solutions:")
    print("=" * 30)
    
    working_libs = [name for name, result in results.items() if result.get('status') == 'success']
    
    if working_libs:
        print(f"✅ Working libraries: {', '.join(working_libs)}")
        
        if 'PyMuPDF' in working_libs:
            print("💡 Recommendation: Use PyMuPDF (fitz) - it's the most robust")
            print("   Install: pip install PyMuPDF")
        
        elif 'pdfplumber' in working_libs:
            print("💡 Recommendation: Use pdfplumber - good for text extraction")
            print("   Install: pip install pdfplumber")
        
        elif 'PyPDF2' in working_libs:
            print("💡 Recommendation: Use PyPDF2 - basic PDF functionality")
            print("   Install: pip install PyPDF2")
    else:
        print("❌ No PDF libraries working - installation issues")
        print("💡 Try installing:")
        print("   pip install PyMuPDF pdfplumber PyPDF2")
    
    # Check for encryption
    encryption_detected = False
    for name, result in results.items():
        if result.get('info', {}).get('encrypted', False):
            encryption_detected = True
            break
    
    if encryption_detected:
        print("\n🔒 Encryption detected:")
        print("   • The PDF may be password protected")
        print("   • Try opening in Adobe Acrobat to check for password")
        print("   • Use pdfplumber or PyMuPDF which handle encryption better")

def main():
    """Main analysis function"""
    target_file = Path("uploads/20260317_202821_tmppp8sfhdr.pdf")
    
    if not target_file.exists():
        print(f"❌ File not found: {target_file}")
        return
    
    print("🔬 Advanced PDF Analysis")
    print("=" * 40)
    print(f"📁 Target: {target_file}")
    print(f"📊 Size: {target_file.stat().st_size:,} bytes")
    
    # Test with different libraries
    results = try_multiple_pdf_libraries(target_file)
    
    # Deep structure analysis
    analyze_pdf_structure(target_file)
    
    # Suggest solutions
    suggest_solutions(results)
    
    # Show text samples if available
    print("\n📝 Text Samples:")
    print("=" * 20)
    
    for lib_name, result in results.items():
        if result.get('status') == 'success' and 'text_sample' in result:
            print(f"\n{lib_name}:")
            text = result['text_sample']
            if text.strip():
                print(f"   {text[:100]}...")
            else:
                print("   (No text extracted)")
        elif result.get('text_error'):
            print(f"\n{lib_name}: ❌ {result['text_error']}")

if __name__ == "__main__":
    main()
