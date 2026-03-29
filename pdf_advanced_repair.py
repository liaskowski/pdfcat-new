#!/usr/bin/env python3
"""
Advanced PDF repair - try to extract partial content
"""

import os
import re
from pathlib import Path

def extract_partial_content(file_path):
    """Try to extract partial content from corrupted/encrypted PDF"""
    print("🔧 Attempting partial content extraction...")
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Look for text strings in the PDF
        text_patterns = [
            rb'BT\s*(.*?)\s*ET',  # Text blocks
            rb'\((.*?)\)',        # Text in parentheses
            rb'\[(.*?)\]',        # Text in brackets
        ]
        
        extracted_texts = []
        
        for pattern in text_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    # Try to decode as text
                    text = match.decode('utf-8', errors='ignore')
                    if len(text) > 10 and text.strip():  # Filter out short/empty strings
                        extracted_texts.append(text)
                except:
                    continue
        
        if extracted_texts:
            print(f"✅ Found {len(extracted_texts)} text fragments")
            
            # Save extracted text
            output_file = file_path.with_name(f"{file_path.stem}_partial_extract.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n\n--- Text Fragment ---\n\n".join(extracted_texts[:50]))  # Limit to first 50
            
            print(f"💾 Partial text saved to: {output_file}")
            print(f"📝 Sample: {extracted_texts[0][:200]}...")
            return True
        else:
            print("❌ No text fragments found")
            return False
            
    except Exception as e:
        print(f"❌ Partial extraction failed: {e}")
        return False

def try_pdf_structure_repair(file_path):
    """Try to repair PDF structure"""
    print("🔧 Attempting PDF structure repair...")
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Check for common PDF structure issues
        issues_found = []
        
        # Check for missing xref table
        if b'startxref' not in content:
            issues_found.append("Missing xref table")
        
        # Check for incomplete objects
        obj_count = content.count(b'obj')
        endobj_count = content.count(b'endobj')
        if obj_count != endobj_count:
            issues_found.append(f"Object mismatch: {obj_count} obj vs {endobj_count} endobj")
        
        # Check for trailer
        if b'trailer' not in content:
            issues_found.append("Missing trailer")
        
        if issues_found:
            print("🔍 PDF Structure Issues:")
            for issue in issues_found:
                print(f"   • {issue}")
            
            # Try basic repair
            try:
                # Create a repaired version
                repaired_content = content
                
                # Add missing trailer if needed
                if b'trailer' not in repaired_content:
                    trailer = b'\ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n0\n%%EOF\n'
                    repaired_content += trailer
                
                # Save repaired version
                repaired_file = file_path.with_name(f"{file_path.stem}_repaired.pdf")
                with open(repaired_file, 'wb') as f:
                    f.write(repaired_content)
                
                print(f"✅ Basic repair attempted: {repaired_file}")
                return True
                
            except Exception as e:
                print(f"❌ Repair failed: {e}")
                return False
        else:
            print("✅ PDF structure appears intact")
            return True
            
    except Exception as e:
        print(f"❌ Structure analysis failed: {e}")
        return False

def create_summary_report(file_path):
    """Create a summary report of the PDF issues"""
    print("📋 Creating summary report...")
    
    try:
        file_size = file_path.stat().st_size
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        report = []
        report.append("PDF Analysis Report")
        report.append("=" * 40)
        report.append(f"File: {file_path.name}")
        report.append(f"Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        report.append("")
        
        # Header analysis
        header = content[:16]
        report.append("File Header:")
        report.append(f"  Raw: {header}")
        if header.startswith(b'%PDF'):
            report.append("  ✅ Valid PDF signature")
            if b'-' in header:
                version = header.split(b'-')[1].split(b'\n')[0].decode('utf-8', errors='ignore')
                report.append(f"  📖 Version: {version}")
        else:
            report.append("  ❌ Invalid PDF signature")
        
        report.append("")
        
        # Structure analysis
        obj_count = content.count(b'obj')
        endobj_count = content.count(b'endobj')
        stream_count = content.count(b'stream')
        
        report.append("Structure Analysis:")
        report.append(f"  📊 Objects: {obj_count}")
        report.append(f"  📊 End Objects: {endobj_count}")
        report.append(f"  📊 Streams: {stream_count}")
        
        if obj_count != endobj_count:
            report.append("  ❌ Object count mismatch - possible corruption")
        
        # Encryption check
        if b'/Encrypt' in content:
            report.append("  🔒 Encryption detected")
        else:
            report.append("  🔓 No encryption detected")
        
        # Features
        features = []
        if b'/Font' in content:
            features.append("Fonts")
        if b'/Image' in content or b'/XObject' in content:
            features.append("Images")
        if b'/AcroForm' in content:
            features.append("Forms")
        if b'/Annot' in content:
            features.append("Annotations")
        
        if features:
            report.append("  🎯 Features: " + ", ".join(features))
        
        report.append("")
        report.append("Recommendations:")
        report.append("  1. PDF is encrypted - requires password")
        report.append("  2. Structure may be corrupted")
        report.append("  3. Try Adobe Acrobat for password recovery")
        report.append("  4. Use online PDF repair tools")
        report.append("  5. Consider professional PDF recovery services")
        
        # Save report
        report_file = file_path.with_name(f"{file_path.stem}_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"📋 Report saved to: {report_file}")
        print('\n'.join(report))
        return True
        
    except Exception as e:
        print(f"❌ Report creation failed: {e}")
        return False

def main():
    """Main function"""
    target_file = Path("uploads/20260317_202821_tmppp8sfhdr.pdf")
    
    if not target_file.exists():
        print(f"❌ File not found: {target_file}")
        return
    
    print("🔧 Advanced PDF Repair Tool")
    print("=" * 40)
    print(f"📁 Target: {target_file}")
    
    # Create summary report
    create_summary_report(target_file)
    
    print("\n" + "=" * 40)
    
    # Try structure repair
    try_pdf_structure_repair(target_file)
    
    print("\n" + "=" * 40)
    
    # Try partial content extraction
    extract_partial_content(target_file)
    
    print("\n" + "=" * 40)
    print("🏁 Analysis Complete!")
    print("\n💡 Next Steps:")
    print("1. Check the generated report file")
    print("2. Try the repaired PDF if created")
    print("3. Check partial text extraction if available")
    print("4. Consider professional recovery if critical")

if __name__ == "__main__":
    main()
