# NFO Date Added Updater

This script updates the `<dateadded>` tag in .nfo files and `<Added>` tag to match the <releasedate> in movie.xml files for movies stored in a designated directory.

## What it does

- Searches for all .nfo files in the specified movie directory and subdirectories
- Backs up each .nfo file and associated movie.xml file before making changes
- Parses the .nfo file and extracts the release date or premiered date
- Sets the `<dateadded>` tag in the .nfo file to the extracted date + a fixed time
- Updates the <Added> tag in the movie.xml file with the same updated date/time
- Provides option to restore files from backups

## Usage

```
python date-added.py - Display help menu

python date-added.py run   - Run the update script 
python date-added.py restore - Restore files from backup
```

The script will log actions to a script_log file created in the movie directory.

## Dependencies

The script requires the following Python modules:

- xml.etree.ElementTree
- shutil
- datetime
- logging  
- importlib
- pip

It will attempt to install missing dependencies automatically using pip.

## Configuration

The main configuration is setting the movie directory path to process in the CONFIG constant at the top of the script.

## Restoring from backup

The script creates dated backup copies of all files before making changes. You can use the `restore` option to revert the files back to the pre-update state.

## Logging

All actions are logged to a script log file created in the movie directory. This helps track activity and catch any errors.