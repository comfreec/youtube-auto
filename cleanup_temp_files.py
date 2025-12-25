#!/usr/bin/env python3
"""
Cleanup script for MoneyPrinterTurbo temporary files
"""
import os
import glob
import shutil
from pathlib import Path

def cleanup_temp_files():
    """Clean up temporary files that might be causing issues"""
    
    print("🧹 Cleaning up temporary files...")
    
    # Directories to clean
    temp_dirs = [
        "storage/tasks",
        "storage/cache_videos", 
        "storage/local_videos"
    ]
    
    # File patterns to clean
    temp_patterns = [
        "**/*TEMP_MPY*",
        "**/temp-clip-*.mp4",
        "**/concat_list.txt",
        "**/*.tempTEMP_MPY*",
        "**/combined-*.mp4.temp*"
    ]
    
    cleaned_count = 0
    
    # Clean temp directories
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            try:
                # Clean old task directories (keep recent ones)
                if temp_dir == "storage/tasks":
                    task_dirs = glob.glob(os.path.join(temp_dir, "*"))
                    for task_dir in task_dirs:
                        if os.path.isdir(task_dir):
                            # Check if directory is older than 1 hour
                            import time
                            dir_time = os.path.getmtime(task_dir)
                            if time.time() - dir_time > 3600:  # 1 hour
                                print(f"  🗑️ Removing old task directory: {task_dir}")
                                shutil.rmtree(task_dir, ignore_errors=True)
                                cleaned_count += 1
                else:
                    print(f"  📁 Checking {temp_dir}...")
                    for file_path in glob.glob(os.path.join(temp_dir, "*")):
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                                print(f"    ✅ Removed: {os.path.basename(file_path)}")
                                cleaned_count += 1
                            except Exception as e:
                                print(f"    ❌ Failed to remove {file_path}: {e}")
            except Exception as e:
                print(f"  ❌ Error cleaning {temp_dir}: {e}")
    
    # Clean temp file patterns
    for pattern in temp_patterns:
        try:
            temp_files = glob.glob(pattern, recursive=True)
            for temp_file in temp_files:
                if os.path.isfile(temp_file):
                    try:
                        os.remove(temp_file)
                        print(f"  ✅ Removed temp file: {temp_file}")
                        cleaned_count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to remove {temp_file}: {e}")
        except Exception as e:
            print(f"  ❌ Error with pattern {pattern}: {e}")
    
    print(f"\n🎉 Cleanup completed! Removed {cleaned_count} files/directories")
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (1024**3)
        print(f"💾 Available disk space: {free_gb} GB")
        
        if free_gb < 5:
            print("⚠️ Warning: Low disk space! Consider freeing up space.")
        
    except Exception as e:
        print(f"❌ Could not check disk space: {e}")

if __name__ == "__main__":
    cleanup_temp_files()