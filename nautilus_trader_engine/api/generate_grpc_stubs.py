#!/usr/bin/env python3
"""
Script to generate Python gRPC stubs from proto files

This script generates the necessary Python files for gRPC communication
from the protocol buffer definitions.

Usage:
    python generate_grpc_stubs.py

Requirements:
    - grpcio-tools
    - protobuf
"""

import os
import subprocess
import sys
from pathlib import Path

def generate_grpc_stubs():
    """Generate Python gRPC stubs from proto files"""
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    proto_dir = script_dir / "protos"
    output_dir = script_dir / "generated"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Create __init__.py in output directory
    init_file = output_dir / "__init__.py"
    init_file.touch()
    
    # Find all proto files
    proto_files = list(proto_dir.glob("*.proto"))
    
    if not proto_files:
        print("No proto files found in", proto_dir)
        return False
    
    print(f"Found {len(proto_files)} proto file(s):")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")
    
    # Generate stubs for each proto file
    success = True
    for proto_file in proto_files:
        try:
            print(f"\nGenerating stubs for {proto_file.name}...")
            
            # Command to generate Python stubs
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                str(proto_file)
            ]
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Successfully generated stubs for {proto_file.name}")
            else:
                print(f"✗ Failed to generate stubs for {proto_file.name}")
                print(f"Error: {result.stderr}")
                success = False
                
        except Exception as e:
            print(f"✗ Error processing {proto_file.name}: {e}")
            success = False
    
    if success:
        print(f"\n✓ All gRPC stubs generated successfully in {output_dir}")
        
        # List generated files
        generated_files = list(output_dir.glob("*.py"))
        print(f"\nGenerated files:")
        for file in generated_files:
            print(f"  - {file.name}")
    else:
        print("\n✗ Some errors occurred during stub generation")
    
    return success

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import grpc_tools.protoc
        import google.protobuf
        print("✓ Required dependencies are available")
        return True
    except ImportError as e:
        print(f"✗ Missing required dependency: {e}")
        print("Please install with: pip install grpcio-tools protobuf")
        return False

if __name__ == "__main__":
    print("gRPC Stub Generator")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Generate stubs
    if generate_grpc_stubs():
        print("\n✓ gRPC stub generation completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ gRPC stub generation failed!")
        sys.exit(1)