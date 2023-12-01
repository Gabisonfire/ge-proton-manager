# ge-proton-manager

Helps managing and updating [GE-Proton versions](https://github.com/GloriousEggroll/proton-ge-custom)

## Features

- Dowload and install latest or specific versions
- Delete unused version, with options to keep X newest
- List which games uses which version
- Can be run in a cron to set & forget
- Automatically detects steam libraries

## Installation
```
wget https://github.com/Gabisonfire/ge-proton-manager/releases/latest/download/ge-proton-manager -O $HOME/.local/bin/ge-proton-manager
chmod +x $HOME/.local/bin/ge-proton-manager
```

## Usage
- --steam-install-path", 
  - Specify a custom install path. Defaults to \"~/.steam/steam\"
- --debug
  - Sets loglevel to debug
- --error
  - Sets loglevel to error only
- --very-quiet
  - Silences all output
- --print-used-games
  - Prints GE-Proton versions used by games in JSON format
- --delete-unused
  - Deletes unused GE-Proton versions
- --confirm-delete
  - Skips deletion prompt confirmation
- --latest
  - Download and install the latest version
- --version"
  - Download and install a specific version
    - Supported version strings are: `GE-ProtonX-XX`, `ge-protonX-XX`, `X-XX` or `X.XX`
- --keep
  - Keeps X most recent unused versions.

## Examples
### Install latest version
```
$~: ge-proton-manager --latest
23-12-01,15:28:02 | INFO |- Reading Steam libraries...
23-12-01,15:28:02 | INFO |- Finding installed compatibility tools...
23-12-01,15:28:02 | INFO |- Looking for versions currently in use
23-12-01,15:28:02 | INFO |- Fecthing latest version...
23-12-01,15:28:03 | INFO |- Downloading GE-Proton8-25...
23-12-01,15:28:03 | INFO |- Saving to /tmp/tmp0hzhy9lz/ge-proton.tar.gz
100%|███████████████████████████████████████████████████████████████████████████| 409M/409M [00:03<00:00, 115MB/s]
23-12-01,15:28:07 | INFO |- Extracting /tmp/tmp0hzhy9lz/ge-proton.tar.gz to /home/gabisonfire/.steam/steam/compatibilitytools.d...
100%|████████████████████████████████████████████████████████████████████████| 7947/7947 [00:05<00:00, 1532.31it/s]
23-12-01,15:28:16 | INFO |- Done.
```
### Install specific version
```
$~: ge-proton-manager --version 7.3
23-12-01,15:29:20 | INFO |- Reading Steam libraries...
23-12-01,15:29:20 | INFO |- Finding installed compatibility tools...
23-12-01,15:29:20 | INFO |- Looking for versions currently in use
23-12-01,15:29:20 | INFO |- Downloading GE-Proton7-3...
23-12-01,15:29:20 | INFO |- Saving to /tmp/tmpurt_xh3z/ge-proton.tar.gz
100%|█████████████████████████████████████████████████████████████████████████| 408M/408M [00:03<00:00, 116MB/s]
23-12-01,15:29:24 | INFO |- Extracting /tmp/tmpurt_xh3z/ge-proton.tar.gz to /home/gabisonfire/.steam/steam/compatibilitytools.d...
100%|████████████████████████████████████████████████████████████████████████████████| 8927/8927 [00:05<00:00, 1745.93it/s]
23-12-01,15:29:33 | INFO |- Done.
```
### Clean unused version
```
$~: ge-proton-manager --delete-unused --confirm-delete --debug
23-12-01,15:31:28 | INFO |- Reading Steam libraries...
23-12-01,15:31:28 | DEBUG |- Found /home/gabisonfire/.local/share/Steam
23-12-01,15:31:28 | DEBUG |- Found /mnt/steam/SteamLibrary
23-12-01,15:31:28 | INFO |- Finding installed compatibility tools...
23-12-01,15:31:28 | INFO |- Looking for versions currently in use
23-12-01,15:31:28 | DEBUG |- Used versions: ['GE-Proton7-38', 'GE-Proton7-41', 'GE-Proton7-49', 'GE-Proton8-16', 'GE-Proton8-6']
23-12-01,15:31:28 | DEBUG |- Installed versions: ['GE-Proton7-3', 'GE-Proton7-38', 'GE-Proton7-41', 'GE-Proton7-49', 'GE-Proton8-16', 'GE-Proton8-25', 'GE-Proton8-6']
23-12-01,15:31:28 | DEBUG |- Sanitized unused versions: ['GE-Proton7-3', 'GE-Proton8-25']
23-12-01,15:31:28 | DEBUG |- Deletion confirmation skipped
23-12-01,15:31:28 | INFO |- Deleting unused versions...
23-12-01,15:31:28 | DEBUG |- Deleting GE-Proton7-3
23-12-01,15:31:29 | DEBUG |- Deleting GE-Proton8-25
```

### Automation on a cronjob, daily at 2 am. Download latest, clean unused except latest.
```
0 2 * * * /home/gabisonfire/.local/bin/ge-proton-manager --latest --delete-unused --confirm-delete --very-quiet --keep 1
```