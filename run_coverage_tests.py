#!/usr/bin/env python3
"""
Script to run coverage tests and generate a coverage report.
"""

import subprocess
import sys
import os

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd or os.getcwd()
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    """Main function to run tests and coverage."""
    print("🚀 Running YOLO Dataset API Coverage Tests")
    print("=" * 50)
    
    # Set the working directory
    project_dir = "/Users/jorgenunes/2026/ultra assesment"
    os.chdir(project_dir)
    
    # Python path
    python_path = "/Users/jorgenunes/miniforge3/envs/dataset-annotation/bin/python"
    
    # Test files to run
    test_files = [
        "tests/test_api.py",
        "tests/test_comprehensive_coverage.py", 
        "tests/test_coverage_boost.py"
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")
        
        cmd = f"{python_path} -m pytest {test_file} -v --tb=short"
        returncode, stdout, stderr = run_command(cmd)
        
        if returncode == 0:
            print(f"✅ {test_file} - ALL TESTS PASSED")
        else:
            print(f"⚠️  {test_file} - SOME TESTS FAILED")
        
        # Parse test results
        lines = stdout.split('\n')
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Extract numbers from line like "2 failed, 14 passed"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed':
                        passed_tests += int(parts[i-1])
                    elif part == 'failed':
                        failed_tests += int(parts[i-1])
            elif 'passed' in line and 'failed' not in line:
                # Extract from line like "16 passed"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed':
                        passed_tests += int(parts[i-1])
        
        print(f"Output preview: {stdout[:200]}...")
    
    total_tests = passed_tests + failed_tests
    
    print(f"\n📊 COVERAGE TEST SUMMARY")
    print("=" * 30)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
    
    # Try to run coverage report
    print(f"\n📈 Attempting to generate coverage report...")
    cmd = f"{python_path} -m pytest --cov=backend --cov-report=term-missing tests/"
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print("✅ Coverage report generated successfully!")
        print(stdout)
    else:
        print("⚠️  Coverage report failed, but tests completed.")
        print(f"Error: {stderr}")
    
    print(f"\n🎯 FINAL STATUS")
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSING! Coverage boost successful!")
        return 0
    else:
        print(f"⚠️  {failed_tests} tests still failing, but significant progress made!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
