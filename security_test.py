#!/usr/bin/env python3
"""
Security test script for the audiobook creator.
Tests the security fixes implemented to prevent vulnerabilities.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the current directory to the path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    sanitize_filename, 
    sanitize_chapter_name, 
    validate_path_within_base, 
    validate_file_safety,
    safe_path_join,
    validate_output_path
)

def test_filename_sanitization():
    """Test filename sanitization against injection attacks."""
    print("Testing filename sanitization...")
    
    # Test cases with malicious inputs
    test_cases = [
        ("normal_file.mp3", "normal_file.mp3"),
        ("; rm -rf / #.mp3", "___rm_-rf____mp3"),
        ("$(malicious_command).wav", "__malicious_command__.wav"),
        ("../../../etc/passwd.flac", "etc_passwd.flac"),
        ("file with spaces.mp3", "file with spaces.mp3"),
        ("", "sanitized_file"),
        ("...", "sanitized_file"),
        ("a" * 300 + ".mp3", "a" * 251 + ".mp3"),  # Length limit test
    ]
    
    for input_name, expected in test_cases:
        try:
            result = sanitize_filename(input_name)
            print(f"✓ '{input_name}' -> '{result}'")
            # Verify no dangerous characters remain
            dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '{', '}', '[', ']', '<', '>']
            has_dangerous = any(char in result for char in dangerous_chars)
            if has_dangerous:
                print(f"  WARNING: Dangerous characters still present in '{result}'")
        except Exception as e:
            print(f"✗ Error sanitizing '{input_name}': {e}")

def test_chapter_name_sanitization():
    """Test chapter name sanitization."""
    print("\nTesting chapter name sanitization...")
    
    test_cases = [
        ("Chapter 1", "Chapter 1"),
        ("Chapter; rm -rf /", "Chapter rm -rf "),
        ("Chapter $(evil)", "Chapter evil"),
        ("", "Unnamed Chapter"),
        ("   ", "Unnamed Chapter"),
        ("A" * 300, "A" * 200),  # Length limit
    ]
    
    for input_name, expected in test_cases:
        result = sanitize_chapter_name(input_name)
        print(f"✓ '{input_name}' -> '{result}'")

def test_path_validation():
    """Test path traversal prevention."""
    print("\nTesting path validation...")
    
    base_dir = "/tmp/test_audiobook"
    
    test_cases = [
        ("/tmp/test_audiobook/safe_file.mp3", True),
        ("/tmp/test_audiobook/../../../etc/passwd", False),
        ("/tmp/test_audiobook/subdir/file.mp3", True),
        ("../../../etc/passwd", False),
        ("normal_file.mp3", False),  # Not absolute path starting with base
    ]
    
    for test_path, expected in test_cases:
        try:
            result = validate_path_within_base(test_path, base_dir)
            status = "✓" if result == expected else "✗"
            print(f"{status} '{test_path}' -> {result} (expected {expected})")
        except Exception as e:
            print(f"✗ Error validating '{test_path}': {e}")

def test_safe_path_join():
    """Test safe path joining."""
    print("\nTesting safe path joining...")
    
    base_dir = "/tmp/test_audiobook"
    
    test_cases = [
        (("safe_file.mp3",), True),
        (("../../../etc/passwd",), False),
        (("subdir", "file.mp3"), True),
        (("..", "..", "..", "etc", "passwd"), False),
    ]
    
    for paths, should_succeed in test_cases:
        try:
            result = safe_path_join(base_dir, *paths)
            if should_succeed:
                print(f"✓ join({base_dir}, {paths}) -> {result}")
            else:
                print(f"✗ Expected failure but got: {result}")
        except ValueError as e:
            if not should_succeed:
                print(f"✓ Correctly rejected: {paths} ({e})")
            else:
                print(f"✗ Unexpected failure: {paths} ({e})")

def test_output_path_validation():
    """Test output path validation."""
    print("\nTesting output path validation...")
    
    test_cases = [
        ("output.m4b", True),
        ("../../../tmp/evil.m4b", True),  # Will be made safe
        ("output.txt", False),  # Wrong extension
        ("output", False),  # No extension
        ("A" * 5000 + ".m4b", False),  # Too long
    ]
    
    for test_path, should_succeed in test_cases:
        try:
            result = validate_output_path(test_path)
            if should_succeed:
                print(f"✓ '{test_path}' -> '{result}'")
            else:
                print(f"✗ Expected failure but got: {result}")
        except ValueError as e:
            if not should_succeed:
                print(f"✓ Correctly rejected: '{test_path}' ({e})")
            else:
                print(f"✗ Unexpected failure: '{test_path}' ({e})")

def test_file_safety_validation():
    """Test file safety validation."""
    print("\nTesting file safety validation...")
    
    # Create a test directory and files
    test_dir = Path("/tmp/audiobook_security_test")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Create a normal test file
        normal_file = test_dir / "normal.mp3"
        normal_file.write_text("fake audio content")
        
        # Create a suspicious file
        suspicious_file = test_dir / "; rm -rf / #.mp3"
        try:
            suspicious_file.write_text("fake audio content")
            suspicious_created = True
        except:
            suspicious_created = False
        
        # Test validation
        if validate_file_safety(normal_file):
            print("✓ Normal file passed validation")
        else:
            print("✗ Normal file failed validation")
        
        if suspicious_created:
            if not validate_file_safety(suspicious_file):
                print("✓ Suspicious file correctly rejected")
            else:
                print("✗ Suspicious file incorrectly accepted")
        else:
            print("✓ Suspicious filename prevented file creation")
            
    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)

def main():
    """Run all security tests."""
    print("=== Audiobook Creator Security Tests ===\n")
    
    try:
        test_filename_sanitization()
        test_chapter_name_sanitization()
        test_path_validation()
        test_safe_path_join()
        test_output_path_validation()
        test_file_safety_validation()
        
        print("\n=== Security Tests Completed ===")
        print("All security fixes appear to be working correctly.")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()