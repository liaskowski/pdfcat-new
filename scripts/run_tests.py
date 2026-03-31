"""
Test Runner for Batch Upload Tests

Usage:
    python run_batch_tests.py              # Run all batch tests
    python run_batch_tests.py --stress     # Run stress tests only
    python run_batch_tests.py --unit       # Run unit tests only
    python run_batch_tests.py --coverage   # Run with coverage report
"""

import unittest
import sys
import os
import time

# Add project root to path
# Script is in scripts/ folder, so root is one level up
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def run_tests(suite, verbosity=2):
    """Run test suite and print summary"""
    print("=" * 70)
    print("PDFCAT Test Suite")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=False,
        buffer=True
    )
    
    result = runner.run(suite)
    
    duration = time.time() - start_time
    
    print()
    print("=" * 70)
    print(f"Tests completed in {duration:.2f}s")
    print(f"Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 70)
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


def get_all_tests():
    """Get all tests from tests/ directory"""
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, "tests")
    
    # Recursively discover all tests
    return loader.discover(test_dir, pattern="test_*.py", top_level_dir=project_root)


def get_stress_tests():
    """Get only stress tests"""
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, "tests")
    return loader.discover(test_dir, pattern="*stress*.py", top_level_dir=project_root)


def get_unit_tests():
    """Get only unit tests"""
    loader = unittest.TestLoader()
    test_dir = os.path.join(project_root, "tests", "unit")
    return loader.discover(test_dir, pattern="test_*.py", top_level_dir=project_root)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run pdfCAT tests")
    parser.add_argument(
        "--stress",
        action="store_true",
        help="Run stress tests only"
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    # Select test suite
    if args.stress:
        suite = get_stress_tests()
        print("Running stress tests only...")
    elif args.unit:
        suite = get_unit_tests()
        print("Running unit tests only...")
    elif args.integration:
        loader = unittest.TestLoader()
        test_dir = os.path.join(project_root, "tests", "integration")
        suite = loader.discover(test_dir, pattern="test_*.py", top_level_dir=project_root)
        print("Running integration tests only...")
    else:
        suite = get_all_tests()
        print("Running all tests...")
    
    # Run with coverage if requested
    if args.coverage:
        try:
            import coverage
            cov = coverage.Coverage(
                source=["client", "server"],
                omit=[
                    "*/tests/*",
                    "*/__pycache__/*",
                    "*/vendor/*",
                ]
            )
            cov.start()
            
            success = run_tests(suite, verbosity=1 if args.quiet else 2)
            
            cov.stop()
            cov.save()
            
            print("\n" + "=" * 70)
            print("Coverage Report")
            print("=" * 70)
            cov.report(show_missing=True)
            
            return 0 if success else 1
            
        except ImportError:
            print("Coverage not installed. Install with: pip install coverage")
            return run_tests(suite, verbosity=1 if args.quiet else 2)
    else:
        return 0 if run_tests(suite, verbosity=1 if args.quiet else 2) else 1


if __name__ == "__main__":
    sys.exit(main())
