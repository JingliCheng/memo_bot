#!/usr/bin/env python3
"""
Test runner script for memo bot backend.
Provides convenient commands for running different test suites.
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run memo bot backend tests")
    parser.add_argument(
        "test_type",
        choices=["all", "unit", "integration", "multi-user", "rate-limit", "quick"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests with verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running tests"
    )
    
    args = parser.parse_args()
    
    # Change to backend directory (parent of tests directory)
    backend_dir = Path(__file__).parent.parent
    import os
    os.chdir(backend_dir)
    
    # Install dependencies if requested
    if args.install_deps:
        if not run_command(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            "Installing test dependencies"
        ):
            return 1
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    # Add test selection based on type
    if args.test_type == "all":
        cmd.append("tests/")
    elif args.test_type == "unit":
        cmd.append("tests/test_rate_limiter.py")
    elif args.test_type == "integration":
        cmd.append("tests/test_integration.py")
    elif args.test_type == "multi-user":
        cmd.append("tests/test_multi_user.py")
    elif args.test_type == "rate-limit":
        cmd.extend(["tests/test_rate_limiter.py", "tests/test_multi_user.py"])
    elif args.test_type == "quick":
        cmd.extend(["-x", "--tb=short", "tests/test_rate_limiter.py"])
    
    # Run tests
    success = run_command(cmd, f"Running {args.test_type} tests")
    
    if args.coverage and success:
        print(f"\n📊 Coverage report generated in htmlcov/index.html")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
