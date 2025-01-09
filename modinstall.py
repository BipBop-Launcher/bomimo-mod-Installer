from io import BytesIO
from enum import Enum
import configparser
import argparse
import platform
import requests
import zipfile
import shutil
import sys
import os

# https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class BColors:
    BLACK = '\033[30m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    STRIKETHROUGH = '\033[9m'

class ExitResult(Enum):
    BOPIMO_NOT_INSTALLED = -10
    FETCH_LATEST_FAILED = -9
    UPDATE_CHECK_FAILED = -8
    DOWNLOAD_FAILED = -7
    EXTRACTION_FAILED = -6
    UNINSTALL_FAILED = -5
    REINSTALL_FAILED = -4
    UPDATE_FAILED = -3
    INSTALL_FAILED = -2
    FAILED = -1
    SUCCESS = 0
    UNKNOWN = 1
    INSTALL_SUCCESS = 2
    UPDATE_SUCCESS = 3
    REINSTALL_SUCCESS = 4
    UNINSTALL_SUCCESS = 5
    UNCHANGED = 10

# Vars
parser = argparse.ArgumentParser(
    prog='Bopimod! Installer',
    description='Installs/Updates Bopimod. A Mod Loader for Bopimo! based on GUMM'
)
parser.add_argument('-s', '--silent', action='store_true')
parser.add_argument('-r', '--reinstall', action='store_true')
parser.add_argument('-u', '--uninstall', action='store_true')
parser.add_argument('--skip-bopistrap', action='store_true')
parser.add_argument('--quick-exit', action='store_true')
run_args = parser.parse_args()

INSTALLER_VERSION = "1.0.0"
OS = platform.system()

if OS == "Windows":
    PATH = os.path.join(os.environ["APPDATA"], "Bopimo!", "Client").replace("\\", "/")
elif OS == "Linux":
    PATH = os.path.join(os.environ["HOME"], ".local", "share", "Bopimo!", "Client").replace("\\", "/")

# Funcs
def silent_print(*args, sep=' ', end='\n'):
    if not run_args.silent:
        print(sep.join(map(str, args)), end=end)

def silent_exit(code: int):
    if not run_args.silent and not run_args.quick_exit:
        silent_print("\n")
        input("Press Enter to exit.")
    sys.exit(code)

def get_latest_release(release_type="file"):
    """Fetches info about the current release from https://bopimod.com/latest_release.json."""
    response = requests.get("https://bopimod.com/latest_release.json")
    if response.status_code == 200:
        if release_type == "file":
            rzip = requests.get(response.json()["file"])
            if rzip.status_code == 200:
                return zipfile.ZipFile(BytesIO(rzip.content), "r")
            silent_exit(ExitResult.DOWNLOAD_FAILED.value)
        return response.json()["version"]
    silent_exit(ExitResult.FETCH_LATEST_FAILED.value)

def update_override(section, key, value):
    config_path = os.path.join(PATH, "override.cfg")
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)

    before = config.get(section, key, fallback=None)
    config.set(section, key, value)

    if before:
        silent_print(f'\033[43m{BColors.BLACK}~ {before} -> {config[section][key]}{BColors.ENDC}')
    else:
        silent_print(f'\033[42m{BColors.BLACK}+ {BColors.HEADER}[{section}]{BColors.BLACK}: {key} = {config[section][key]}{BColors.ENDC}')

    with open(config_path, 'w') as configfile:
        config.write(configfile)

def get_override_section(section):
    config_path = os.path.join(PATH, "override.cfg")
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)
    return config[section]

def get_override_value(section, key):
    config_path = os.path.join(PATH, "override.cfg")
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)
    return config[section][key]

def has_bopistrap() -> bool:
    """Determines if Bopistrap is installed by checking for a Client folder."""
    if OS != "Windows":
        return False
    return os.path.exists(os.path.join(os.environ["LOCALAPPDATA"], "Bopistrap", "Client"))

def already_installed() -> bool:
    """Checks if Bopimod has already been installed."""
    return (
        os.path.exists(os.path.join(PATH, "override.cfg")) and
        os.path.exists(os.path.join(PATH, "GUMM_mod_loader.tscn"))
    )

def version_check(version_a: str, version_b: str):
    a = list(map(int, version_a.split('.')))
    b = list(map(int, version_b.split('.')))

    if a[0] < b[0]:
        return "Major"
    if a[1] < b[1]:
        return "Minor"
    if a[2] < b[2]:
        return "Patch"
    return None

def remove_file(path):
    if os.path.exists(path):
        os.remove(path)
        silent_print(f'{BColors.ITALIC}{BColors.STRIKETHROUGH}{path}{BColors.ENDC}')

