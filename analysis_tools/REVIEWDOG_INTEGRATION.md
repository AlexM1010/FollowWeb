# Reviewdog Integration for analysis_tools

This document describes the integration between reviewdog and analysis_tools for automated code review in CI/CD pipelines.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                   │
│                  (.github/workflows/reviewdog.yml)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         reviewdog                            │
│              (CI/CD Orchestrator & Formatter)                │
│  - Diff mode analysis (only changed lines)                  │
│  - SARIF output for GitHub Code Scanning                    │
│  - GitHub Actions annotations for inline PR comments        │
│  - Severity-based build failures                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      analysis_tools                          │
│                  (Code Analysis Engines)                     │
│  - AILanguageScanner: AI language pattern detection          │
│  - DuplicationDetector: Code duplication analysis            │
│  - CrossPlatformAnalyzer: Platform compatibility checks      │
│  - PatternDetector: Generic patterns and validation          │
│  - CodeAnalyzer: Import analysis, code quality metrics       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Output Formats                            │
│  - rdjson: Reviewdog JSON format                            │
│  - SARIF: GitHub Code Scanning format                       │
│  - GitHub Actions: Inline PR annotations                    │
│  - analysis_reports/: Timestamped JSON reports               │
└─────────────────────────────────────────────────────────────┘
```

## Key Principles

1. **reviewdog is an orchestrator, NOT an analyzer**
   - reviewdog calls analysis_tools analyzers
   - reviewdog formats and displays results
   - All analysis logic stays in analysis_tools

2. **analysis_tools performs all code analysis**
   - AILanguageScanner: Unique AI pattern detection
   - DuplicationDetector: Unique code duplication analysis
   - CrossPlatformAnalyzer: Unique platform compatibility checks
   - PatternDetector: Unique pattern detection
   - CodeAnalyzer: Import and code quality analysis

3. **No redundancy**
   - reviewdog does NOT duplicate analysis_tools functionality
   - analysis_tools does NOT duplicate reviewdog functionality
   - Clear separation of concerns

## Usage

### Command Line

Run individual analyzers with reviewdog output:

```bash
# AI Language Scanner
python -m analysis_tools.ai_language_scanner --format=reviewdog --diff-only

# Duplication Detector
python -m analysis_tools.duplication_detector --format=reviewdog --output=report.json

# Cross-Platform Analyzer
python -m analysis_tools.cross_platform_analyzer --format=sarif

# Pattern Detector
python -m analysis_tools.pattern_detector --format=github-actions
```

### GitHub Actions Workflow

The reviewdog workflow (`.github/workflows/reviewdog.yml`) automatically runs on:
- Pull requests to main/develop branches
- Pushes to main/develop branches
- Manual workflow dispatch

### Output Formats

1. **rdjson** (Reviewdog JSON)
   - Native reviewdog format
   - Includes diagnostics, locations, severity, suggestions
   - Used for reviewdog processing

2. **SARIF** (Static Analysis Results Interchange Format)
   - GitHub Code Scanning integration
   - Uploaded to Security tab
   - Persistent security/quality tracking

3. **GitHub Actions Annotations**
   - Inline PR comments
   - File/line/column annotations
   - Immediate developer feedback

## Configuration

### Reviewdog Configuration (`.github/reviewdog.yml`)

```yaml
runner:
  # Standard linters
  ruff:
    cmd: ruff check --output-format=json
    level: error
  
  mypy:
    cmd: mypy --show-column-numbers
    level: error
  
  # analysis_tools analyzers
  ai-language:
    cmd: python -m analysis_tools.ai_language_scanner --format=reviewdog --diff-only
    level: warning
  
  duplication:
    cmd: python -m analysis_tools.duplication_detector --format=reviewdog --diff-only
    level: warning
  
  cross-platform:
    cmd: python -m analysis_tools.cross_platform_analyzer --format=reviewdog --diff-only
    level: warning
  
  patterns:
    cmd: python -m analysis_tools.pattern_detector --format=reviewdog --diff-only
    level: info

filter:
  mode: diff_context  # Only analyze changed lines
  gitignore: true     # Respect .gitignore
  exclude:
    - "*.ipynb"
    - "tests/test_data/*"
    - "docs/*"

fail_on_error: true  # Fail build on error-level issues
```

### Severity Levels

- **error**: Critical issues that fail the build
- **warning**: Important issues that should be addressed
- **info**: Informational findings for awareness

## Integration with analysis_reports/

All reviewdog results are saved to `analysis_reports/` directory:

```
analysis_reports/
├── reviewdog_ai_language_20241113_120000.json
├── reviewdog_duplication_20241113_120001.json
├── reviewdog_cross_platform_20241113_120002.json
├── reviewdog_patterns_20241113_120003.json
└── reviewdog_combined.sarif
```

## Benefits

1. **Automated Code Review**
   - Consistent quality enforcement across all PRs
   - Immediate feedback on code quality issues
   - Reduces manual review burden

2. **GitHub Integration**
   - Inline PR comments on specific lines
   - Security tab integration via SARIF
   - Status checks for PR merging

3. **Diff Mode Analysis**
   - Only analyzes changed lines
   - Faster feedback
   - Focuses on new code

4. **Comprehensive Analysis**
   - Multiple analyzers in one workflow
   - Unique analysis_tools capabilities
   - Standard linters (ruff, mypy)

5. **Persistent Tracking**
   - Results saved to analysis_reports/
   - Historical trend analysis
   - Audit trail for quality improvements

## Troubleshooting

### No issues reported

- Check if files match filter patterns
- Verify analyzers are finding issues locally
- Check reviewdog logs for errors

### SARIF upload fails

- Ensure `security-events: write` permission
- Verify SARIF format is valid
- Check file size limits (10 MB max)

### Inline comments not appearing

- Verify `pull-requests: write` permission
- Check if running on pull request event
- Ensure REVIEWDOG_GITHUB_API_TOKEN is set

## Future Enhancements

1. **Custom Rules**
   - Project-specific analysis rules
   - Team coding standards enforcement

2. **Performance Optimization**
   - Caching of analysis results
   - Incremental analysis

3. **Additional Analyzers**
   - Security-specific analyzers
   - Performance pattern detection
   - Documentation quality checks

## References

- [reviewdog Documentation](https://github.com/reviewdog/reviewdog)
- [SARIF Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
- [analysis_tools Documentation](./README.md)
