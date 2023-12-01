import requests
import os
import vdf
import json
import tempfile
import tarfile
import shutil
import re
import argparse
import logging
import sys
from tqdm.auto import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("--steam-install-path", help="Specify a custom install path. Defaults to \"~/.steam/steam\"")
parser.add_argument("--debug", help="Sets loglevel to debug", action="store_true")
parser.add_argument("--error", help="Sets loglevel to error only", action="store_true")
parser.add_argument("--very-quiet", help="No output", action="store_true")
parser.add_argument("--print-used-games", help="Prints GE-Proton used by games", action="store_true")
parser.add_argument("--delete-unused", help="Deletes unused GE-Proton versions", action="store_true")
parser.add_argument("--confirm-delete", help="Skips deletion prompt confirmation", action="store_false")
parser.add_argument("--latest", help="Download and install the latest version", action="store_true")
parser.add_argument("--version", help="Download and install a specific version")
parser.add_argument("--keep", help="Keep X most recent unused versions.", type=int)
args = parser.parse_args()

logger = logging.getLogger("proton-ge-manager")
logger.setLevel(logging.INFO)
console = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(filename)s - %(message)s', datefmt='%y-%m-%d,%H:%M:%S')
console.setFormatter(formatter)
logger.addHandler(console)

if args.debug:
    logger.setLevel(logging.DEBUG)
if args.error:
    logger.setLevel(logging.ERROR)
if args.very_quiet:
    logger.setLevel(logging.CRITICAL)
if not args.confirm_delete:
    args.confirm_delete = False

steam_install_path = os.path.expanduser("~/.steam/steam")
if args.steam_install_path:
    steam_install_path = args.steam_install_path

uses_stats = {}
steam_libraries = []
installed_versions = []
used_version = []
unused_versions = []
cleaned_installed_version = []
cleaned_used_version = []

steamapps_path = f"{steam_install_path}/steamapps"
compat_path = f"{steam_install_path}/compatibilitytools.d"


def prep_lists():
    logger.info("Reading Steam libraries...")
    lib_files = vdf.load(open(f"{steamapps_path}/libraryfolders.vdf"))["libraryfolders"]
    for file in lib_files:
        logger.debug(f"Found {lib_files[file]['path']}")
        steam_libraries.append(lib_files[file]["path"])

    logger.info("Finding installed compatibility tools...")
    for dir in os.listdir(compat_path):
        #x = open(f"{compat_path}/{dir}/version").read()
        #installed_versions.append(x.split(' ')[1].strip())
        x = vdf.load(open(f"{compat_path}/{dir}/compatibilitytool.vdf"))
        logger.debug(f"Found {list(x['compatibilitytools']['compat_tools'].keys())[0]} in {compat_path}/{dir}")
        installed_versions.append(list(x["compatibilitytools"]["compat_tools"].keys())[0])

    logger.info("Looking for versions currently in use")
    for library in steam_libraries:
        for dir in os.listdir(f"{library}/steamapps/compatdata"):
            try:
                x = open(f"{library}/steamapps/compatdata/{dir}/version").read()
                y = vdf.load(open(f"{library}/steamapps/appmanifest_{dir}.acf"))
                if x.strip().startswith("GE-Proton"):
                    logger.debug(f"{x.strip()} is currently used by {y['AppState']['name']}")
                    if x.strip() in uses_stats:
                        uses_stats[x.strip()].append(y['AppState']['name'])
                    else:
                        uses_stats[x.strip()] = [y['AppState']['name']]
                used_version.append(x.strip())
            except FileNotFoundError as e:
                # These are expected, not logging them.
                #logger.debug(e)
                pass
            except Exception as e:
                logger.error(e)
                exit(1)

def clean_lists():
    global used_version
    global cleaned_used_version
    global cleaned_installed_version
    global unused_versions
    used_version = list(dict.fromkeys(used_version))
    cleaned_used_version = [ x for x in used_version if "GE-Proton" in x ]
    cleaned_installed_version = [ x for x in installed_versions if "GE-Proton" in x ]
    cleaned_used_version.sort()
    cleaned_installed_version.sort()
    unused_versions = [ x for x in cleaned_installed_version if x not in cleaned_used_version]
    unused_versions.sort()
    if args.keep:
        logger.debug(f"Current unused versions: {unused_versions}")
        logger.debug(f"Keeping newest {args.keep} versions")
        unused_versions = unused_versions[:-args.keep]

