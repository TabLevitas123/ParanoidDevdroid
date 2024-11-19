# tests/master_test_runner.py

import asyncio
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from tests.advanced_test_cases import run_advanced_tests
from tests.api_endpoint_tests import run_api_tests
from tests.transaction_tests import run_transaction_tests
from utils.logger import CustomLogger

logger = CustomLogger("master_test_runner", "master_tests.log")

class TestSuite:
    def __init__(self, name: str, runner):
        self.name = name
        self.runner = runner
        self.results = None
        self.execution_time = 0
        self.status = "NOT_RUN"
        self.error = None

class MasterTestRunner:
    """Master test runner that executes all test suites"""
    
    def __init__(self):
        self.test_suites = [
            TestSuite("Advanced Tests", run_advanced_tests),
            TestSuite("API Endpoint Tests", run_api_tests),
            TestSuite("Transaction Tests", run_transaction_tests)
        ]
        self.start_time = None
        self.end_time = None
        
        # Create test directories
        self._create_test_directories()

    def _create_test_directories(self):
        """Create necessary test directories"""
        directories = [
            'test/db',
            'test/logs',
            'test/reports',
            'test/data'
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    async def setup(self):
        """Setup test environment"""
        try:
            logger.info("Setting up test environment...")
            
            # Create test report directory
            report_dir = Path("test/reports")
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Additional setup if needed
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Test environment setup failed: {str(e)}")
            return False

    async def run_all_tests(self):
        """Run all test suites"""
        self.start_time = datetime.now()
        logger.info(f"Starting test run at {self.start_time}")
        
        total_tests = len(self.test_suites)
        completed_tests = 0
        
        for suite in self.test_suites:
            try:
                logger.info(f"\nRunning {suite.name}...")
                print(f"\n{'='*20} Running {suite.name} {'='*20}")
                
                suite_start = time.time()
                suite.results = await suite.runner()
                suite.execution_time = time.time() - suite_start
                
                if suite.results:
                    suite.status = "PASSED"
                    logger.info(f"{suite.name} completed successfully")
                else:
                    suite.status = "FAILED"
                    logger.error(f"{suite.name} failed")
                
            except Exception as e:
                suite.status = "ERROR"
                suite.error = str(e)
                logger.error(f"{suite.name} encountered an error: {str(e)}")
            
            completed_tests += 1
            self._print_progress(completed_tests, total_tests)

        self.end_time = datetime.now()
        await self._generate_report()

    def _print_progress(self, completed: int, total: int):
        """Print test progress"""
        percentage = (completed / total) * 100
        bar_length = 50
        filled_length = int(bar_length * completed // total)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        print(f'\rProgress: [{bar}] {percentage:.1f}% ({completed}/{total} suites)', end='')
        if completed == total:
            print()

    async def _generate_report(self):
        """Generate test report"""
        report_file = Path("test/reports") / f"test_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w') as f:
            f.write("Test Execution Report\n")
            f.write("===================\n\n")
            
            f.write(f"Start Time: {self.start_time}\n")
            f.write(f"End Time: {self.end_time}\n")
            f.write(f"Duration: {self.end_time - self.start_time}\n\n")
            
            f.write("Test Suite Results\n")
            f.write("-----------------\n")
            
            for suite in self.test_suites:
                f.write(f"\n{suite.name}:\n")
                f.write(f"Status: {suite.status}\n")
                f.write(f"Execution Time: {suite.execution_time:.2f} seconds\n")
                
                if suite.error:
                    f.write(f"Error: {suite.error}\n")
                
                if isinstance(suite.results, dict):
                    for key, value in suite.results.items():
                        f.write(f"{key}: {value}\n")
            
            f.write("\nSummary\n")
            f.write("-------\n")
            passed = sum(1 for suite in self.test_suites if suite.status == "PASSED")
            failed = sum(1 for suite in self.test_suites if suite.status in ["FAILED", "ERROR"])
            f.write(f"Total Suites: {len(self.test_suites)}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
        
        logger.info(f"Test report generated: {report_file}")
        return report_file

    def print_summary(self):
        """Print test execution summary"""
        print("\nTest Execution Summary")
        print("=====================")
        print(f"Start Time: {self.start_time}")
        print(f"End Time: {self.end_time}")
        print(f"Duration: {self.end_time - self.start_time}\n")
        
        passed_suites = []
        failed_suites = []
        
        for suite in self.test_suites:
            if suite.status == "PASSED":
                passed_suites.append(suite.name)
            else:
                failed_suites.append((suite.name, suite.status, suite.error))
        
        print("Passed Test Suites:")
        for suite_name in passed_suites:
            print(f"✓ {suite_name}")
        
        if failed_suites:
            print("\nFailed Test Suites:")
            for suite_name, status, error in failed_suites:
                print(f"✗ {suite_name} ({status})")
                if error:
                    print(f"  Error: {error}")
        
        print(f"\nTotal Suites: {len(self.test_suites)}")
        print(f"Passed: {len(passed_suites)}")
        print(f"Failed: {len(failed_suites)}")

async def main():
    """Main execution function"""
    runner = MasterTestRunner()
    
    try:
        # Setup
        if not await runner.setup():
            logger.error("Test setup failed")
            return 1
        
        # Run tests
        await runner.run_all_tests()
        
        # Print summary
        runner.print_summary()
        
        # Determine exit code
        failed_suites = sum(
            1 for suite in runner.test_suites 
            if suite.status in ["FAILED", "ERROR"]
        )
        
        return 1 if failed_suites > 0 else 0
        
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
