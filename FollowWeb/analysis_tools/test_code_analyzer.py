"""
Tests for the CodeAnalyzer class functionality.
"""

# Standard library imports
import os
import tempfile

# Third-party imports
import pytest

# Local imports
from .code_analyzer import CodeAnalyzer
from .models import IssueType, Severity


class TestCodeAnalyzer:
    """Test cases for CodeAnalyzer functionality."""

    def setup_method(self):
        """Initialize test environment."""
        self.analyzer = CodeAnalyzer()

    def create_temp_file(self, content: str) -> str:
        """Create a temporary Python file with specified content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            return f.name

    def teardown_temp_file(self, file_path: str):
        """Clean up temporary file."""
        if os.path.exists(file_path):
            os.unlink(file_path)

    def test_imports_at_top_no_issues(self):
        """Test that properly placed imports don't trigger issues."""
        content = '''"""Module docstring."""
from __future__ import annotations

import os
import sys
from typing import Dict, List

def some_function():
    return "hello"
'''

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that no import location issues were found
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 0, (
                "Should not flag imports at top of file"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_imports_after_code_flagged(self):
        """Test that imports after code statements are flagged."""
        content = '''"""Module docstring."""
from __future__ import annotations

import os

def some_function():
    return "hello"

import sys  # This should be flagged
from typing import Dict  # This should also be flagged

class MyClass:
    pass
'''

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that import location issues were found
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 2, (
                f"Expected 2 import issues, got {len(import_location_issues)}"
            )

            # Check specific imports that were flagged
            flagged_imports = [issue.description for issue in import_location_issues]
            assert any("sys" in desc for desc in flagged_imports), (
                "Should flag sys import"
            )
            assert any("typing.Dict" in desc for desc in flagged_imports), (
                "Should flag typing.Dict import"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_imports_after_class_flagged(self):
        """Test that imports after class definitions are flagged."""
        content = """import os

class MyClass:
    def method(self):
        pass

import sys  # This should be flagged

def function():
    pass
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that import location issues were found
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 1, (
                f"Expected 1 import issue, got {len(import_location_issues)}"
            )
            assert "sys" in import_location_issues[0].description, (
                "Should flag sys import"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_mixed_import_types_flagged(self):
        """Test both regular imports and from imports after code."""
        content = '''"""Module with mixed import issues."""

import os
from pathlib import Path

x = 42  # Non-import statement

import sys  # Regular import after code
from typing import Dict, List  # From import after code

def function():
    pass
'''

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that import location issues were found
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 2, (
                f"Expected 2 import issues, got {len(import_location_issues)}"
            )

            # Check that both types of imports are flagged
            flagged_imports = [issue.description for issue in import_location_issues]
            assert any("sys" in desc for desc in flagged_imports), (
                "Should flag sys import"
            )
            assert any(
                "typing.Dict" in desc and "typing.List" in desc
                for desc in flagged_imports
            ), "Should flag typing imports"

        finally:
            self.teardown_temp_file(test_file)

    def test_future_imports_allowed_at_top(self):
        """Test that __future__ imports are allowed at the top."""
        content = '''"""Module docstring."""
from __future__ import annotations
from __future__ import division

import os
import sys

def function():
    pass
'''

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that no import location issues were found
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 0, (
                "Should not flag __future__ imports at top"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_import_location_severity(self):
        """Test that import location issues have correct severity."""
        content = """import os

def function():
    pass

import sys  # This should be flagged
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that import location issues have medium severity
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 1, "Should find one import issue"
            assert import_location_issues[0].severity == Severity.MEDIUM, (
                "Import location issues should have medium severity"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_import_location_suggested_fix(self):
        """Test that import location issues include fix suggestions."""
        content = """import os

def function():
    pass

import sys  # This should be flagged
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that import location issues have fix suggestions
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 1, "Should find one import issue"
            issue = import_location_issues[0]
            assert issue.fix_suggestion is not None, "Should have a fix suggestion"
            assert "Move import to top of file" in issue.fix_suggestion, (
                "Should suggest moving import to top"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_unused_imports_still_detected(self):
        """Test that unused import detection still works alongside location checking."""
        content = """import os
import sys  # Unused import
from typing import Dict  # Unused import

def function():
    print("Using os:", os.path.exists("."))
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check that unused import issues were found
            unused_import_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "Unused import" in issue.description
            ]

            assert len(unused_import_issues) >= 1, "Should detect unused imports"

            # Check that no location issues were found (imports are at top)
            import_location_issues = [
                issue
                for issue in result.issues
                if issue.issue_type == IssueType.IMPORT_ISSUES
                and "not at top of file" in issue.description
            ]

            assert len(import_location_issues) == 0, (
                "Should not flag imports at top of file"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_syntax_error_handling(self):
        """Test that files with syntax errors are handled gracefully."""
        content = """import os

def function(
    # Missing closing parenthesis - syntax error
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Should return a result even with syntax errors
            assert result is not None, "Should return result even with syntax errors"
            assert result.file_path == test_file, "Should have correct file path"

        finally:
            self.teardown_temp_file(test_file)

    def test_complex_function_detection(self):
        """Test detection of functions with high cyclomatic complexity."""
        content = """def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            return "very high"
                        else:
                            return "high"
                    else:
                        return "medium-high"
                else:
                    return "medium"
            else:
                return "low-medium"
        else:
            return "low"
    else:
        return "negative"
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check for complexity issues
            complexity_issues = [
                issue
                for issue in result.issues
                if "cyclomatic complexity" in issue.description
            ]

            assert len(complexity_issues) >= 1, (
                f"Should detect high complexity function, found {len(complexity_issues)} complexity issues"
            )
            assert "complex_function" in complexity_issues[0].description, (
                "Should identify the complex function"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_missing_docstring_detection(self):
        """Test detection of missing docstrings."""
        content = '''class MyClass:
    pass

def public_function():
    return "hello"

def _private_function():
    return "private"

def documented_function():
    """This function has a docstring."""
    return "documented"
'''

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check for missing docstring issues
            docstring_issues = [
                issue
                for issue in result.issues
                if "missing a docstring" in issue.description
            ]

            # Should find issues for MyClass and public_function, but not _private_function
            assert len(docstring_issues) >= 2, (
                f"Should detect missing docstrings, found {len(docstring_issues)}"
            )

            descriptions = [issue.description for issue in docstring_issues]
            assert any("MyClass" in desc for desc in descriptions), (
                "Should flag class without docstring"
            )
            assert any("public_function" in desc for desc in descriptions), (
                "Should flag public function without docstring"
            )
            assert not any("_private_function" in desc for desc in descriptions), (
                "Should not flag private function"
            )
            assert not any("documented_function" in desc for desc in descriptions), (
                "Should not flag documented function"
            )

        finally:
            self.teardown_temp_file(test_file)

    def test_security_issue_detection(self):
        """Test detection of potential security issues."""
        content = """import os

def dangerous_function():
    user_input = input("Enter code: ")
    eval(user_input)  # Security risk

def another_risk():
    password = "hardcoded_password_123"  # Security risk
    api_key = "sk-1234567890abcdef"  # Security risk
    return password, api_key
"""

        test_file = self.create_temp_file(content)
        try:
            result = self.analyzer.analyze_file(test_file)

            # Check for security issues
            security_issues = [
                issue
                for issue in result.issues
                if issue.severity == Severity.HIGH
                and (
                    "security risk" in issue.description.lower()
                    or "hardcoded" in issue.description.lower()
                )
            ]

            assert len(security_issues) >= 2, (
                f"Should detect security issues, found {len(security_issues)}"
            )

            descriptions = [issue.description for issue in security_issues]
            assert any("eval" in desc for desc in descriptions), (
                "Should detect eval() usage"
            )
            assert any("password" in desc.lower() for desc in descriptions), (
                "Should detect hardcoded password"
            )

        finally:
            self.teardown_temp_file(test_file)


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__])
