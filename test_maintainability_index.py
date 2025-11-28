#!/usr/bin/env python3
"""
Maintainability Index (MI) Calculator for StatBox Codebase

This script calculates the Maintainability Index for Python modules,
helping identify code quality issues and areas for improvement.

MI Formula (Microsoft):
MI = max(0, (171 - 5.2 * ln(Halstead Volume) - 0.23 * (Cyclomatic Complexity) 
     - 16.2 * ln(Lines of Code) + 50 * sin(sqrt(2.4 * Comment Ratio))) * 100 / 171)

Simplified version used here:
MI = max(0, 171 - 5.2 * ln(avg_halstead) - 0.23 * avg_complexity 
     - 16.2 * ln(avg_lines) + 50 * sin(sqrt(2.4 * comment_ratio))) * 100 / 171

Where:
- Halstead Volume ≈ (operators + operands) * log2(unique_operators + unique_operands)
- Complexity = Control Flow statements (if, for, while, try, except, etc.)
- Lines = Lines of code
- Comment Ratio = Comments / Total lines
"""

import os
import re
import ast
import math
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Control flow keywords
CONTROL_FLOW_KEYWORDS = {
    'if', 'elif', 'else', 'for', 'while', 'try', 'except', 
    'finally', 'with', 'assert', 'break', 'continue', 'return',
    'yield', 'raise', 'pass'
}

# Operators (Python)
OPERATORS = {
    '+', '-', '*', '/', '//', '%', '**', '==', '!=', '<', '>', 
    '<=', '>=', '=', '+=', '-=', '*=', '/=', '//=', '%=', '**=',
    '&', '|', '^', '~', '<<', '>>', 'and', 'or', 'not', 'in', 
    'is', 'not in', 'is not', '.', '(', ')', '[', ']', '{', '}',
    ':', ',', ';', '@', '->', '...'
}

# Keywords that count as operands
KEYWORD_OPERANDS = {
    'True', 'False', 'None', 'self', 'cls', 'super'
}


def count_lines(content: str) -> Tuple[int, int, int]:
    """Count total lines, code lines, and comment lines."""
    lines = content.split('\n')
    total_lines = len(lines)
    code_lines = 0
    comment_lines = 0
    
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
        
        # Check for multiline comments
        if '"""' in stripped or "'''" in stripped:
            in_multiline_comment = not in_multiline_comment
            comment_lines += 1
            continue
        
        if in_multiline_comment:
            comment_lines += 1
            continue
        
        # Single line comments
        if stripped.startswith('#'):
            comment_lines += 1
        else:
            # Check for inline comments
            if '#' in line:
                # Split by # and check if there's code before it
                parts = line.split('#')
                if parts[0].strip():
                    code_lines += 1
                else:
                    comment_lines += 1
            else:
                code_lines += 1
    
    return total_lines, code_lines, comment_lines


def count_control_flow(content: str) -> int:
    """Count control flow statements in code."""
    count = 0
    for keyword in CONTROL_FLOW_KEYWORDS:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(keyword) + r'\b'
        count += len(re.findall(pattern, content))
    return count


def count_halstead_volume(content: str) -> Tuple[int, int]:
    """Estimate Halstead volume by counting operators and operands."""
    try:
        tree = ast.parse(content)
    except:
        # If parsing fails, use simple regex-based estimation
        return estimate_halstead_simple(content)
    
    operators = set()
    operands = set()
    
    class HalsteadVisitor(ast.NodeVisitor):
        def visit_BinOp(self, node):
            operators.add(type(node.op).__name__)
            self.generic_visit(node)
        
        def visit_UnaryOp(self, node):
            operators.add(type(node.op).__name__)
            self.generic_visit(node)
        
        def visit_Compare(self, node):
            for op in node.ops:
                operators.add(type(op).__name__)
            self.generic_visit(node)
        
        def visit_BoolOp(self, node):
            operators.add(type(node.op).__name__)
            self.generic_visit(node)
        
        def visit_Name(self, node):
            if not isinstance(node.ctx, ast.Store):
                operands.add(node.id)
            self.generic_visit(node)
        
        def visit_Constant(self, node):
            operands.add(str(node.value))
            self.generic_visit(node)
        
        def visit_Attribute(self, node):
            operands.add(node.attr)
            self.generic_visit(node)
        
        def visit_Call(self, node):
            operators.add('call')
            self.generic_visit(node)
        
        def visit_Subscript(self, node):
            operators.add('subscript')
            self.generic_visit(node)
    
    visitor = HalsteadVisitor()
    visitor.visit(tree)
    
    # Count total occurrences
    operator_count = len(operators)
    operand_count = len(operands)
    
    return operator_count, operand_count