def capitalize_nth(s, n):
    return s[:n] + s[n:].capitalize()

def sanitize_version(version_string):
    if re.match("(([1-9][0-9])|([1-9]))-(([1-9][0-9])|([1-9]))", version_string):
        return f"GE-Proton{version_string}"
    if re.match("(([1-9][0-9])|([1-9])).(([1-9][0-9])|([1-9]))", version_string):
        return f"GE-Proton{version_string.replace('.','-')}"
    if re.match("GE-Proton(([1-9][0-9])|([1-9]))-(([1-9][0-9])|([1-9]))", version_string):
        return version_string
    if re.match("ge-proton(([1-9][0-9])|([1-9]))-(([1-9][0-9])|([1-9]))", version_string):
        version_string = capitalize_nth(version_string, 0)
        version_string = capitalize_nth(version_string, 1)
        version_string = capitalize_nth(version_string, 3)
        return version_string
    raise(ValueError(f"No match for '{version_string}'"))

def install_version(version_string):
    if version_string == "latest":
        logger.info(f"Fecthing latest version...")
        r = requests.get("https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest")
        version_string = json.loads(r.content.decode())["tag_name"]
    logger.debug(f"Version string received: {version_string}")
    version_string = sanitize_version(version_string)
    logger.debug(f"Version string returned: {version_string}")
    if version_string in cleaned_installed_version:
        logger.warning(f"{version_string} is already installed.")
        return
    logger.info(f"Downloading {version_string}...")
    logger.debug(f"URL: https://github.com/GloriousEggroll/proton-ge-custom/releases/download/{version_string}/{version_string}.tar.gz")
    temp_dir = tempfile.TemporaryDirectory()
    temp_file_path = f"{temp_dir.name}/ge-proton.tar.gz"
    logger.info(f"Saving to {temp_file_path}")
    # Download
    with requests.get(f"https://github.com/GloriousEggroll/proton-ge-custom/releases/download/{version_string}/{version_string}.tar.gz", stream=True) as r:
        total_length = int(r.headers.get("Content-Length"))
        if r.status_code != 200:
            logger.error(f"Version '{version_string}' cannot be found ({r.status_code})")
            return
        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="")as raw:
            with open(temp_file_path, 'wb') as output:
                shutil.copyfileobj(raw, output)
    # Extract
    logger.info(f"Extracting {temp_file_path} to {compat_path}...")
    with tarfile.open(temp_file_path) as tar:
        for member in tqdm(iterable=tar.getmembers(), total=len(tar.getmembers())):
            tar.extract(member=member, path=compat_path)
    temp_dir.cleanup()
    logger.info("Done.")

def delete_unused(confirmation_required = True):
    if len(unused_versions) == 0:
        logger.info("No unused versions found.")
        return
    if not confirmation_required:
        logger.debug("Deletion confirmation skipped")
    confirmed = not confirmation_required
    if confirmation_required:
        for i in unused_versions: print(i)
        answer = input(f"Are you sure you want to delete these versions?(y/n)")
        if answer.lower() in ["y","yes"]:
            confirmed = True
        elif answer.lower() in ["n","no"]:
            return
        else:
            return
    if confirmed:
        logger.info("Deleting unused versions...")
        for i in unused_versions:
            logger.debug(f"Deleting {i}")
            shutil.rmtree(f"{compat_path}/{i}")

prep_lists()
clean_lists()

# Debug logging
logger.debug(f"Used versions: {cleaned_used_version}")
logger.debug(f"Installed versions: {cleaned_installed_version}")
logger.debug(f"Sanitized unused versions: {unused_versions}")

if args.print_used_games:
    print(json.dumps(uses_stats, indent=2))
if args.latest:
    install_version("latest")
if args.version:
    install_version(args.version)
if args.delete_unused:
    delete_unused(args.confirm_delete)
