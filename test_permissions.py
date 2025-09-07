import os
import tempfile
import shutil

def test_permissions():
    print("Testing file permissions...")
    
    # Test 1: Create and delete a temporary directory
    try:
        temp_dir = tempfile.mkdtemp()
        print(f"Created temp dir: {temp_dir}")
        os.rmdir(temp_dir)
        print("Deleted temp dir successfully")
    except Exception as e:
        print(f"Failed to create/delete temp dir: {e}")
        return False
    
    # Test 2: Create and delete a file in the results directory
    try:
        test_file = 'tests/results/test_permission_check.txt'
        with open(test_file, 'w') as f:
            f.write('test')
        print(f"Created test file: {test_file}")
        os.remove(test_file)
        print("Deleted test file successfully")
    except Exception as e:
        print(f"Failed to create/delete test file: {e}")
        return False
    
    # Test 3: Check if we can write to the current directory
    try:
        test_file = 'test_current_dir.txt'
        with open(test_file, 'w') as f:
            f.write('test')
        print(f"Created test file in current dir: {test_file}")
        os.remove(test_file)
        print("Deleted test file from current dir successfully")
    except Exception as e:
        print(f"Failed to create/delete test file in current dir: {e}")
        return False
    
    print("All permission tests passed!")
    return True

if __name__ == "__main__":
    test_permissions()