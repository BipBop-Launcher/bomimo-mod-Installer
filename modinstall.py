##
## Version 1.0.0
## Jan 7th 2025 @ 6:50 PM EST
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

#https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class bcolors:
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

class exit_result:
    Bopimo_Not_Installed = -10
    Fetch_Latest_Failed = -9
    Update_Check_Failed = -8
    Download_Failed = -7
    Extraction_Failed = -6

    Uninstall_Failed = -5
    Reinstall_Failed = -4
    Update_Failed = -3
    Install_Failed = -2
    Failed = -1
    Sucess = 0
    Unknown = 1
    Install_Sucess = 2
    Update_Sucess = 3
    Reinstall_Sucess = 4
    Uninstall_Sucess = 5

    Unchanged = 10


## Vars
parser = argparse.ArgumentParser(
                    prog='Bopimod! Installer',
                    description='Installs/Updates Bopimod. A Mod Loader for Bopimo! based on GUMM'
)
parser.add_argument('-s', '--silent', action='store_true')
parser.add_argument('-r', '--reinstall', action='store_true')
parser.add_argument('-u', '--uninstall', action='store_true')
parser.add_argument('--skip-bopistrap', action='store_true')
run_args = parser.parse_args()

INSTALLER_VERSION = "1.0.0"
OS = platform.system()

path = ""
if OS == "Windows":
    path = f'{os.environ["APPDATA"]}/Bopimo!/Client/'.replace("\\", "/")
elif OS == "Linux":
    path = f'{os.environ["HOME"]}/.local/share/Bopimo!/Client/'

## Functions
def sprint(*args, sep=' ', end='\n'):
    if run_args.silent == False:

        # Convert all arguments to strings
        str_args = [str(arg) for arg in args]

        # Join the strings with the specified separator
        output = sep.join(str_args)

        print(output, end=end)

def get_latest_release(type = "file"):
    """Fetches info about the current release from https://bopimod.com/latest_release.json."""
    r = requests.get("https://bopimod.com/latest_release.json")
    if r.status_code == 200:

        if type == "file":
            rzip = requests.get(r.json()["file"])
            if rzip.status_code == 200:
                return zipfile.ZipFile(BytesIO(rzip.content), "r")
            else:
                sys.exit(exit_result.Download_Failed)
        else:
            return r.json()["version"]
    else:
        sys.exit(exit_result.Fetch_Latest_Failed)

    return None

def update_override(section, key, value):
    config_path = f'{path}override.cfg'
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)

    before = None
    if section in config:
        if key in config[section]:
            before = config[section][key]
    config.set(section, key, value)
    if before:
        sprint(f'\033[43m{bcolors.BLACK}~ {before} -> {config[section][key]}{bcolors.ENDC}')
    else:
        sprint(f'\033[42m{bcolors.BLACK}+ {bcolors.HEADER}[{section}]{bcolors.BLACK}: {key}{bcolors.BLACK} = {config[section][key]}{bcolors.ENDC}')

    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
def get_override_section(section):
    config_path = f'{path}override.cfg'
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)

    return config[section]

def get_override_value(section, key): #rename function?
    config_path = f'{path}override.cfg'
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_path)

    return config[section][key]

def has_bopistrap() -> bool:
    """Determines if Bopistrap is installed by checking for a Client folder."""
    if OS != "Windows": return False
    if not os.path.exists(f'{os.environ["LOCALAPPDATA"]}/Bopistrap/Client/'): return False
    return True

def already_installed() -> bool:
    """Checks if Bopimod has already been installed."""
    if os.path.exists(f'{path}override.cfg') and os.path.exists(f'{path}GUMM_mod_loader.tscn'): return True
    return False
    
def version_check(a : str, b : str):
    a = a.split('.')
    b = b.split('.')

    if a[0] < b[0]:
        return "Major"
    elif a[1] < b[1]:
        return "Minor"
    elif a[2] < b[2]:
        return "Patch"
    return None

def remove_file(path):
    if os.path.exists(path):
        os.remove(path)
        sprint(f'{bcolors.ITALIC}{bcolors.STRIKETHROUGH}{path}{bcolors.ENDC}')

def remove_folder(path):
    if os.path.exists(path):
        shutil.rmtree(path)
        sprint(f'{bcolors.ITALIC}{bcolors.STRIKETHROUGH}{path}{bcolors.ENDC}')