def remove_folder(path):
    if os.path.exists(path):
        shutil.rmtree(path)
        silent_print(f'{BColors.ITALIC}{BColors.STRIKETHROUGH}{path}{BColors.ENDC}')

def install(skip_bopistrap=False):
    """Installs the latest version of Bopimod."""
    modloader = get_latest_release("file")
    if modloader:
        silent_print(f'Installing to {BColors.UNDERLINE}"{PATH}"{BColors.ENDC}')
        modloader.extractall(PATH)
        update_override('application', 'run/main_scene', f'"{PATH}GUMM_mod_loader.tscn"')
        update_override('application', 'boot_splash/image', f'"{PATH}ModdedIcon.png"')

        if has_bopistrap() and not skip_bopistrap:
            bopistrap_client_path = os.path.join(os.environ["LOCALAPPDATA"], "Bopistrap", "Client").replace("\\", "/")
            silent_print(f'Creating symlink for {BColors.BOLD}{BColors.HEADER}Bopistrap{BColors.ENDC}')
            remove_file(os.path.join(bopistrap_client_path, "override.cfg"))
            os.symlink(os.path.join(PATH, "override.cfg"), os.path.join(bopistrap_client_path, "override.cfg"), target_is_directory=False)

        return True
    return False

def update():
    """Updates Bopimod to the latest version."""
    autoloads = get_override_section('autoload')
    install(True)
    for autoload, value in autoloads.items():
        update_override("autoload", autoload, value)

def uninstall():
    if has_bopistrap():
        bopistrap_client_path = os.path.join(os.environ["LOCALAPPDATA"], "Bopistrap", "Client").replace("\\", "/")
        remove_file(os.path.join(bopistrap_client_path, "override.cfg"))

    remove_folder(os.path.join(PATH, "mods"))
    remove_file(os.path.join(PATH, "ModdedIcon.png"))
    remove_file(os.path.join(PATH, "override.cfg"))
    remove_file(os.path.join(PATH, "GUMM_mod_loader.tscn"))

# Main
def main():
    if not os.path.exists(PATH):
        silent_print(f'{BColors.FAIL}You don\'t have Bopimo! installed.{BColors.ENDC}')
        silent_exit(ExitResult.BOPIMO_NOT_INSTALLED.value)

    if already_installed() and not run_args.reinstall:
        if not run_args.uninstall:
            silent_print(f'{BColors.BOLD}{BColors.HEADER}Bopimo! {BColors.FAIL}Mod Loader Updater {BColors.OKCYAN}v{INSTALLER_VERSION}{BColors.ENDC}')
            bopimod_version = get_override_value("modloader", "version_string")[1:-1]
            latest_version = get_latest_release("version")

            silent_print(f'Installed Version: {BColors.OKCYAN}v{bopimod_version}{BColors.ENDC}')
            silent_print(f'Latest Version: {BColors.OKCYAN}v{latest_version}{BColors.ENDC}')

            update_type = version_check(bopimod_version.split('-')[0], latest_version)
            if update_type:
                silent_print(f'New {update_type} update found!')
                update()
                silent_print(f'{BColors.FAIL}Bopimod!{BColors.OKGREEN} has been updated.{BColors.ENDC}')
                silent_exit(ExitResult.UPDATE_SUCCESS.value)
            else:
                silent_print('No updates found.')
                silent_exit(ExitResult.UNCHANGED.value)

        silent_print(f'{BColors.BOLD}{BColors.HEADER}Bopimo! {BColors.FAIL}Mod Loader Uninstaller {BColors.OKCYAN}v{INSTALLER_VERSION}{BColors.ENDC}')
        silent_print("Uninstalling...")
        uninstall()
        silent_print(f'{BColors.FAIL}Bopimod!{BColors.OKGREEN} has been removed.{BColors.ENDC}')
        silent_exit(ExitResult.UNINSTALL_SUCCESS.value)

    if run_args.reinstall:
        silent_print(f'Reinstalling {BColors.FAIL}Bopimod{BColors.ENDC}...')
        install()
        silent_exit(ExitResult.REINSTALL_SUCCESS.value)

    if not run_args.uninstall:
        silent_print(f'{BColors.BOLD}{BColors.HEADER}Bopimo! {BColors.FAIL}Mod Loader Installer {BColors.OKCYAN}v{INSTALLER_VERSION}{BColors.ENDC}')
        install(run_args.skip_bopistrap)
        silent_print(f'{BColors.FAIL}Bopimod!{BColors.OKGREEN} has been installed.{BColors.ENDC}')
        silent_exit(ExitResult.INSTALL_SUCCESS.value)

    silent_print("There is nothing to uninstall.")
    silent_print("If there IS an install, you might need to reinstall the mod loader.")
    silent_exit(ExitResult.UNCHANGED.value)

if __name__ == "__main__":
    main()
