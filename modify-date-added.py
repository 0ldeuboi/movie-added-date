import os
import shutil
import logging
import sys
from datetime import datetime
import importlib
import xml.etree.ElementTree as ET
import re

# Constants and Configuration
CONFIG = {
    "DIRECTORY_PATH": "/volume1/EMBY_MEDIA/ANIMATED",
    # "DIRECTORY_PATH": "/mnt/w_drive/WORKING_MOVIES",
}

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def setup_logging(log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def close_log_handlers():
    logging.shutdown()


def check_root():
    if os.geteuid() != 0:
        raise PermissionError(
            "This script requires root privileges. Please run as root."
        )


def install_dependency(dependency):
    try:
        importlib.import_module(dependency)
    except ImportError as e:
        logging.warning(f"Dependency not found: {dependency}")
        if dependency == "pip":
            install_pip()
        else:
            install_dependency_manually(dependency)


def install_pip():
    check_root()
    try:
        import ensurepip

        ensurepip.bootstrap()
        logging.info("pip installed successfully.")
        importlib.import_module("pip")
    except Exception as install_error:
        log_error_and_continue(f"Error installing pip: {install_error}")


def install_dependency_manually(dependency):
    logging.warning(f"Please install the missing dependency '{dependency}' manually.")
    logging.warning("You can typically install it using the following command:")
    logging.warning(f"  pip install {dependency}")


def log_error_and_continue(message, exception=None):
    logging.error(message)
    if exception:
        logging.error(f"Exception: {str(exception)}")


def backup_file(file_path, file_type, skip_if_exists=True):
    try:
        datestamp = datetime.now().strftime("%Y-%m-%d")
        backup_file = f"{file_path}.{datestamp}.bak"

        if skip_if_exists and os.path.exists(backup_file):
            logging.warning(f"Backup file already exists for {file_type}: {backup_file}")
            return

        if os.path.exists(file_path):
            shutil.copy(file_path, backup_file)
            logging.info(f"Backup created for {file_type}: {backup_file}")
        else:
            logging.warning(f"File not found for {file_type} backup: {file_path}")

    except Exception as e:
        logging.error(f"Error creating backup for {file_type}: {e}")


def update_nfo(nfo_file_path):
    try:
        with open(nfo_file_path, "r", encoding="utf-8") as f:
            nfo_content = f.read()

        # Update <dateadded>
        dateadded_pattern = r"<dateadded>(.*?)</dateadded>"
        match_dateadded = re.search(dateadded_pattern, nfo_content)

        if match_dateadded is None:
            match_title = re.search(r"<title>(.*?)</title>", nfo_content)
            if match_title:
                title_tag = match_title.group(0)
                new_dateadded = f"{title_tag}\n  <dateadded>2024-10-01 13:52:00</dateadded>"
                nfo_content = nfo_content.replace(title_tag, new_dateadded, 1)
            else:
                log_error_and_continue(f"Error: <title> tag not found in NFO file {nfo_file_path}")
                return None

        # Existing code for updating <dateadded>
        releasedate_pattern = r"<releasedate>(.*?)</releasedate>"
        match_releasedate = re.search(releasedate_pattern, nfo_content)
        if match_releasedate:
            releasedate_value = match_releasedate.group(1).split()[0]
        else:
            match_premiered = re.search(r"<premiered>(.*?)</premiered>", nfo_content)
            if match_premiered:
                releasedate_value = match_premiered.group(1).split()[0]
            else:
                log_error_and_continue(f"Error: Neither <releasedate> nor <premiered> found in NFO file {nfo_file_path}")
                return None

        new_dateadded_value = f"<dateadded>{releasedate_value} 13:52:00</dateadded>"

        # Update <mpaa>
        mpaa_pattern = r"<mpaa>(.*?)</mpaa>"
        match_mpaa = re.search(mpaa_pattern, nfo_content)

        if match_mpaa:
            current_mpaa = match_mpaa.group(1)

            # Add logic to map different MPAA ratings to "PG-13"
            if current_mpaa == "12A" or current_mpaa == "15" or current_mpaa == "12":
                new_mpaa_value = "PG-13"
                nfo_content = re.sub(mpaa_pattern, f"<mpaa>{new_mpaa_value}</mpaa>", nfo_content)

        # Write the modified content to the file
        with open(nfo_file_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)

        return releasedate_value  

    except Exception as e:
        log_error_and_continue(f"Error updating NFO file {nfo_file_path}: {e}")
        return None


def update_xml(nfo_file_path):
    nfo_releasedate = update_nfo(nfo_file_path)

    if nfo_releasedate:
        xml_file_path = os.path.join(os.path.dirname(nfo_file_path), "movie.xml")

        if os.path.exists(xml_file_path):
            try:
                tree = ET.parse(xml_file_path)
            except ET.ParseError as e:
                logging.error(f"Error parsing XML file {xml_file_path}: {e}")
                return
        else:
            root = ET.Element("root")
            tree = ET.ElementTree(root)

        root = tree.getroot()
        added_elem = None
        for elem in root.iter():
            if elem.tag == "Added":
                added_elem = elem
                break

        if added_elem is None:
            added_elem = ET.SubElement(root, "Added")

        added_elem.text = datetime.strptime(nfo_releasedate, "%Y-%m-%d").strftime("%d/%m/%Y %I:%M:%S %p")

        try:
            tree.write(xml_file_path)
            logging.info(f"XML file updated: {xml_file_path}")  # Updated log entry
        except Exception as e:
            logging.error(f"Error writing XML file {xml_file_path}: {e}")
    else:
        logging.warning("Cannot update XML, no release date from NFO")


def restore_file(file_path, file_type, skip_if_exists=True):
    try:
        datestamp = datetime.now().strftime("%Y-%m-%d")
        backup_file = f"{file_path}.{datestamp}.bak"

        if skip_if_exists and os.path.exists(backup_file):
            logging.warning(f"Skipping restore for {file_type} as backup file already exists: {backup_file}")
            return

        if os.path.exists(backup_file):
            shutil.copy(backup_file, file_path)
            logging.info(f"Restored {file_type} from backup: {file_path}")
        else:
            logging.warning(f"Backup file not found for {file_type}: {backup_file}")

    except Exception as e:
        logging.error(f"Error restoring {file_type}: {e}")


def process_directory(directory_path, restore_mode=False, skip_backup_if_exists=True):
    nfo_files = [f for f in os.listdir(directory_path) if f.endswith(".nfo")]
    total_files = len(nfo_files)
    processed_files = 0

    for nfo_file in nfo_files:
        nfo_file_path = os.path.join(directory_path, nfo_file)

        try:
            if restore_mode:
                restore_file(nfo_file_path, "NFO", skip_backup_if_exists)
                # Restore corresponding movie.xml file
                movie_xml_path = os.path.join(directory_path, "movie.xml")
                restore_file(movie_xml_path, "XML", skip_backup_if_exists)
            else:
                backup_file(nfo_file_path, "NFO", skip_backup_if_exists)
                releasedate_value = update_nfo(nfo_file_path)

                if releasedate_value is not None:
                    message = f"Processing: NFO file updated: {nfo_file_path}"
                    print(message)
                    logging.debug(message)
                    movie_xml_path = os.path.join(directory_path, "movie.xml")
                    if os.path.exists(movie_xml_path):
                        backup_file(movie_xml_path, "XML", skip_backup_if_exists)
                        update_xml(nfo_file_path)

            processed_files += 1
            progress_message = f"Processing: Progress: {processed_files}/{total_files}"
            print(progress_message)
            logging.debug(progress_message)
        except Exception as e:
            error_message = f"Processing: Error processing {nfo_file}: {e}"
            print(error_message)
            logging.error(error_message)

    logging.info("Processing complete.")


def main():
    try:
        dependencies = ["xml.etree.ElementTree", "shutil", "datetime", "logging", "importlib", "pip"]
        for dependency in dependencies:
            install_dependency(dependency)

        SCRIPT_LOG_PATH = f"script_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        LOG_FILE_PATH = os.path.join(CONFIG["DIRECTORY_PATH"], SCRIPT_LOG_PATH)
        setup_logging(LOG_FILE_PATH)

        if len(sys.argv) > 1:
            if sys.argv[1] == "-h" or sys.argv[1] == "--help":
                print("Usage:")
                print("  python date-added.py - Display this help menu")
                print("  python date-added.py run - Run the script")
                print("  python date-added.py run force - Run the script and force backups")
                print("  python date-added.py restore - Restore from backup")
            elif sys.argv[1] == "run":
                restore_mode = False
                force_backup = "force" in sys.argv[2:]
            elif sys.argv[1] == "restore":
                restore_mode = True
                force_backup = False
            else:
                print("Usage:")
                print("  python date-added.py - Display this help menu")
                print("  python date-added.py run - Run the script")
                print("  python date-added.py run force - Run the script and force backups")
                print("  python date-added.py restore - Restore from backup")
                sys.exit(1)

            for subdir in os.scandir(CONFIG["DIRECTORY_PATH"]):
                if subdir.is_dir():
                    process_directory(subdir.path, restore_mode, force_backup)

            if restore_mode:
                logging.warning("Restore mode enabled. Files have been restored from backups.")
                logging.warning("Please review the restored files to ensure data integrity.")
                logging.warning("If everything looks correct, you can remove the backup files.")
            else:
                logging.warning("Restore mode not enabled. Use 'python date-added.py restore' to restore backups.")
        else:
            print("Usage:")
            print("  python date-added.py - Display this help menu")
            print("  python date-added.py run - Run the script")
            print("  python date-added.py run force - Run the script and force backups")
            print("  python date-added.py restore - Restore from backup")

    except Exception as e:
        log_error_and_continue(f"An unexpected error occurred: {e}")
    finally:
        close_log_handlers()


if __name__ == "__main__":
    main()

