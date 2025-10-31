"""
Pattern detection utilities for identifying AI language artifacts and code patterns.
"""

# Standard library imports
import re
from typing import Dict, List

# Local imports
from .models import CodeIssue, CodeLocation, IssueType, Severity


class PatternDetector:
    """Detects various patterns in code including AI language artifacts."""

    def __init__(self):
        self.ai_patterns = self._initialize_ai_patterns()
        self.error_message_patterns = self._initialize_error_patterns()
        self.validation_patterns = self._initialize_validation_patterns()

    def _initialize_ai_patterns(self) -> Dict[str, List[str]]:
        """Initialize AI language detection patterns."""
        return {
            "overused_adjectives": [
                r"\bcomprehensive\b",
                r"\benhanced\b",
                r"\brobust\b",
                r"\bseamless\b",
                r"\bcutting-edge\b",
                r"\bstate-of-the-art\b",
                r"\bpowerful\b",
                r"\badvanced\b",
                r"\bsophisticated\b",
                r"\boptimized\b",
                r"\bstreamlined\b",
                r"\befficient\b",
                r"\bflexible\b",
                r"\bscalable\b",
                r"\binnovative\b",
                r"\bversatile\b",
                r"\bdynamic\b",
                r"\bintelligent\b",
            ],
            "marketing_phrases": [
                r"best-in-class",
                r"industry-leading",
                r"world-class",
                r"next-generation",
                r"revolutionary",
                r"game-changing",
                r"breakthrough",
                r"cutting edge",
                r"state of the art",
            ],
            "generic_descriptions": [
                r"provides.*functionality",
                r"offers.*capabilities",
                r"delivers.*performance",
                r"ensures.*quality",
                r"enables.*features",
                r"facilitates.*operations",
            ],
        }

    def _initialize_error_patterns(self) -> List[str]:
        """Initialize patterns for generic error messages."""
        return [
            r"An error occurred",
            r"Something went wrong",
            r"Operation failed",
            r"Invalid input",
            r"Error processing",
            r"Failed to process",
            r"Unable to complete",
        ]

    def _initialize_validation_patterns(self) -> List[str]:
        """Initialize patterns for redundant validation."""
        return [
            r"if\s+.*\s+is\s+None:",
            r"if\s+not\s+.*:",
            r"assert\s+.*\s+is\s+not\s+None",
            r"if\s+len\(.*\)\s*==\s*0:",
            r'if\s+.*\s+==\s+"":',
        ]

    def detect_ai_language_in_text(
        self, text: str, file_path: str, start_line: int = 1
    ) -> List[CodeIssue]:
        """Detect AI-generated language patterns in text."""
        issues = []
        lines = text.split("\n")

        for line_offset, line in enumerate(lines):
            line_num = start_line + line_offset

            # Check each pattern category
            for category, patterns in self.ai_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        severity = self._determine_ai_severity(category, match.group())

                        issues.append(
                            CodeIssue(
                                issue_type=IssueType.AI_LANGUAGE,
                                location=CodeLocation(
                                    file_path, line_num, match.start()
                                ),
                                description=f"AI language detected ({category}): '{match.group()}'",
                                severity=severity,
                                fix_suggestion=self._suggest_replacement(
                                    match.group(), category
                                ),
                                context=line.strip(),
                            )
                        )

        return issues

    def detect_generic_error_messages(
        self, text: str, file_path: str, start_line: int = 1
    ) -> List[CodeIssue]:
        """Detect generic error messages that should be more specific."""
        issues = []
        lines = text.split("\n")

        for line_offset, line in enumerate(lines):
            line_num = start_line + line_offset

            # Look for error messages in strings
            if any(quote in line for quote in ['"', "'"]):
                for pattern in self.error_message_patterns:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        issues.append(
                            CodeIssue(
                                issue_type=IssueType.ERROR_HANDLING,
                                location=CodeLocation(
                                    file_path, line_num, match.start()
                                ),
                                description=f"Generic error message: '{match.group()}'",
                                severity=Severity.MEDIUM,
                                fix_suggestion="Replace with specific, descriptive error message",
                                context=line.strip(),
                            )
                        )

        return issues

    def detect_redundant_validation(
        self, text: str, file_path: str, start_line: int = 1
    ) -> List[CodeIssue]:
        """Detect potentially redundant validation patterns."""
        issues = []
        lines = text.split("\n")
        validation_locations = []

        for line_offset, line in enumerate(lines):
            line_num = start_line + line_offset

            for pattern in self.validation_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    validation_locations.append((line_num, match.group(), line.strip()))

        # Look for similar validation patterns that might be redundant
        for i, (line1, pattern1, context1) in enumerate(validation_locations):
            for line2, pattern2, _context2 in validation_locations[i + 1 :]:
                if self._are_similar_validations(pattern1, pattern2):
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.REDUNDANT_VALIDATION,
                            location=CodeLocation(file_path, line1),
                            description=f"Similar validation found at lines {line1} and {line2}",
                            severity=Severity.LOW,
                            fix_suggestion="Consider consolidating validation logic",
                            context=context1,
                        )
                    )

        return issues

    def _determine_ai_severity(self, category: str, text: str) -> Severity:
        """Determine severity based on AI pattern category and context."""
        if category == "marketing_phrases":
            return Severity.HIGH
        elif category == "overused_adjectives":
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _suggest_replacement(self, text: str, category: str) -> str:
        """Suggest replacement for AI-generated text."""
        replacements = {
            "comprehensive": "complete",
            "enhanced": "improved",
            "robust": "reliable",
            "seamless": "smooth",
            "cutting-edge": "modern",
            "state-of-the-art": "current",
            "powerful": "capable",
            "advanced": "complex",
            "sophisticated": "detailed",
            "optimized": "efficient",
            "streamlined": "simplified",
            "flexible": "adaptable",
            "scalable": "expandable",
            "novel": "new",
            "versatile": "multi-purpose",
            "dynamic": "changing",
            "intelligent": "automated",
        }

        lower_text = text.lower()
        if lower_text in replacements:
            return f"Consider replacing with '{replacements[lower_text]}'"

        return "Replace with more specific technical terminology"

    def _are_similar_validations(self, pattern1: str, pattern2: str) -> bool:
        """Check if two validation patterns are similar."""
        # Simple similarity check - could be enhanced
        pattern1_clean = re.sub(r"\s+", " ", pattern1.strip())
        pattern2_clean = re.sub(r"\s+", " ", pattern2.strip())

        # Check for similar structure
        if pattern1_clean.startswith("if") and pattern2_clean.startswith("if"):
            # Extract the condition part
            cond1 = (
                pattern1_clean.split(":")[0]
                if ":" in pattern1_clean
                else pattern1_clean
            )
            cond2 = (
                pattern2_clean.split(":")[0]
                if ":" in pattern2_clean
                else pattern2_clean
            )

            # Simple similarity based on common words
            words1 = set(cond1.split())
            words2 = set(cond2.split())

            if len(words1) > 0 and len(words2) > 0:
                intersection = len(words1.intersection(words2))
                union = len(words1.union(words2))
                similarity = intersection / union
                return similarity > 0.6

        return False

    def scan_docstrings_and_comments(
        self, file_content: str, file_path: str
    ) -> List[CodeIssue]:
        """Scan docstrings and comments for AI language patterns."""
        issues = []
        lines = file_content.split("\n")

        in_docstring = False
        docstring_start = 0
        docstring_content = []

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Handle docstrings
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_start = line_num
                    docstring_content = [line]
                else:
                    in_docstring = False
                    docstring_content.append(line)

                    # Analyze complete docstring
                    full_docstring = "\n".join(docstring_content)
                    docstring_issues = self.detect_ai_language_in_text(
                        full_docstring, file_path, docstring_start
                    )
                    issues.extend(docstring_issues)

                    docstring_content = []
            elif in_docstring:
                docstring_content.append(line)

            # Handle single-line comments
            elif stripped.startswith("#"):
                comment_issues = self.detect_ai_language_in_text(
                    line, file_path, line_num
                )
                issues.extend(comment_issues)

        return issues
