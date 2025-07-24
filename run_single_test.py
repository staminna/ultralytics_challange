#!/usr/bin/env python3
"""
Simple test runner for individual test files with timeout.
"""

import subprocess
import sys
import os

def run_test_with_timeout(test_file, timeout=30):
    """Run a single test file with timeout."""
    print(f"🧪 Running {test_file} with {timeout}s timeout...")
    
    try:
        cmd = [
            "python", "-m", "pytest", 
            f"tests/{test_file}",
            "-v",
            "--tb=short"
        ]
        
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        
        result = subprocess.run(
            cmd, 
            timeout=timeout,
            capture_output=True, 
            text=True,
            env=env
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"❌ Test timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python run_single_test.py <test_file.py>")
        print("Example: python run_single_test.py test_coverage_boost.py")
        return 1
    
    test_file = sys.argv[1]
    
    if run_test_with_timeout(test_file, timeout=60):
        print("✅ Test completed successfully")
        return 0
    else:
        print("❌ Test failed or timed out")
        return 1

if __name__ == "__main__":
    sys.exit(main())
