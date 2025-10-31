"""
Code analysis utilities for scanning Python files and detecting quality issues.
"""

# Standard library imports
import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

# Local imports
from .ast_utils import extract_all_exports, is_init_file
from .models import (
    AnalysisResult,
    CodeIssue,
    CodeLocation,
    CodeMetrics,
    IssueType,
    OptimizationOpportunity,
    OptimizationType,
    Severity,
)
from .similarity_utils import SimilarityCalculator, SimilarityMethod


class CodeAnalyzer:
    """Analyzes Python source code for quality issues and optimization opportunities."""

    def __init__(self):
        self.ai_language_patterns = self._load_ai_language_patterns()
        self.import_patterns = re.compile(
            r"^(from\s+\S+\s+)?import\s+(.+)$", re.MULTILINE
        )

    def _load_ai_language_patterns(self) -> List[str]:
        """Load patterns that indicate AI-generated language."""
        return [
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
        ]

    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze a single Python file for quality issues."""
        path = Path(file_path)
        if not path.exists() or not path.suffix == ".py":
            raise ValueError(f"Invalid Python file: {file_path}")

        with open(path, encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            # Return minimal result for files with syntax errors
            return AnalysisResult(
                file_path=file_path,
                issues=[
                    CodeIssue(
                        issue_type=IssueType.DEAD_CODE,
                        location=CodeLocation(file_path, e.lineno or 1),
                        description=f"Syntax error: {e.msg}",
                        severity=Severity.CRITICAL,
                    )
                ],
                refactoring_opportunities=[],
                metrics=CodeMetrics(0, 0, 0, 0, 0, 0),
            )

        issues = []
        opportunities = []

        # Detect AI language patterns
        ai_issues = self._detect_ai_language(content, file_path)
        issues.extend(ai_issues)

        # Detect import issues
        import_issues = self._analyze_imports(tree, content, file_path)
        issues.extend(import_issues)

        # Detect code duplication within file
        duplication_issues = self._detect_internal_duplication(tree, file_path)
        issues.extend(duplication_issues)

        # Detect complex functions that need refactoring
        complexity_issues = self._detect_complex_functions(tree, file_path)
        issues.extend(complexity_issues)

        # Detect missing docstrings
        docstring_issues = self._detect_missing_docstrings(tree, file_path)
        issues.extend(docstring_issues)

        # Detect potential security issues
        security_issues = self._detect_security_issues(tree, content, file_path)
        issues.extend(security_issues)

        # Detect unnecessary parameter passing and default value inconsistencies
        parameter_issues = self._detect_parameter_issues(tree, file_path)
        issues.extend(parameter_issues)

        # Calculate metrics
        metrics = self._calculate_metrics(tree, content)

        # Generate refactoring opportunities
        opportunities = self._identify_refactoring_opportunities(
            tree, issues, file_path
        )

        return AnalysisResult(
            file_path=file_path,
            issues=issues,
            refactoring_opportunities=opportunities,
            metrics=metrics,
            ai_language_count=len(
                [i for i in issues if i.issue_type == IssueType.AI_LANGUAGE]
            ),
        )

    def scan_directory(
        self, directory: str, exclude_patterns: Optional[List[str]] = None
    ) -> List[AnalysisResult]:
        """Scan all Python files in a directory."""
        if exclude_patterns is None:
            exclude_patterns = ["__pycache__", ".git", ".pytest_cache", "venv", "env"]

        results = []
        directory_path = Path(directory)

        for py_file in directory_path.rglob("*.py"):
            # Skip excluded directories
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue

            try:
                result = self.analyze_file(str(py_file))
                results.append(result)
            except Exception as e:
                # Log error but continue with other files
                print(f"Error analyzing {py_file}: {e}")

        return results

    def _detect_ai_language(self, content: str, file_path: str) -> List[CodeIssue]:
        """Detect AI-generated language patterns in code."""
        issues = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip code lines, focus on comments and docstrings
            stripped = line.strip()
            if not (stripped.startswith("#") or '"""' in line or "'''" in line):
                continue

            for pattern in self.ai_language_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.AI_LANGUAGE,
                            location=CodeLocation(file_path, line_num, match.start()),
                            description=f"AI-generated language detected: '{match.group()}'",
                            severity=Severity.MEDIUM,
                            fix_suggestion="Replace with more specific technical terminology",
                            context=line.strip(),
                        )
                    )

        return issues

    def _analyze_imports(
        self, tree: ast.AST, content: str, file_path: str
    ) -> List[CodeIssue]:
        """Analyze import statements for issues."""
        issues = []
        imports = []
        used_names = set()

        # Collect all imports with their positions
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, alias.asname, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(
                        (f"{module}.{alias.name}", alias.asname, node.lineno)
                    )

        # Check for imports not at the top of the file
        import_location_issues = self._check_import_locations(tree, file_path)
        issues.extend(import_location_issues)

        # Collect all name usage
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle attribute access like module.function
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Special handling for __init__.py files: check __all__ list
        all_exports = set()
        init_file = is_init_file(file_path)

        if init_file:
            all_exports = extract_all_exports(tree)

        # Check for unused imports
        for import_name, alias, line_num in imports:
            name_to_check = alias if alias else import_name.split(".")[-1]

            # Skip unused import check if this is an __init__.py file and the import is in __all__
            if init_file and name_to_check in all_exports:
                continue

            # Skip nx-parallel import check - it's necessary for NetworkX parallelization even if not directly used
            if import_name == "nx_parallel" or name_to_check == "nx_parallel":
                continue

            if name_to_check not in used_names:
                issues.append(
                    CodeIssue(
                        issue_type=IssueType.IMPORT_ISSUES,
                        location=CodeLocation(file_path, line_num),
                        description=f"Unused import: {import_name}",
                        severity=Severity.LOW,
                        fix_suggestion="Remove unused import",
                    )
                )

        return issues

    def _check_import_locations(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """Check for imports that are not at the top of the file."""
        issues = []

        # First, check for nested imports (imports inside functions, classes, etc.)
        nested_import_issues = self._detect_nested_imports(tree, file_path)
        issues.extend(nested_import_issues)

        # Then check top-level import ordering
        top_level_issues = self._check_top_level_import_order(tree, file_path)
        issues.extend(top_level_issues)

        return issues

    def _detect_nested_imports(self, tree: ast.AST, file_path: str) -> List[CodeIssue]:
        """Detect imports that are nested inside functions, classes, or other blocks."""
        issues = []

        # Get all top-level import nodes for comparison
        top_level_imports = set()
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                top_level_imports.add(id(node))

        # Find all imports in the entire tree
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Skip if this is a top-level import
                if id(node) in top_level_imports:
                    continue

                # Skip __future__ imports (they're allowed to be nested in some cases)
                if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                    continue

                # Skip nx-parallel imports in try blocks (legitimate pattern for optional imports)
                import_names = []
                if isinstance(node, ast.Import):
                    import_names = [alias.name for alias in node.names]
                    # Check if this is nx_parallel in a try block
                    if any("nx_parallel" in name for name in import_names):
                        context = self._get_import_context(tree, node)
                        if "try block" in context:
                            continue
                else:
                    module = node.module or ""
                    import_names = [
                        f"{module}.{alias.name}" if alias.name != "*" else f"{module}.*"
                        for alias in node.names
                    ]
                    # Check if this is nx_parallel in a try block
                    if any("nx_parallel" in name for name in import_names):
                        context = self._get_import_context(tree, node)
                        if "try block" in context:
                            continue

                # Determine the context (function, class, etc.)
                context = self._get_import_context(tree, node)

                issues.append(
                    CodeIssue(
                        issue_type=IssueType.IMPORT_ISSUES,
                        location=CodeLocation(file_path, node.lineno),
                        description=f"Nested import detected {context}: {', '.join(import_names)}",
                        severity=Severity.HIGH,  # High priority as requested
                        fix_suggestion="Move import to top of file for better performance and clarity",
                        context=f"Import found {context}",
                    )
                )

        return issues

    def _get_import_context(self, tree: ast.AST, import_node: ast.AST) -> str:
        """Determine the context where a nested import is located."""
        # Walk through all nodes to find the parent context
        for node in ast.walk(tree):
            if hasattr(node, "body") and import_node in ast.walk(node):
                if isinstance(node, ast.FunctionDef):
                    return f"inside function '{node.name}'"
                elif isinstance(node, ast.AsyncFunctionDef):
                    return f"inside async function '{node.name}'"
                elif isinstance(node, ast.ClassDef):
                    return f"inside class '{node.name}'"
                elif isinstance(node, ast.If):
                    return "inside if statement"
                elif isinstance(node, ast.For):
                    return "inside for loop"
                elif isinstance(node, ast.While):
                    return "inside while loop"
                elif isinstance(node, ast.Try):
                    return "inside try block"
                elif isinstance(node, ast.With):
                    return "inside with statement"

        return "in nested block"

    def _check_top_level_import_order(
        self, tree: ast.AST, file_path: str
    ) -> List[CodeIssue]:
        """Check the ordering of top-level imports."""
        issues = []

        # Get all top-level statements in order
        top_level_statements = tree.body

        # Track when we've seen non-import statements
        seen_non_import = False
        seen_non_import_line = None

        for node in top_level_statements:
            # Skip module docstrings and __future__ imports at the beginning
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                # This is likely a module docstring, skip it
                continue
            elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
                # __future__ imports are allowed at the top
                continue
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                # This is an import statement
                if seen_non_import:
                    # We've seen non-import statements before this import
                    import_names = []
                    if isinstance(node, ast.Import):
                        import_names = [alias.name for alias in node.names]
                    else:
                        module = node.module or ""
                        import_names = [
                            f"{module}.{alias.name}" for alias in node.names
                        ]

                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.IMPORT_ISSUES,
                            location=CodeLocation(file_path, node.lineno),
                            description=f"Import statement not at top of file: {', '.join(import_names)}",
                            severity=Severity.MEDIUM,
                            fix_suggestion=f"Move import to top of file (after line {seen_non_import_line})",
                            context=f"Non-import statement found at line {seen_non_import_line}",
                        )
                    )
            else:
                # This is a non-import statement
                if not seen_non_import:
                    seen_non_import = True
                    seen_non_import_line = node.lineno

        return issues

    def _detect_internal_duplication(
        self, tree: ast.AST, file_path: str
    ) -> List[CodeIssue]:
        """Detect code duplication within a single file."""
        issues = []
        function_bodies = []

        # Collect function bodies for comparison
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                body_code = ast.dump(node)
                function_bodies.append((node.name, body_code, node.lineno))

        # Simple duplication detection based on AST similarity
        for i, (name1, body1, line1) in enumerate(function_bodies):
            for name2, body2, _line2 in function_bodies[i + 1 :]:
                similarity = self._calculate_similarity(body1, body2)
                if similarity > 0.8:  # 80% similarity threshold
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.DUPLICATION,
                            location=CodeLocation(file_path, line1),
                            description=f"Similar function detected: {name1} and {name2}",
                            severity=Severity.MEDIUM,
                            fix_suggestion="Consider extracting common functionality",
                        )
                    )

        return issues

    def _calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code blocks."""
        return SimilarityCalculator.calculate_similarity(
            code1, code2, SimilarityMethod.CHARACTER_BASED
        )

    def _calculate_metrics(self, tree: ast.AST, content: str) -> CodeMetrics:
        """Calculate code quality metrics."""
        lines = content.split("\n")
        loc = len(
            [
                line
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
        )

        function_count = len(
            [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        )
        class_count = len(
            [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        )
        import_count = len(
            [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
            ]
        )

        # Simple complexity calculation based on control flow nodes
        complexity_nodes = [
            ast.If,
            ast.For,
            ast.While,
            ast.Try,
            ast.With,
            ast.FunctionDef,
            ast.ClassDef,
        ]
        complexity = len(
            [
                node
                for node in ast.walk(tree)
                if any(isinstance(node, cls) for cls in complexity_nodes)
            ]
        )

        return CodeMetrics(
            lines_of_code=loc,
            complexity_score=complexity,
            duplication_percentage=0.0,  # Will be calculated across files
            import_count=import_count,
            function_count=function_count,
            class_count=class_count,
        )

    def _identify_refactoring_opportunities(
        self, tree: ast.AST, issues: List[CodeIssue], file_path: str
    ) -> List[OptimizationOpportunity]:
        """Identify refactoring opportunities based on detected issues."""
        opportunities = []

        # Group issues by type to identify patterns
        issue_groups = defaultdict(list)
        for issue in issues:
            issue_groups[issue.issue_type].append(issue)

        # Suggest extracting utilities if there's duplication
        if IssueType.DUPLICATION in issue_groups:
            opportunities.append(
                OptimizationOpportunity(
                    opportunity_type=OptimizationType.EXTRACT_UTILITY,
                    impact_level="Medium",
                    effort_required="Medium",
                    description="Extract common functionality into utility functions",
                    implementation_plan=[
                        "Identify common code patterns",
                        "Create utility functions",
                        "Replace duplicate code with utility calls",
                    ],
                    affected_files=[file_path],
                )
            )

        # Suggest import cleanup if there are import issues
        if IssueType.IMPORT_ISSUES in issue_groups:
            opportunities.append(
                OptimizationOpportunity(
                    opportunity_type=OptimizationType.STANDARDIZE_IMPORTS,
                    impact_level="Low",
                    effort_required="Low",
                    description="Clean up and organize import statements",
                    implementation_plan=[
                        "Remove unused imports",
                        "Organize imports according to PEP 8",
                        "Group related imports",
                    ],
                    affected_files=[file_path],
                )
            )

        return opportunities

    def _detect_complex_functions(
        self, tree: ast.AST, file_path: str
    ) -> List[CodeIssue]:
        """Detect functions with high cyclomatic complexity."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)

                if complexity > 5:  # Lower threshold for testing
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.DEAD_CODE,  # Using existing enum value
                            location=CodeLocation(file_path, node.lineno),
                            description=f"Function '{node.name}' has high cyclomatic complexity: {complexity}",
                            severity=(
                                Severity.MEDIUM if complexity <= 10 else Severity.HIGH
                            ),
                            fix_suggestion="Consider breaking this function into smaller, more focused functions",
                            context=f"Complexity score: {complexity}/5 (recommended maximum)",
                        )
                    )

        return issues

    def _calculate_cyclomatic_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity

        for node in ast.walk(func_node):
            # Count decision points
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += 1
                # Add complexity for each except handler
                complexity += len(node.handlers)
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # And/Or operations add complexity
                complexity += len(node.values) - 1

        return complexity

    def _detect_missing_docstrings(
        self, tree: ast.AST, file_path: str
    ) -> List[CodeIssue]:
        """Detect functions and classes missing docstrings."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                # Skip private methods (starting with _) for docstring requirements
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue

                has_docstring = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )

                if not has_docstring:
                    node_type = (
                        "Class" if isinstance(node, ast.ClassDef) else "Function"
                    )
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.DEAD_CODE,  # Using existing enum value
                            location=CodeLocation(file_path, node.lineno),
                            description=f"{node_type} '{node.name}' is missing a docstring",
                            severity=Severity.LOW,
                            fix_suggestion=f"Add a docstring describing the {node_type.lower()}'s purpose and parameters",
                            context=f"Public {node_type.lower()} without documentation",
                        )
                    )

        return issues

    def _detect_security_issues(
        self, tree: ast.AST, content: str, file_path: str
    ) -> List[CodeIssue]:
        """Detect potential security issues in code."""
        issues = []

        # Check for dangerous function calls
        dangerous_functions = {
            "eval": "Use of eval() can execute arbitrary code",
            "exec": "Use of exec() can execute arbitrary code",
            "compile": "Use of compile() with user input can be dangerous",
            "__import__": "Dynamic imports can be security risks",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None

                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in dangerous_functions:
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.ERROR_HANDLING,  # Using existing enum value
                            location=CodeLocation(file_path, node.lineno),
                            description=f"Potential security risk: {dangerous_functions[func_name]}",
                            severity=Severity.HIGH,
                            fix_suggestion="Consider safer alternatives or add proper input validation",
                            context=f"Call to {func_name}()",
                        )
                    )

        # Check for hardcoded secrets (simple patterns)
        lines = content.split("\n")
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token detected"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, message in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        CodeIssue(
                            issue_type=IssueType.ERROR_HANDLING,  # Using existing enum value
                            location=CodeLocation(file_path, line_num),
                            description=message,
                            severity=Severity.HIGH,
                            fix_suggestion="Move sensitive data to environment variables or configuration files",
                            context=line.strip(),
                        )
                    )

        return issues

    def _detect_parameter_issues(
        self, tree: ast.AST, file_path: str
    ) -> List[CodeIssue]:
        """Detect unnecessary parameter passing and default value inconsistencies."""
        issues = []

        # Collect function definitions with their parameters
        function_signatures = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract parameter information
                params = []
                defaults = []

                # Get regular arguments
                for arg in node.args.args:
                    params.append(arg.arg)

                # Get default values
                if node.args.defaults:
                    defaults = node.args.defaults

                # Map parameters to their defaults
                param_defaults = {}
                if defaults:
                    # Defaults apply to the last N parameters
                    default_start = len(params) - len(defaults)
                    for i, default in enumerate(defaults):
                        param_name = params[default_start + i]
                        if isinstance(default, ast.Constant):
                            param_defaults[param_name] = default.value
                        elif isinstance(default, ast.NameConstant):
                            param_defaults[param_name] = default.value
                        elif isinstance(default, ast.Name) and default.id == "None":
                            param_defaults[param_name] = None

                function_signatures[node.name] = {
                    "params": params,
                    "defaults": param_defaults,
                    "line": node.lineno,
                }

        # Check function calls for unnecessary parameter passing
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None

                # Get function name
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name and func_name in function_signatures:
                    sig = function_signatures[func_name]

                    # Check for parameters passed with their default values
                    for i, arg in enumerate(node.args):
                        if i < len(sig["params"]):
                            param_name = sig["params"][i]
                            if param_name in sig["defaults"]:
                                default_value = sig["defaults"][param_name]

                                # Check if argument matches default value
                                arg_value = None
                                if isinstance(arg, ast.Constant):
                                    arg_value = arg.value
                                elif isinstance(arg, ast.NameConstant):
                                    arg_value = arg.value
                                elif isinstance(arg, ast.Name) and arg.id == "None":
                                    arg_value = None

                                if arg_value == default_value:
                                    issues.append(
                                        CodeIssue(
                                            issue_type=IssueType.DEAD_CODE,
                                            location=CodeLocation(
                                                file_path, node.lineno
                                            ),
                                            description=f"Unnecessary parameter '{param_name}' passed with default value",
                                            severity=Severity.LOW,
                                            fix_suggestion=f"Remove parameter '{param_name}' as it matches the default value",
                                            context=f"Function call to {func_name}",
                                        )
                                    )

                    # Check keyword arguments for default values
                    for keyword in node.keywords:
                        if keyword.arg in sig["defaults"]:
                            default_value = sig["defaults"][keyword.arg]

                            # Check if keyword argument matches default value
                            arg_value = None
                            if isinstance(keyword.value, ast.Constant):
                                arg_value = keyword.value.value
                            elif isinstance(keyword.value, ast.NameConstant):
                                arg_value = keyword.value.value
                            elif (
                                isinstance(keyword.value, ast.Name)
                                and keyword.value.id == "None"
                            ):
                                arg_value = None

                            if arg_value == default_value:
                                issues.append(
                                    CodeIssue(
                                        issue_type=IssueType.DEAD_CODE,
                                        location=CodeLocation(file_path, node.lineno),
                                        description=f"Unnecessary keyword argument '{keyword.arg}' passed with default value",
                                        severity=Severity.LOW,
                                        fix_suggestion=f"Remove keyword argument '{keyword.arg}' as it matches the default value",
                                        context=f"Function call to {func_name}",
                                    )
                                )

        # Check for default value inconsistencies in dataclasses and similar patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Look for dataclass or similar patterns
                has_dataclass_decorator = any(
                    (isinstance(decorator, ast.Name) and decorator.id == "dataclass")
                    or (
                        isinstance(decorator, ast.Attribute)
                        and decorator.attr == "dataclass"
                    )
                    for decorator in node.decorator_list
                )

                if has_dataclass_decorator:
                    # Check field definitions for inconsistent defaults
                    field_defaults = {}
                    for class_node in node.body:
                        if isinstance(class_node, ast.AnnAssign) and class_node.value:
                            field_name = (
                                class_node.target.id
                                if isinstance(class_node.target, ast.Name)
                                else None
                            )
                            if field_name:
                                if isinstance(class_node.value, ast.Constant):
                                    field_defaults[field_name] = class_node.value.value
                                elif (
                                    isinstance(class_node.value, ast.Name)
                                    and class_node.value.id == "None"
                                ):
                                    field_defaults[field_name] = None

                    # Look for constructor calls that might be inconsistent
                    # This is a simplified check - could be expanded
                    for field_name, default_value in field_defaults.items():
                        if default_value is None:
                            # Check if this field is being passed explicitly as None elsewhere
                            for call_node in ast.walk(tree):
                                if isinstance(call_node, ast.Call):
                                    for keyword in call_node.keywords:
                                        if (
                                            keyword.arg == field_name
                                            and isinstance(keyword.value, ast.Name)
                                            and keyword.value.id == "None"
                                        ):
                                            issues.append(
                                                CodeIssue(
                                                    issue_type=IssueType.DEAD_CODE,
                                                    location=CodeLocation(
                                                        file_path, call_node.lineno
                                                    ),
                                                    description=f"Unnecessary explicit None for field '{field_name}' with None default",
                                                    severity=Severity.LOW,
                                                    fix_suggestion=f"Remove explicit None for '{field_name}' parameter",
                                                    context=f"Constructor call for {node.name}",
                                                )
                                            )

        return issues
