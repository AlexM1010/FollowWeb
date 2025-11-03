"""
AST utility functions for code analysis tools.

This module provides shared utilities for parsing and analyzing Python AST nodes.
"""

import ast
from typing import Set


def extract_all_exports(tree: ast.AST) -> Set[str]:
    """
    Extract names from __all__ list in __init__.py files.

    Args:
        tree: The AST tree to analyze

    Returns:
        Set of names that are exported via __all__ list
    """
    all_exports = set()

    for node in ast.walk(tree):
        # Look for __all__ assignment
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        ):
            # Extract string literals from the list
            if isinstance(node.value, ast.List):
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        all_exports.add(item.value)
                    elif isinstance(item, ast.Str):  # For older Python versions
                        all_exports.add(item.s)

    return all_exports


def is_init_file(file_path: str) -> bool:
    """
    Check if a file path represents an __init__.py file.

    Args:
        file_path: Path to the file

    Returns:
        True if the file is an __init__.py file
    """
    return file_path.endswith("__init__.py")


def extract_import_names(tree: ast.AST) -> list:
    """
    Extract all import names from an AST tree.

    Args:
        tree: The AST tree to analyze

    Returns:
        List of tuples (import_name, alias, line_number)
    """
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, alias.asname, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                full_name = f"{module}.{alias.name}" if module else alias.name
                imports.append((full_name, alias.asname, node.lineno))

    return imports


def extract_used_names(tree: ast.AST) -> Set[str]:
    """
    Extract all names that are used in the code.

    Args:
        tree: The AST tree to analyze

    Returns:
        Set of names that are referenced in the code
    """
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Handle attribute access like module.function
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    return used_names