def estimate_halstead_simple(content: str) -> Tuple[int, int]:
    """Simple regex-based Halstead estimation when AST parsing fails."""
    # Count operators (simplified)
    operator_patterns = [
        r'\+\+|--',  # Not in Python but for completeness
        r'[+\-*/%=<>&|^~!]+',  # Operators
        r'\b(and|or|not|in|is)\b',  # Logical operators
        r'[()\[\]{}]',  # Brackets
        r'\.',  # Dot operator
        r',',  # Comma
        r':',  # Colon
    ]
    
    operators = set()
    for pattern in operator_patterns:
        matches = re.findall(pattern, content)
        operators.update(matches)
    
    # Count operands (identifiers, literals)
    identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    identifiers = set(re.findall(identifier_pattern, content))
    
    # Filter out keywords
    python_keywords = {
        'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally',
        'def', 'class', 'return', 'yield', 'break', 'continue', 'pass',
        'import', 'from', 'as', 'with', 'assert', 'raise', 'del',
        'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None',
        'lambda', 'global', 'nonlocal'
    }
    operands = identifiers - python_keywords - operators
    
    return len(operators), len(operands)


def analyze_function(func_node: ast.FunctionDef, content: str) -> Dict:
    """Analyze a single function."""
    # Get function lines
    func_lines = content.split('\n')[func_node.lineno - 1:func_node.end_lineno]
    func_content = '\n'.join(func_lines)
    
    total_lines, code_lines, comment_lines = count_lines(func_content)
    cf_count = count_control_flow(func_content)
    op_count, operand_count = count_halstead_volume(func_content)
    
    # Estimate Halstead volume
    if op_count > 0 and operand_count > 0:
        halstead_volume = (op_count + operand_count) * math.log2(max(op_count + operand_count, 1))
    else:
        halstead_volume = code_lines * 2  # Fallback
    
    comment_ratio = comment_lines / max(total_lines, 1)
    
    # Calculate complexity (simplified: control flow + nesting)
    complexity = cf_count + 1  # +1 for function itself
    
    return {
        'name': func_node.name,
        'lines': code_lines,
        'total_lines': total_lines,
        'comment_lines': comment_lines,
        'comment_ratio': comment_ratio,
        'control_flow': cf_count,
        'complexity': complexity,
        'halstead_volume': halstead_volume,
        'operators': op_count,
        'operands': operand_count
    }


def calculate_mi(halstead_volume: float, complexity: float, lines: float, comment_ratio: float) -> float:
    """Calculate Maintainability Index."""
    if halstead_volume <= 0 or lines <= 0:
        return 0.0
    
    try:
        mi = (171 - 
              5.2 * math.log(max(halstead_volume, 1)) - 
              0.23 * complexity - 
              16.2 * math.log(max(lines, 1)) + 
              50 * math.sin(math.sqrt(2.4 * comment_ratio))) * 100 / 171
        
        return max(0, min(100, mi))  # Clamp between 0 and 100
    except:
        return 0.0


