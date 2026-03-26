"""
Build script — package the bot into a single .exe file using PyInstaller.

Usage:
    python build.py

Output:
    dist/MahoganyHomes.exe
"""
import subprocess
import sys
import os


def build():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_dir, "main.py")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "MahoganyHomes",
        "--add-data", f"config{os.pathsep}config",
        "--add-data", f"data{os.pathsep}data",
        main_script,
    ]

    print("Building MahoganyHomes.exe...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=project_dir)

    if result.returncode == 0:
        exe_path = os.path.join(project_dir, "dist", "MahoganyHomes.exe")
        print(f"\nBuild successful! Exe at: {exe_path}")
    else:
        print(f"\nBuild failed with code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
