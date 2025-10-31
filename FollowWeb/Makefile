# Makefile for FollowWeb development and testing

.PHONY: help install install-dev test test-unit test-integration test-performance test-coverage test-coverage-sequential test-coverage-xml test-fast test-parallel test-sequential test-parallel-debug test-benchmark test-performance-comparison clean lint format type-check docs build dist upload tox tox-parallel

# Default target
help:
	@echo "FollowWeb Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  install-editable Install package in editable mode"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests with optimal parallelization"
	@echo "  test-unit        Run unit tests only (fast, parallel)"
	@echo "  test-integration Run integration tests only (controlled parallelization)"
	@echo "  test-performance Run performance tests only (sequential)"
	@echo "  test-coverage    Run tests with coverage report (parallel)"
	@echo "  test-coverage-sequential Run tests with coverage report (sequential, debugging)"
	@echo "  test-coverage-xml Run tests with coverage report and XML output (parallel)"
	@echo "  test-fast        Run fast tests only (exclude slow)"
	@echo "  test-sequential  Run tests sequentially (debugging)"
	@echo "  test-debug       Run tests with debug output"
	@echo "  test-benchmark   Run pytest-benchmark performance tests"
	@echo "  test-performance-comparison Benchmark parallel vs sequential performance"
	@echo "  system-info      Show system resources and recommended worker counts"
	@echo "  tox              Run tests across all Python versions"
	@echo "  tox-parallel     Run tox tests in parallel"
	@echo "  tox-parallel-tests Run tests with explicit parallel execution"
	@echo "  tox-sequential-tests Run tests sequentially (debugging)"
	@echo "  tox-parallel-debug Run parallel tests with debug output"
	@echo ""
	@echo "Test Runner Features:"
	@echo "  - Automatic resource detection and safe worker allocation"
	@echo "  - Prevents pytest-benchmark + xdist conflicts"
	@echo "  - CI environment optimization"
	@echo "  - Worker isolation for parallel test execution"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with ruff"
	@echo "  type-check       Run type checking with mypy"
	@echo ""
	@echo "Build & Distribution:"
	@echo "  build            Build package distributions"
	@echo "  dist             Create distribution packages"
	@echo "  upload           Upload to PyPI (requires credentials)"
	@echo "  upload-test      Upload to TestPyPI"
	@echo ""
	@echo "Utilities:"
	@echo "  clean            Clean up temporary files"
	@echo "  docs             Generate documentation"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

install-editable:
	pip install -e .

# Testing
# Using the consolidated test runner for better resource management
test:
	python tests/run_tests.py all

test-unit:
	python tests/run_tests.py unit

test-integration:
	python tests/run_tests.py integration

test-performance:
	python tests/run_tests.py performance

test-coverage:
	@echo "Running tests with parallel coverage collection..."
	@# Clean any existing coverage data
	@if exist tests\Output\.coverage del tests\Output\.coverage
	@if exist tests\Output\.coverage.* del tests\Output\.coverage.*
	@# Run tests with parallel coverage using consolidated runner
	python tests/run_tests.py all --cov=FollowWeb_Visualizor --cov-report=
	@# Combine coverage data from all workers
	python -m coverage combine
	@# Generate reports
	python -m coverage report --show-missing
	python -m coverage html
	@echo "Coverage reports generated: tests/Output/htmlcov/index.html"

test-coverage-sequential:
	@echo "Running tests with sequential coverage collection (for debugging)..."
	@if exist tests\Output\.coverage del tests\Output\.coverage
	@if exist tests\Output\.coverage.* del tests\Output\.coverage.*
	python tests/run_tests.py sequential --cov=FollowWeb_Visualizor --cov-report=html --cov-report=term-missing
	@echo "Sequential coverage report generated: tests/Output/htmlcov/index.html"

test-coverage-xml:
	@echo "Running tests with parallel coverage collection and XML output..."
	@if exist tests\Output\.coverage del tests\Output\.coverage
	@if exist tests\Output\.coverage.* del tests\Output\.coverage.*
	python tests/run_tests.py all --cov=FollowWeb_Visualizor --cov-report=
	python -m coverage combine
	python -m coverage xml
	python -m coverage report --show-missing
	@echo "Coverage XML report generated: coverage.xml"

test-fast:
	python tests/run_tests.py all -m "not slow"

test-parallel:
	python tests/run_tests.py all

# Debugging and benchmarking targets
test-debug:
	python tests/run_tests.py debug

system-info:
	python tests/run_tests.py system-info

test-sequential:
	python tests/run_tests.py sequential

test-benchmark:
	python tests/run_tests.py benchmark

test-performance-comparison:
	@echo "Benchmarking parallel vs sequential execution..."
	@echo "=== Sequential Execution ==="
	@time python tests/run_tests.py sequential -m "not benchmark" --tb=no -q
	@echo ""
	@echo "=== Parallel Execution ==="
	@time python tests/run_tests.py all -m "not benchmark" --tb=no -q
	@echo ""
	@echo "Performance comparison complete. Compare execution times above."

# Tox testing
tox:
	tox

tox-parallel:
	tox -p auto

tox-parallel-tests:
	tox -e parallel

tox-sequential-tests:
	tox -e sequential

tox-parallel-debug:
	tox -e parallel-debug

tox-recreate:
	tox -r

tox-list:
	tox -l

# Code Quality
lint:
	ruff check FollowWeb_Visualizor tests
	@echo "Linting complete"

format:
	ruff format FollowWeb_Visualizor tests
	ruff check --fix FollowWeb_Visualizor tests
	@echo "Code formatting complete"

type-check:
	mypy FollowWeb_Visualizor
	@echo "Type checking complete"

# Build & Distribution
build:
	python -m build

dist: clean build
	@echo "Distribution packages created in dist/"

upload: dist
	python -m twine upload dist/*

upload-test: dist
	python -m twine upload --repository testpypi dist/*

# Utilities
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf tests/Output/.coverage*
	rm -rf tests/Output/htmlcov
	rm -rf dist
	rm -rf build
	@echo "Cleanup complete"

clean-test-outputs:
	@echo "Cleaning up old test output files..."
	python analysis_tools/cleanup_test_outputs.py --days 7

clean-test-outputs-dry:
	@echo "Showing what test output files would be cleaned..."
	python analysis_tools/cleanup_test_outputs.py --days 7 --dry-run

docs:
	@echo "Documentation generation not yet implemented"

# Development workflow
dev-setup: install-dev
	@echo "Development environment setup complete"

check: lint type-check test-fast
	@echo "All checks passed"

ci: lint type-check test-coverage
	@echo "CI pipeline complete"