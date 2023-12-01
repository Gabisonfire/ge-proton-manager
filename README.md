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
    - Supported version string are: `GE-ProtonX-XX`, `ge-protonX-XX`, `X-XX` or `X.XX`
- --keep
  - Keeps X most recent unused versions.

## Examples
### Interactive
```

```