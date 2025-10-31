@echo off
REM Windows batch file for running FollowWeb tests using the consolidated test runner

setlocal enabledelayedexpansion

REM Change to parent directory to run tests from project root
cd /d "%~dp0\.."

REM Parse command line arguments
set COMMAND=%1

if "%COMMAND%"=="" (
    echo FollowWeb Test Runner
    echo Usage: test.bat ^<command^> [additional arguments]
    echo.
    echo Available commands:
    echo   all                      - Run all tests with optimal parallelization
    echo   unit                     - Run unit tests only
    echo   integration              - Run integration tests only
    echo   performance              - Run performance tests only ^(sequential^)
    echo   benchmark                - Run benchmark tests ^(sequential^)
    echo   sequential               - Run all tests sequentially
    echo   debug                    - Run tests with debug output
    echo   system-info              - Show system resources and worker counts
    echo   help                     - Show this help message
    echo.
    echo Examples:
    echo   test.bat unit
    echo   test.bat benchmark
    echo   test.bat all --collect-only
    echo   test.bat integration -k test_pipeline
    goto :eof
)

if "%COMMAND%"=="help" (
    python tests\run_tests.py
    goto :eof
)

REM Pass all arguments to the Python test runner
python tests\run_tests.py %*