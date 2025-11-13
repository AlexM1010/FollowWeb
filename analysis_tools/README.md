# Code Quality Analysis Tools

This package analyzes Python codebases to detect quality issues, AI-generated language artifacts, test redundancies, and improvement opportunities.

## Components

### 1. CodeAnalyzer (`code_analyzer.py`)
Analyzes Python source code for quality issues and improvement opportunities.

**Features:**
- AI language pattern detection in comments and docstrings
- Import analysis (unused and redundant imports)
- Code duplication detection within files
- Code quality metrics calculation
- NetworkX parallelization detection (nx-parallel import analysis)

**Usage:**
```python
from analysis_tools import CodeAnalyzer

analyzer = CodeAnalyzer()
result = analyzer.analyze_file('path/to/file.py')
print(f"Found {len(result.issues)} issues")
```

### 2. PatternDetector (`pattern_detector.py`)
Detects AI language artifacts and code patterns.

**Features:**
- Detection of overused AI adjectives (comprehensive, robust, enhanced, etc.)
- Marketing phrase identification
- Generic error message detection
- Redundant validation pattern recognition

**Usage:**
```python
from analysis_tools import PatternDetector

detector = PatternDetector()
issues = detector.detect_ai_language_in_text(text, file_path)
```

### 3. TestAnalyzer (`test_analyzer.py`)
Analyzes test files for duplicates and redundancies.

**Features:**
- Duplicate test detection within and across files
- Unused fixture identification
- Redundant import detection in test files
- Test similarity scoring and consolidation recommendations

**Usage:**
```python
from analysis_tools import TestAnalyzer

analyzer = TestAnalyzer()
result = analyzer.analyze_test_file('tests/test_example.py')
print(f"Found {len(result.duplicate_tests)} duplicate test groups")
```

### 4. AILanguageScanner (`ai_language_scanner.py`)
Specialized scanner for AI-generated language patterns and artifacts.

**Features:**
- Detection of AI-generated marketing phrases and buzzwords
- Identification of generic error messages and placeholder text
- Severity-based classification of language issues
- Comprehensive pattern matching with configurable rules

**Usage:**
```python
from analysis_tools.ai_language_scanner import AILanguageScanner

scanner = AILanguageScanner()
report = scanner.scan_file('path/to/file.py')
print(f"Found {report.total_matches} AI language patterns")
```

### 5. DuplicationDetector (`duplication_detector.py`)
Advanced code duplication detection and analysis.

**Features:**
- Validation pattern duplication detection
- Import redundancy analysis
- Code block similarity assessment
- Consolidation recommendations with impact analysis

**Usage:**
```python
from analysis_tools.duplication_detector import DuplicationDetector

detector = DuplicationDetector()
report = detector.analyze_file('path/to/file.py')
print(f"Found {len(report.duplicate_blocks)} duplicate code blocks")
```

### 6. CrossPlatformAnalyzer (`cross_platform_analyzer.py`)
Cross-platform compatibility analysis for test suites.

**Features:**
- Platform-specific code detection
- Path handling compatibility analysis
- Temporary file usage assessment
- CI/CD compatibility scoring

**Usage:**
```python
from analysis_tools.cross_platform_analyzer import CrossPlatformAnalyzer

analyzer = CrossPlatformAnalyzer()
report = analyzer.analyze_file('tests/test_example.py')
print(f"CI compatibility score: {report.ci_compatibility_score}/100")
```

### 7. AnalysisOrchestrator (`analyzer.py`)
Coordinates all analysis tools for comprehensive project assessment.

**Features:**
- Full project analysis with detailed reporting
- Optimization analysis for code quality improvements
- AI language pattern detection and cleanup recommendations
- Code duplication identification and consolidation opportunities
- Cross-platform compatibility analysis
- Environment validation for cleanup processes

**Usage:**
```python
from analysis_tools.analyzer import AnalysisOrchestrator

orchestrator = AnalysisOrchestrator()

# Run comprehensive analysis
report = orchestrator.run_full_analysis()

# Run optimization-focused analysis
optimization_report = orchestrator.run_optimization_analysis()

# Validate cleanup environment
validation_result = orchestrator.validate_cleanup_environment()
```

## Data Models (`models.py`)

The package includes data models for representing analysis results:

- `AnalysisResult`: Analysis result for source files
- `TestAnalysisResult`: Analysis result for test files
- `CodeIssue`: Individual code quality issues
- `OptimizationOpportunity`: Identified improvement opportunities
- `DuplicateTestGroup`: Groups of similar/duplicate tests

## Command Line Interface

Use the CLI for comprehensive analysis:

```bash
# Run full project analysis
python -m analysis_tools

# Run optimization analysis
python -m analysis_tools --optimize

# Validate cleanup environment
python -m analysis_tools --validate-cleanup

# Validate specific cleanup phase
python -m analysis_tools --validate-phase dependencies

# Specify custom project root
python -m analysis_tools --project-root /path/to/project
```

## Installation Requirements

The analysis tools require Python 3.8+ and have minimal dependencies:
- Standard library modules only (ast, re, pathlib, etc.)
- No external dependencies required for core analysis functionality

### NetworkX Parallelization Support

When analyzing projects that use NetworkX (such as FollowWeb):
- **nx-parallel must be imported** for NetworkX parallelization to work
- nx-parallel enables parallel processing backends even when not directly used
- Without the nx-parallel import, NetworkX algorithms run single-threaded
- The analysis tools detect and report on nx-parallel integration

## Testing

Run the test suite to verify functionality:

```bash
python test_analysis_tools.py
```

## Integration with Code Quality Workflow

These tools support a comprehensive code quality workflow:

1. **Analysis Phase**: Identify issues, patterns, and optimization opportunities
2. **Planning Phase**: Generate prioritized improvement recommendations  
3. **Optimization Phase**: Focus on AI language cleanup, deduplication, and compatibility
4. **Validation Phase**: Verify improvements and environment readiness
5. **Cleanup Phase**: Execute safe refactoring with validation checkpoints

### NetworkX Performance Detection

The analysis tools include detection for NetworkX performance opportunities:

- **Missing nx-parallel Import**: Detects NetworkX usage without nx-parallel import
- **Parallelization Opportunities**: Identifies algorithms that could benefit from parallel processing
- **Performance Recommendations**: Suggests nx-parallel integration for NetworkX-heavy codebases
- **Backend Configuration**: Analyzes parallel backend availability and configuration

**Key Finding**: nx-parallel must be imported (even if not directly used) to enable NetworkX's parallel processing backends. The analysis tools flag NetworkX projects missing this import.

## Output and Reporting

Analysis results are saved to the `analysis_reports/` directory in JSON format, containing:

- Executive summary with key metrics
- Issue breakdowns by type and severity
- Improvement recommendations with priority and impact
- File-by-file analysis results
- Test suite analysis and efficiency metrics

## Safety Features

- Non-destructive analysis (read-only operations)
- Error handling and logging

## Extensibility

The modular design allows for easy extension:

- Add new pattern detectors
- Implement additional analysis algorithms
- Extend data models for new issue types
- Customize reporting formats
- Integrate with CI/CD pipelines