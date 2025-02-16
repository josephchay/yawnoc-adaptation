# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- Temporarily commented out all `steamworks` related code.

## [1.1.3] - 2024-12-07 (Supposed - based on updates on Steam)

### Added

- `.gitkeep` file for `save` directory.
- `save/save.json` file to `.gitignore`.

### Fixed

- Temporary fix for `TypeError: 'float' object cannot be interpreted as an integer` from minimap.py -
  by converting the position of the player to `int`.

### Changed

- Major updated code (Version 1.1.3) from DafluffyPotato's work 
  (obtained from game files from Steam game purchase: https://store.steampowered.com/app/2824730/Yawnoc/)

### Removed

- Removed `scripts/steamworks.py` and usages of this code file in `main.py`. 
  (Code can be obtained from local game files from the purchased game).
