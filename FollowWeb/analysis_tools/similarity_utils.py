"""
Consolidated similarity calculation utilities for code analysis.

This module provides unified similarity calculation methods to avoid duplication
across different analyzers.
"""

# Standard library imports
import difflib
import re
from enum import Enum
from typing import List


class SimilarityMethod(Enum):
    """Available similarity calculation methods."""

    CHARACTER_BASED = "character"
    JACCARD = "jaccard"
    SEQUENCE_MATCHER = "sequence"


class SimilarityCalculator:
    """Unified similarity calculator for different types of code comparison."""

    @staticmethod
    def calculate_similarity(
        text1: str,
        text2: str,
        method: SimilarityMethod = SimilarityMethod.SEQUENCE_MATCHER,
    ) -> float:
        """
        Calculate similarity between two text strings using specified method.

        Args:
            text1: First text string
            text2: Second text string
            method: Similarity calculation method to use

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0

        if method == SimilarityMethod.CHARACTER_BASED:
            return SimilarityCalculator._character_similarity(text1, text2)
        elif method == SimilarityMethod.JACCARD:
            return SimilarityCalculator._jaccard_similarity(text1, text2)
        elif method == SimilarityMethod.SEQUENCE_MATCHER:
            return SimilarityCalculator._sequence_similarity(text1, text2)
        else:
            raise ValueError(f"Unknown similarity method: {method}")

    @staticmethod
    def calculate_line_similarity(lines1: List[str], lines2: List[str]) -> float:
        """
        Calculate similarity between two sets of code lines using Jaccard similarity.

        Args:
            lines1: First set of code lines
            lines2: Second set of code lines

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not lines1 or not lines2:
            return 0.0

        # Normalize lines for comparison
        normalized1 = [SimilarityCalculator._normalize_line(line) for line in lines1]
        normalized2 = [SimilarityCalculator._normalize_line(line) for line in lines2]

        # Calculate Jaccard similarity
        set1 = set(normalized1)
        set2 = set(normalized2)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _character_similarity(text1: str, text2: str) -> float:
        """Calculate similarity based on common characters."""
        common_chars = sum(1 for c1, c2 in zip(text1, text2) if c1 == c2)
        max_length = max(len(text1), len(text2))
        return common_chars / max_length if max_length > 0 else 0.0

    @staticmethod
    def _jaccard_similarity(text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        # Split into words and normalize
        words1 = set(SimilarityCalculator._normalize_text(text1).split())
        words2 = set(SimilarityCalculator._normalize_text(text2).split())

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _sequence_similarity(text1: str, text2: str) -> float:
        """Calculate similarity using difflib SequenceMatcher."""
        return difflib.SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def _normalize_line(line: str) -> str:
        """Normalize a line of code for similarity comparison."""
        # Remove whitespace and comments
        normalized = re.sub(r"#.*$", "", line).strip()

        # Replace string literals with placeholder
        normalized = re.sub(r'["\'].*?["\']', '""', normalized)

        # Replace numbers with placeholder
        normalized = re.sub(r"\b\d+\b", "0", normalized)

        # Replace variable names with placeholder (simple heuristic)
        normalized = re.sub(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", "VAR", normalized)

        return normalized

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r"\s+", " ", text.lower().strip())

        # Replace string literals with placeholder
        normalized = re.sub(r'["\'].*?["\']', '""', normalized)

        # Replace numbers with placeholder
        normalized = re.sub(r"\b\d+\b", "0", normalized)

        return normalized
