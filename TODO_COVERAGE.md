# Coverage Improvement TODO List

Current: 68% | Target: 70% | Gap: 2%

## Critical Low Coverage Files (Priority Order)

1. **connectivity.py** - 11% coverage (70 statements, 62 missed)
   - Need tests for connectivity analysis functions
   
2. **processors.py** - 21% coverage (56 statements, 44 missed)
   - Need tests for data processing functions

3. **color_palette.py** - 37% coverage (113 statements, 71 missed)
   - Need tests for color palette generation

4. **files.py** - 38% coverage (217 statements, 135 missed)
   - Need tests for file utility functions

5. **incremental_freesound.py** - 40% coverage (789 statements, 475 missed)
   - Large file, but even small improvements help

6. **validation.py** - 43% coverage (133 statements, 76 missed)
   - Need tests for validation functions

7. **metadata_cache.py** - 54% coverage (106 statements, 49 missed)
   - Need tests for metadata caching

8. **rate_limiter.py** - 52% coverage (63 statements, 30 missed)
   - Need tests for rate limiting

## Quick Wins (Small files, big impact)

- **processors.py**: 56 statements total, adding 10 tests could add ~1% coverage
- **connectivity.py**: 70 statements total, adding 15 tests could add ~1% coverage

## Strategy

Focus on quick wins first - small files where a few tests can significantly improve coverage.
Target: Add enough tests to reach 70% (need ~130 more covered statements across all files)
