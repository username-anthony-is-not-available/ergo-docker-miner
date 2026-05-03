import os
import time
import re
import logging
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("log_monitor")

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
LOG_PATTERN = os.getenv('LOG_PATTERN', 'miner*.log')
RESTART_SCRIPT = os.getenv('RESTART_SCRIPT', './restart.sh')
ERROR_PATTERN = re.compile(
    r'out of memory|illegal instruction|CUDA error|GPU fell off the bus|an illegal memory access was encountered',
    re.IGNORECASE
)

class LogHandler(FileSystemEventHandler):
    def __init__(self):
        self.log_files = {}
        self.observer = None

    def on_modified(self, event):
        if not event.is_directory:
            filepath = event.src_path
            if self._matches_pattern(filepath):
                self._process_log_file(filepath)

    def on_created(self, event):
        if not event.is_directory:
            filepath = event.src_path
            if self._matches_pattern(filepath):
                logger.info(f"New log file detected: {filepath}")
                self._process_log_file(filepath)

    def _matches_pattern(self, filepath):
        import fnmatch
        return fnmatch.fnmatch(os.path.basename(filepath), LOG_PATTERN)

    def _process_log_file(self, filepath):
        try:
            if filepath not in self.log_files:
                self.log_files[filepath] = {'file': None, 'position': 0, 'inode': None}

            entry = self.log_files[filepath]
            current_inode = os.stat(filepath).st_ino

            if entry['inode'] != current_inode:
                if entry['file']:
                    entry['file'].close()
                entry['file'] = open(filepath, 'r')
                entry['position'] = 0
                entry['inode'] = current_inode
                logger.info(f"Log file rotated or reopened: {filepath}")

            if not entry['file']:
                entry['file'] = open(filepath, 'r')
                entry['file'].seek(0, os.SEEK_END)
                entry['position'] = entry['file'].tell()

            entry['file'].seek(entry['position'])
            new_lines = entry['file'].readlines()
            entry['position'] = entry['file'].tell()

            for line in new_lines:
                line = line.strip()
                if ERROR_PATTERN.search(line):
                    logger.error(f"CRITICAL: CUDA error detected: {line}")
                    logger.info("Triggering auto-restart...")
                    time.sleep(1)
                    try:
                        subprocess.run([RESTART_SCRIPT], check=True)
                    except Exception as e:
                        logger.error(f"Failed to run restart script: {e}")

        except FileNotFoundError:
            logger.warning(f"Log file not found: {filepath}")
            if filepath in self.log_files:
                del self.log_files[filepath]
        except Exception as e:
            logger.exception(f"Error processing log file {filepath}: {e}")

    def start(self):
        self.observer = Observer()
        self.observer.schedule(self, DATA_DIR, recursive=False)
        self.observer.start()
        logger.info(f"Started CUDA error monitor on {DATA_DIR} for {LOG_PATTERN}")

        try:
            while True:
                time.sleep(10)
                self._check_for_new_files()
        except KeyboardInterrupt:
            self.stop()

    def _check_for_new_files(self):
        import glob
        current_files = set(glob.glob(os.path.join(DATA_DIR, LOG_PATTERN)))
        for filepath in current_files:
            if filepath not in self.log_files:
                logger.info(f"Detected new log file: {filepath}")
                self._process_log_file(filepath)

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        for entry in self.log_files.values():
            if entry['file']:
                entry['file'].close()
        logger.info("Stopped CUDA error monitor")

if __name__ == '__main__':
    handler = LogHandler()
    handler.start()