def analyze_module(file_path: Path) -> Dict:
    """Analyze a Python module."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return None
    
    # Module-level metrics
    total_lines, code_lines, comment_lines = count_lines(content)
    cf_count = count_control_flow(content)
    op_count, operand_count = count_halstead_volume(content)
    
    if op_count > 0 and operand_count > 0:
        halstead_volume = (op_count + operand_count) * math.log2(max(op_count + operand_count, 1))
    else:
        halstead_volume = code_lines * 2
    
    comment_ratio = comment_lines / max(total_lines, 1)
    
    # Function-level analysis
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            func_analysis = analyze_function(node, content)
            functions.append(func_analysis)
    
    # Calculate averages
    if functions:
        avg_lines = sum(f['lines'] for f in functions) / len(functions)
        avg_complexity = sum(f['complexity'] for f in functions) / len(functions)
        avg_halstead = sum(f['halstead_volume'] for f in functions) / len(functions)
        avg_comment_ratio = sum(f['comment_ratio'] for f in functions) / len(functions)
    else:
        avg_lines = code_lines
        avg_complexity = cf_count + 1
        avg_halstead = halstead_volume
        avg_comment_ratio = comment_ratio
    
    # Calculate MI
    mi = calculate_mi(avg_halstead, avg_complexity, avg_lines, avg_comment_ratio)
    
    return {
        'file': str(file_path),
        'module': file_path.stem,
        'total_lines': total_lines,
        'code_lines': code_lines,
        'comment_lines': comment_lines,
        'comment_ratio': comment_ratio,
        'control_flow': cf_count,
        'functions': len(functions),
        'avg_function_lines': avg_lines,
        'avg_complexity': avg_complexity,
        'avg_halstead': avg_halstead,
        'mi': mi,
        'functions_detail': functions
    }


def analyze_directory(directory: Path, exclude_patterns: List[str] = None) -> List[Dict]:
    """Analyze all Python files in a directory."""
    if exclude_patterns is None:
        exclude_patterns = ['migrations', '__pycache__', '.git', 'venv', 'env', 'node_modules']
    
    results = []
    
    for py_file in directory.rglob('*.py'):
        # Skip excluded patterns
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue
        
        result = analyze_module(py_file)
        if result:
            results.append(result)
    
    return results


def main():
    """Main function to run MI analysis."""
    # Analyze engine/views directory
    views_dir = Path('engine/views')
    services_dir = Path('engine/services')
    helpers_dir = Path('engine/helpers')
    
    print("=" * 80)
    print("MAINTAINABILITY INDEX (MI) ANALYSIS")
    print("=" * 80)
    print()
    
    all_results = []
    
    # Analyze views
    if views_dir.exists():
        print(f"Analyzing {views_dir}...")
        views_results = analyze_directory(views_dir)
        all_results.extend(views_results)
    
    # Analyze services
    if services_dir.exists():
        print(f"Analyzing {services_dir}...")
        services_results = analyze_directory(services_dir)
        all_results.extend(services_results)
    
    # Analyze helpers
    if helpers_dir.exists():
        print(f"Analyzing {helpers_dir}...")
        helpers_results = analyze_directory(helpers_dir)
        all_results.extend(helpers_results)
    
    if not all_results:
        print("No Python files found to analyze.")
        return
    
    # Calculate weighted average MI
    total_lines = sum(r['code_lines'] for r in all_results)
    weighted_mi = sum(r['mi'] * r['code_lines'] for r in all_results) / total_lines if total_lines > 0 else 0
    
    # Print results
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    # Sort by MI (lowest first)
    all_results.sort(key=lambda x: x['mi'])
    
    print(f"{'Module':<30} {'Lines':<8} {'Funcs':<6} {'CF':<6} {'Avg Func':<10} {'MI':<8} {'Status':<15}")
    print("-" * 80)
    
    for result in all_results:
        mi = result['mi']
        if mi >= 80:
            status = "✅ Excellent"
        elif mi >= 70:
            status = "🟢 Good"
        elif mi >= 60:
            status = "🟡 Needs Work"
        else:
            status = "🔴 Critical"
        
        print(f"{result['module']:<30} {result['code_lines']:<8} {result['functions']:<6} "
              f"{result['control_flow']:<6} {result['avg_function_lines']:<10.1f} "
              f"{mi:<8.1f} {status:<15}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    total_code_lines = sum(r['code_lines'] for r in all_results)
    total_functions = sum(r['functions'] for r in all_results)
    total_cf = sum(r['control_flow'] for r in all_results)
    avg_func_size = sum(r['avg_function_lines'] for r in all_results) / len(all_results) if all_results else 0
    
    print(f"Total Modules Analyzed: {len(all_results)}")
    print(f"Total Lines of Code: {total_code_lines:,}")
    print(f"Total Functions: {total_functions}")
    print(f"Total Control Flow Statements: {total_cf}")
    print(f"Average Function Size: {avg_func_size:.1f} lines")
    print(f"Weighted Average MI: {weighted_mi:.1f}/100")
    print()
    
    # Status breakdown
    excellent = sum(1 for r in all_results if r['mi'] >= 80)
    good = sum(1 for r in all_results if 70 <= r['mi'] < 80)
    needs_work = sum(1 for r in all_results if 60 <= r['mi'] < 70)
    critical = sum(1 for r in all_results if r['mi'] < 60)
    
    print("Status Breakdown:")
    print(f"  ✅ Excellent (80+): {excellent} modules")
    print(f"  🟢 Good (70-79): {good} modules")
    print(f"  🟡 Needs Work (60-69): {needs_work} modules")
    print(f"  🔴 Critical (<60): {critical} modules")
    print()
    
    # Recommendations
    if weighted_mi < 80:
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        low_mi_modules = [r for r in all_results if r['mi'] < 70]
        if low_mi_modules:
            print("Modules needing improvement:")
            for module in sorted(low_mi_modules, key=lambda x: x['mi']):
                print(f"  - {module['module']}: MI={module['mi']:.1f}, "
                      f"Lines={module['code_lines']}, Functions={module['functions']}, "
                      f"Avg Func Size={module['avg_function_lines']:.1f}")
                print(f"    → Consider breaking down large functions")
                print(f"    → Extract complex logic into service classes")
                print(f"    → Reduce control flow complexity")
                print()
        
        large_functions = []
        for result in all_results:
            for func in result.get('functions_detail', []):
                if func['lines'] > 50:
                    large_functions.append((result['module'], func['name'], func['lines']))
        
        if large_functions:
            print("Large functions (>50 lines):")
            for module, func_name, lines in sorted(large_functions, key=lambda x: x[2], reverse=True)[:10]:
                print(f"  - {module}.{func_name}: {lines} lines")
            print()
    
    print("=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()



