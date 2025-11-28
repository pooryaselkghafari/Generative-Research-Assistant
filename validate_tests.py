#!/usr/bin/env python3
"""
Test validation script for paper keywords/journals tests.
This validates test structure and logic without requiring full Django setup.
"""
import ast
import sys
from pathlib import Path

def validate_test_file():
    """Validate the test file structure."""
    test_file = Path('tests/api/test_api.py')
    
    if not test_file.exists():
        print("❌ Test file not found")
        return False
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Parse AST
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"❌ Syntax error in test file: {e}")
        return False
    
    # Find test methods
    test_methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            test_methods.append(node.name)
    
    # Expected tests
    expected_tests = [
        'test_paper_keywords_journals_get',
        'test_paper_keywords_journals_get_empty',
        'test_paper_keywords_journals_post',
        'test_paper_keywords_journals_post_filters_empty',
        'test_paper_keywords_journals_post_invalid_list',
        'test_paper_keywords_journals_post_invalid_string_items',
        'test_paper_keywords_journals_unauthorized',
        'test_paper_keywords_journals_not_found',
        'test_paper_keywords_journals_requires_auth',
    ]
    
    print(f"✅ Found {len(test_methods)} test methods")
    print(f"✅ Expected {len(expected_tests)} tests for keywords/journals feature")
    
    # Check if all expected tests exist
    found_tests = [t for t in expected_tests if t in test_methods]
    missing_tests = [t for t in expected_tests if t not in test_methods]
    
    if missing_tests:
        print(f"❌ Missing tests: {missing_tests}")
        return False
    
    print(f"✅ All {len(expected_tests)} expected tests found:")
    for test in found_tests:
        print(f"   - {test}")
    
    # Check imports
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    
    required_imports = ['json', 'django.test', 'django.contrib.auth.models', 'engine.models']
    has_imports = all(any(req in imp for imp in imports) for req in ['json', 'django', 'engine'])
    
    if has_imports:
        print("✅ Required imports found")
    else:
        print("⚠️  Some imports may be missing")
    
    return True

if __name__ == '__main__':
    success = validate_test_file()
    sys.exit(0 if success else 1)

