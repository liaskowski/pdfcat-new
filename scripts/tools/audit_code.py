"""
Code Audit Script for PDFLib

Performs:
1. Dead code detection (unused imports, unused functions)
2. Code duplication detection
3. Large file detection
4. TODO/FIXME tracking
5. Code complexity analysis

Usage:
    python scripts/audit_code.py
"""

import os
import re
import ast
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class CodeAuditor:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.issues = []
        self.stats = {
            'total_files': 0,
            'total_lines': 0,
            'total_functions': 0,
            'total_classes': 0,
            'large_files': [],
            'complex_functions': [],
            'duplicated_code': [],
            'dead_code': [],
            'todos': []
        }
    
    def scan_directory(self, include_dirs: List[str] = None, exclude_dirs: List[str] = None):
        """Scan Python files in directory"""
        if exclude_dirs is None:
            exclude_dirs = ['__pycache__', 'vendor', 'node_modules', '.git', 'venv', 'env']
        
        if include_dirs is None:
            include_dirs = ['client', 'server', 'manager']
        
        for dir_name in include_dirs:
            dir_path = self.root_dir / dir_name
            if not dir_path.exists():
                continue
            
            for py_file in dir_path.rglob('*.py'):
                # Skip excluded directories
                if any(excl in str(py_file) for excl in exclude_dirs):
                    continue
                
                self.analyze_file(py_file)
    
    def analyze_file(self, file_path: Path):
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return
        
        self.stats['total_files'] += 1
        self.stats['total_lines'] += len(lines)
        
        # Check for large files
        if len(lines) > 400:
            self.stats['large_files'].append({
                'file': str(file_path.relative_to(self.root_dir)),
                'lines': len(lines)
            })
            self.issues.append(f"LARGE_FILE: {file_path.relative_to(self.root_dir)} ({len(lines)} lines)")
        
        # Analyze TODOs and FIXMEs
        self.find_todos(file_path, lines)
        
        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content)
            self.analyze_ast(file_path, content, tree)
        except SyntaxError as e:
            self.issues.append(f"SYNTAX_ERROR: {file_path.relative_to(self.root_dir)} - {e}")
        
        # Check for code duplication (simple line-based)
        self.check_duplication(file_path, lines)
    
    def analyze_ast(self, file_path: Path, content: str, tree: ast.AST):
        """Analyze AST for dead code and complexity"""
        functions = []
        classes = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                self.stats['total_functions'] += 1
                
                # Check function complexity
                complexity = self.calculate_complexity(node)
                if complexity > 10:
                    self.stats['complex_functions'].append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'function': node.name,
                        'complexity': complexity
                    })
            
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                self.stats['total_classes'] += 1
            
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
        
        # Check for unused imports (simple heuristic)
        self.check_unused_imports(file_path, content, imports)
    
    def calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                 ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def check_unused_imports(self, file_path: Path, content: str, imports: List[str]):
        """Check for potentially unused imports"""
        for imp in imports:
            # Simple check: if import name appears only once (in import statement)
            # This is not perfect but catches obvious cases
            occurrences = len(re.findall(r'\b' + re.escape(imp) + r'\b', content))
            if occurrences == 1:
                self.stats['dead_code'].append({
                    'type': 'unused_import',
                    'file': str(file_path.relative_to(self.root_dir)),
                    'name': imp
                })
                self.issues.append(f"UNUSED_IMPORT: {imp} in {file_path.relative_to(self.root_dir)}")
    
    def check_duplication(self, file_path: Path, lines: List[str]):
        """Check for duplicated code blocks (simple 5+ line duplication)"""
        # Normalize lines (remove whitespace and comments)
        normalized = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                normalized.append((i+1, stripped))
        
        # Find 5+ line duplications within the same file
        for i in range(len(normalized) - 4):
            block = tuple(line for _, line in normalized[i:i+5])
            
            # Check if this block appears elsewhere
            for j in range(i + 5, len(normalized) - 4):
                other_block = tuple(line for _, line in normalized[j:j+5])
                
                if block == other_block and len(block) > 3:  # At least 4 lines
                    start_line = normalized[i][0]
                    dup_line = normalized[j][0]
                    
                    self.stats['duplicated_code'].append({
                        'file': str(file_path.relative_to(self.root_dir)),
                        'lines': f"{start_line}-{start_line+4} and {dup_line}-{dup_line+4}"
                    })
                    break  # Only report first duplication
    
    def find_todos(self, file_path: Path, lines: List[str]):
        """Find TODO, FIXME, XXX comments"""
        todo_pattern = re.compile(r'#\s*(TODO|FIXME|XXX|HACK|BUG)(?::|\s)(.+)', re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            match = todo_pattern.search(line)
            if match:
                self.stats['todos'].append({
                    'file': str(file_path.relative_to(self.root_dir)),
                    'line': i,
                    'type': match.group(1).upper(),
                    'message': match.group(2).strip()
                })
    
    def generate_report(self, output_file: str = None):
        """Generate audit report"""
        report = []
        report.append("=" * 80)
        report.append("PDFLib Code Audit Report")
        report.append("=" * 80)
        report.append("")
        
        # Statistics
        report.append("STATISTICS")
        report.append("-" * 40)
        report.append(f"Total files analyzed: {self.stats['total_files']}")
        report.append(f"Total lines of code: {self.stats['total_lines']}")
        report.append(f"Total functions: {self.stats['total_functions']}")
        report.append(f"Total classes: {self.stats['total_classes']}")
        report.append("")
        
        # Issues summary
        report.append("ISSUES SUMMARY")
        report.append("-" * 40)
        report.append(f"Large files (>400 lines): {len(self.stats['large_files'])}")
        report.append(f"Complex functions (>10): {len(self.stats['complex_functions'])}")
        report.append(f"Dead code (unused imports): {len(self.stats['dead_code'])}")
        report.append(f"Duplicated code blocks: {len(self.stats['duplicated_code'])}")
        report.append(f"TODOs/FIXMEs: {len(self.stats['todos'])}")
        report.append("")
        
        # Large files
        if self.stats['large_files']:
            report.append("LARGE FILES")
            report.append("-" * 40)
            for item in self.stats['large_files'][:10]:  # Show top 10
                report.append(f"  {item['file']}: {item['lines']} lines")
            report.append("")
        
        # Complex functions
        if self.stats['complex_functions']:
            report.append("COMPLEX FUNCTIONS")
            report.append("-" * 40)
            for item in self.stats['complex_functions'][:10]:
                report.append(f"  {item['file']}::{item['function']}: complexity {item['complexity']}")
            report.append("")
        
        # Dead code
        if self.stats['dead_code']:
            report.append("DEAD CODE (Unused Imports)")
            report.append("-" * 40)
            for item in self.stats['dead_code'][:20]:  # Show top 20
                report.append(f"  {item['file']}: {item['name']}")
            report.append("")
        
        # TODOs
        if self.stats['todos']:
            report.append("TODOs/FIXMEs")
            report.append("-" * 40)
            for item in self.stats['todos'][:20]:
                report.append(f"  {item['file']}:{item['line']} [{item['type']}] {item['message']}")
            report.append("")
        
        # All issues
        if self.issues:
            report.append("ALL ISSUES")
            report.append("-" * 40)
            for issue in self.issues[:50]:  # Show top 50
                report.append(f"  - {issue}")
            report.append("")
        
        report_text = '\n'.join(report)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"Report saved to: {output_file}")
        
        print(report_text)
        return report_text


def main():
    """Main entry point"""
    root_dir = Path(__file__).parent.parent
    
    # Create logs directory
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    print("Starting code audit...")
    auditor = CodeAuditor(root_dir)
    auditor.scan_directory()
    auditor.generate_report(output_file=str(logs_dir / "code_audit.txt"))
    
    print("\nAudit complete!")


if __name__ == "__main__":
    main()