def install(skip_bopistrap = False):
    """Installs the latest version of Bopimod."""
    modloader = get_latest_release("file")
    if modloader:
        sprint(f'Installing to {bcolors.UNDERLINE}"{path}"{bcolors.ENDC}')
        modloader.extractall(f'{path}')
        update_override('application', 'run/main_scene', f'"{path}GUMM_mod_loader.tscn"')
        update_override('application', 'boot_splash/image', f'"{path}ModdedIcon.png"')
         
        #Create symlinks for Bopistrap
        if has_bopistrap() and not skip_bopistrap:
            bopistap_client_path = f'{os.environ["LOCALAPPDATA"]}/Bopistrap/Client/'.replace("\\", "/")
            sprint(f'Creating symlink for {bcolors.BOLD+bcolors.HEADER}Bopistrap{bcolors.ENDC}')

            remove_file(f'{bopistap_client_path}override.cfg')
            os.symlink(f'{path}override.cfg', f'{bopistap_client_path}override.cfg', target_is_directory = False)

        return True
    else:
        return False

def update():
    """Updates Bopimod to the latest version."""
    autoloads = get_override_section('autoload')
    install(True)
    #sprint(autoloads)
    for autoload in autoloads:
        update_override("autoload", autoload, autoloads[autoload])

def uninstall():
    if has_bopistrap():
        bopistap_client_path = f'{os.environ["LOCALAPPDATA"]}/Bopistrap/Client/'.replace("\\", "/")
        remove_file(f'{bopistap_client_path}override.cfg')

    remove_folder(f'{path}mods/')
    remove_file(f'{path}ModdedIcon.png')
    remove_file(f'{path}override.cfg')
    remove_file(f'{path}GUMM_mod_loader.tscn')
## Main

# TODO: Clean up this code. It's a bit of a mess.
def main():
    #Check that Bopimo! is installed
    if not os.path.exists(path): 
        sprint(f'{bcolors.FAIL}You don\'t have Bopimo! installed. Exiting...{bcolors.ENDC}')
        sys.exit(exit_result.Bopimo_Not_Installed)

    if already_installed() and not run_args.reinstall:
        if not run_args.uninstall: #Update Mode
            sprint(f'{bcolors.BOLD+bcolors.HEADER}Bopimo! {bcolors.FAIL}Mod Loader Updater {bcolors.OKCYAN}v{INSTALLER_VERSION}{bcolors.ENDC}')
            bopimod_version = get_override_value("modloader", "version_string")[1:-1]
            latest_version = get_latest_release("version")

            sprint(f'Instaled Version: {bcolors.OKCYAN}v{bopimod_version}{bcolors.ENDC}')
            sprint(f'Latest Version: {bcolors.OKCYAN}v{latest_version}{bcolors.ENDC}')

            update_type = version_check(bopimod_version.split('-')[0], latest_version)
            if update_type:
                sprint(f'New {update_type} update found!')
                update()
                sprint(f'{bcolors.FAIL}Bopimod!{bcolors.OKGREEN} has been updated.{bcolors.ENDC}')
                sys.exit(exit_result.Update_Sucess)

            else:
                sprint('No updates found. Exiting...')
                sys.exit(exit_result.Unchanged)

        else: #Remove Mode
            sprint(f'{bcolors.BOLD+bcolors.HEADER}Bopimo! {bcolors.FAIL}Mod Loader Uninstaller {bcolors.OKCYAN}v{INSTALLER_VERSION}{bcolors.ENDC}')
            sprint("Uninstalling...")
            uninstall()
            sprint(f'{bcolors.FAIL}Bopimod!{bcolors.OKGREEN} has been removed.{bcolors.ENDC}')
            sys.exit(exit_result.Uninstall_Sucess)

    elif run_args.reinstall: #Reinstall Mode
        sprint(f'Reinstalling {bcolors.FAIL}Bopimod{bcolors.ENDC}...')
        install()
        #sys.exit(exit_result.Reinstall_Sucess)
        
    elif not run_args.uninstall: #Install Mode
        sprint(f'{bcolors.BOLD+bcolors.HEADER}Bopimo! {bcolors.FAIL}Mod Loader Installer {bcolors.OKCYAN}v{INSTALLER_VERSION}{bcolors.ENDC}')
        install(run_args.skip_bopistrap)
        sprint(f'{bcolors.FAIL}Bopimod!{bcolors.OKGREEN} has been installed.{bcolors.ENDC}')
        sys.exit(exit_result.Install_Sucess)
    
    else:
        sprint("There is nothing to uninstall.")
        sprint("If there IS an install. You might need to reinstall the mod loader")
        sys.exit(exit_result.Unchanged)
        
if __name__ == "__main__":
    main()
