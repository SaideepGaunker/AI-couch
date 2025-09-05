#!/usr/bin/env python3
"""
Simple wrapper script for database maintenance operations

This script provides easy-to-use commands for common database maintenance tasks.
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a maintenance command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.path.dirname(__file__))
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    if len(sys.argv) < 2:
        print("Database Maintenance Tool")
        print("Usage: python run_maintenance.py <command>")
        print("")
        print("Available commands:")
        print("  quick-check    - Quick performance check and index analysis")
        print("  full-optimize  - Complete database optimization")
        print("  analyze-slow   - Analyze slow queries")
        print("  cleanup        - Clean up old data")
        print("  report         - Generate performance report")
        print("  monitor        - Start query performance monitoring (60 seconds)")
        print("")
        return

    command = sys.argv[1].lower()
    
    if command == "quick-check":
        print("Running quick performance check...")
        success, stdout, stderr = run_command("python database_maintenance.py --analyze-indexes --maintenance-checks")
        
    elif command == "full-optimize":
        print("Running full database optimization...")
        success, stdout, stderr = run_command("python database_maintenance.py --full-maintenance")
        
    elif command == "analyze-slow":
        print("Analyzing slow queries...")
        success, stdout, stderr = run_command("python query_performance_monitor.py --analyze-slow-queries")
        
    elif command == "cleanup":
        print("Cleaning up old data...")
        success, stdout, stderr = run_command("python database_maintenance.py --cleanup-old-data")
        
    elif command == "report":
        print("Generating performance report...")
        success, stdout, stderr = run_command("python database_maintenance.py --generate-report")
        
    elif command == "monitor":
        print("Starting query performance monitoring for 60 seconds...")
        success, stdout, stderr = run_command("python query_performance_monitor.py --monitor --duration 60")
        
    else:
        print(f"Unknown command: {command}")
        print("Use 'python run_maintenance.py' to see available commands")
        return
    
    # Print output
    if stdout:
        print(stdout)
    
    if stderr:
        print("Errors/Warnings:", file=sys.stderr)
        print(stderr, file=sys.stderr)
    
    if success:
        print(f"\n✓ Command '{command}' completed successfully")
    else:
        print(f"\n✗ Command '{command}' failed")
        sys.exit(1)

if __name__ == "__main__":
    main()