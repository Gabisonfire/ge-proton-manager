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
from tabulate import tabulate
from tqdm.auto import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("--steam-install-path", help="Specify a custom install path. Defaults to \"~/.steam/steam\"")
parser.add_argument("--debug", help="Sets loglevel to debug", action="store_true")
parser.add_argument("--error", help="Sets loglevel to error only", action="store_true")
parser.add_argument("--very-quiet", help="No output", action="store_true")
parser.add_argument("--delete-unused", help="Deletes unused GE-Proton versions", action="store_true")
parser.add_argument("--confirm-delete", help="Skips deletion prompt confirmation", action="store_false")
parser.add_argument("--list", help="List currently used versions and by which game", action="store_true")
parser.add_argument("--list-json", help="List currently used versions and by which game as json", action="store_true")
parser.add_argument("--latest", help="Download and install the latest version", action="store_true")
parser.add_argument("--update-games", help="Updates installed games to the latest GE version (requires --latest or --version)", action="store_true")
parser.add_argument("--update-default", help="Updates the default proton version to latest GE version (requires --latest or --version)", action="store_true")
parser.add_argument("--update-exclude", help="Exclude games from updates", nargs='+', default=[])
parser.add_argument("--dry-run", help="Does not write to Steam's config file", action="store_true")
parser.add_argument("--version", help="Download and install a specific version")
parser.add_argument("--keep", help="Keep X most recent unused versions.", type=int)
args = parser.parse_args()

logger = logging.getLogger("proton-ge-manager")
logger.setLevel(logging.INFO)
console = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s | %(levelname)s |- %(message)s', datefmt='%y-%m-%d,%H:%M:%S')
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
uses_stats_ids = {}
steam_libraries = []
installed_versions = []
used_version = []
unused_versions = []
cleaned_installed_version = []
cleaned_used_version = []

steamapps_path = f"{steam_install_path}/steamapps"
compat_path = f"{steam_install_path}/compatibilitytools.d"
config_path = f"{steam_install_path}/config/config.vdf"


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
                        uses_stats_ids[x.strip()].append((y['AppState']['name'],y['AppState']['appid']))
                    else:
                        uses_stats[x.strip()] = [y['AppState']['name']]
                        uses_stats_ids[x.strip()] = [(y['AppState']['name'],y['AppState']['appid'])]
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
    used_version = list(dict.fromkeys(uses_stats))
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
        return version_string
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
    return version_string

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

def change_proton_version(games, version):
    cfg = vdf.load(open(config_path))
    default_version = cfg["InstallConfigStore"]["Software"]["Valve"]["Steam"]["CompatToolMapping"]["0"]["name"]
    try:
        for game in games:
            logger.debug(f"Processing {game[0]}")
            if game[2] == default_version:
                logger.debug(f"{game[0]}({game[1]}) uses the default version ({default_version}), use --update-default to update.")
                continue
            if game[0] == "Default Proton Version":
                game = ("Default Proton Version", "0", default_version)
            logger.debug(f"Changing {game[0]}({game[1]}) from {game[2]} to {version}")
            if game[1] not in cfg["InstallConfigStore"]["Software"]["Valve"]["Steam"]["CompatToolMapping"]:
                logger.debug(f"{game[0]}({game[1]}) is likely set to the default version. This message won't appeat after the game is ran once. Skipping.")
            else:
                cfg["InstallConfigStore"]["Software"]["Valve"]["Steam"]["CompatToolMapping"][game[1]]["name"] = version
        if not args.dry_run:
            logger.debug("Writing config file...")
            vdf.dump(cfg, open(config_path, "w"))
        else:
            logger.debug("DRYRUN! Config file not written.")
        logger.debug("Game(s) updated.")
    except Exception as e:
        logger.error(str(e))

def update_games():
    ver = ""
    games = []
    filtered_games = []
    if not args.latest or args.version:
        logger.error("Requires either '--latest' or '--version' to be set")
    if args.latest:
        ver = install_version("latest")
    if args.version:
        ver = install_version(args.version)
    if args.update_games:
        for version in uses_stats_ids:
            games += ([(i[0], i[1], version) for i in uses_stats_ids[version]])
        for game in games:
            if game[1] in args.update_exclude:
                logger.debug(f"Excluding {game[0]}({game[1]}) due to exclude rule")
                continue
            filtered_games.append(game)
    if args.update_default:
        filtered_games.append(("Default Proton Version", "0", ""))
    change_proton_version(filtered_games, ver)
    exit(0)

prep_lists()
clean_lists()

# Debug logging
logger.debug(f"Used versions: {cleaned_used_version}")
logger.debug(f"Installed versions: {cleaned_installed_version}")
logger.debug(f"Unused versions: {unused_versions}")

def list_versions():
    print()
    print(tabulate(uses_stats, headers="keys"))
    print()

if args.list_json:
    print(json.dumps(uses_stats_ids, indent=2))
if args.update_games:
    update_games()
if args.update_default:
    update_games()
if args.latest:
    install_version("latest")
if args.version:
    install_version(args.version)
if args.delete_unused:
    delete_unused(args.confirm_delete)
if args.list:
    list_versions()


# TODO
# Update app manifest, otherwise --list is not accurate.
# Post update command and vars