import os
from importlib import import_module
import subprocess
import sys


def install_requirements(requirements_path):
    with open(requirements_path, encoding='utf-8') as f:
        packages = f.read().splitlines()

    for package in packages:
        if not check_package(package):
            try:
                print(f"Installing {package}...")
                subprocess.run([sys.executable, "-m", "pip", "install", package, "-q", "--no-warn-conflicts"], check=True)
            except subprocess.CalledProcessError:
                # Install latest version
                print(f"\n\033[34mFailed to install {package}. Trying again...\033[0m")
                print(f"Installing {package.split('==')[0]}...")
                subprocess.run([sys.executable, "-m", "pip", "install", package.split('==')[0], "-q", "--no-warn-conflicts"], check=True)


def check_package(package_name):
    try:
        import_module(package_name)
        return True
    except ImportError:
        return False


def update_pip():
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "-q"],
                       capture_output=True, check=False)
    except Exception as e:
        print(f"Error updating pip: {str(e)}")


if __name__ == "__main__":
    try:
        print("Installing dependencies...")
        update_pip()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        requirements_file = os.path.join(script_dir, 'lib', 'requirements.txt')
        install_ffmpeg_script = os.path.join(script_dir, 'lib', 'install_ffmpeg.py')
        vod_recovery_script = os.path.join(script_dir, 'vod_recovery.py')

        install_requirements(requirements_file)
        subprocess.run([sys.executable, install_ffmpeg_script], check=False)
        subprocess.run([sys.executable, vod_recovery_script], check=False)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        input("\nPress Enter to continue...")

