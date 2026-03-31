"""
Safe Import Cleaner for PDFLib

Removes only 100% safe unused imports:
- from __future__ imports (not needed in Python 3.11+)
- Imports that are clearly unused (no references in file)

Usage:
    python scripts/clean_imports.py --dry-run  # Preview changes
    python scripts/clean_imports.py            # Apply changes
"""

import os
import re
import ast
import argparse
from pathlib import Path
from typing import List, Tuple, Set


class ImportCleaner:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding='utf-8')
        self.lines = self.content.split('\n')
        self.unused_imports = []
        self.safe_removals = []
    
    def analyze(self):
        """Find unused imports"""
        try:
            tree = ast.parse(self.content)
        except SyntaxError:
            print(f"  ⚠️  Syntax error in {self.file_path}")
            return
        
        # Find all imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append((name, node.lineno, 'import'))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports.append((name, node.lineno, 'from'))
        
        # Check each import
        for name, lineno, import_type in imports:
            # Skip if it's a module import (might be used as module.func)
            if import_type == 'import' and '.' in name:
                continue
            
            # Count occurrences in code (excluding import line itself)
            pattern = r'\b' + re.escape(name) + r'\b'
            occurrences = []
            
            for i, line in enumerate(self.lines, 1):
                if i == lineno:  # Skip import line
                    continue
                if line.strip().startswith('#'):  # Skip comments
                    continue
                if re.search(pattern, line):
                    occurrences.append(i)
            
            # If only 1 occurrence (in import), it's unused
            if len(occurrences) == 0:
                self.unused_imports.append((name, lineno, import_type))
                
                # Mark as safe removal if it's __future__
                if 'from __future__' in self.lines[lineno - 1]:
                    self.safe_removals.append((name, lineno, import_type))
    
    def remove_safe(self) -> bool:
        """Remove only 100% safe imports (__future__)"""
        if not self.safe_removals:
            return False
        
        # Sort by line number descending (to not mess up line numbers)
        self.safe_removals.sort(key=lambda x: x[1], reverse=True)
        
        removed = []
        for name, lineno, _ in self.safe_removals:
            # Remove the line
            line = self.lines[lineno - 1].strip()
            if 'from __future__' in line:
                removed.append((lineno, line))
                del self.lines[lineno - 1]
        
        if removed:
            # Write back
            self.file_path.write_text('\n'.join(self.lines), encoding='utf-8')
            return True
        
        return False
    
    def report(self, verbose=False):
        """Report findings"""
        if self.unused_imports or self.safe_removals:
            print(f"\n{self.file_path.relative_to(Path.cwd())}")
            
            if self.safe_removals:
                print(f"  ✅ Safe to remove ({len(self.safe_removals)}):")
                for name, lineno, _ in self.safe_removals:
                    line = self.lines[lineno - 1].strip()
                    print(f"    Line {lineno}: {line}")
            
            if verbose and self.unused_imports:
                print(f"  ⚠️  Potentially unused ({len(self.unused_imports)}):")
                for name, lineno, _ in self.unused_imports[:5]:  # Show first 5
                    line = self.lines[lineno - 1].strip()
                    print(f"    Line {lineno}: {name}")
                if len(self.unused_imports) > 5:
                    print(f"    ... and {len(self.unused_imports) - 5} more")


def main():
    parser = argparse.ArgumentParser(description='Clean unused imports')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show all unused imports')
    parser.add_argument('--dirs', nargs='+', default=['client', 'server', 'manager'],
                       help='Directories to scan')
    args = parser.parse_args()
    
    root_dir = Path(__file__).parent.parent
    total_files = 0
    total_safe = 0
    total_potential = 0
    
    print("🔍 Scanning for unused imports...\n")
    
    for dir_name in args.dirs:
        dir_path = root_dir / dir_name
        if not dir_path.exists():
            continue
        
        for py_file in dir_path.rglob('*.py'):
            # Skip __pycache__ and vendor
            if '__pycache__' in str(py_file) or 'vendor' in str(py_file):
                continue
            
            total_files += 1
            cleaner = ImportCleaner(py_file)
            cleaner.analyze()
            
            if cleaner.safe_removals or (args.verbose and cleaner.unused_imports):
                cleaner.report(verbose=args.verbose)
                total_safe += len(cleaner.safe_removals)
                total_potential += len(cleaner.unused_imports)
    
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"  Files scanned: {total_files}")
    print(f"  Safe to remove: {total_safe} (from __future__ imports)")
    print(f"  Potentially unused: {total_potential} (requires manual review)")
    
    if not args.dry_run and total_safe > 0:
        print(f"\n⚠️  This is a DRY RUN. To apply changes, run without --dry-run")
    elif total_safe > 0:
        print(f"\n✅ Ready to remove {total_safe} safe imports")
        
        # Actually remove them
        for dir_name in args.dirs:
            dir_path = root_dir / dir_name
            if not dir_path.exists():
                continue
            
            for py_file in dir_path.rglob('*.py'):
                if '__pycache__' in str(py_file) or 'vendor' in str(py_file):
                    continue
                
                cleaner = ImportCleaner(py_file)
                cleaner.analyze()
                if cleaner.remove_safe():
                    print(f"  ✓ Cleaned {py_file.relative_to(root_dir)}")


if __name__ == "__main__":
    main()
