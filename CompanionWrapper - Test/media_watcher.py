"""
Media Watcher for the entity

Watches a folder for new audio files and triggers media processing.
Uses watchdog library for filesystem monitoring.

Watch folder: F:\AlphaKayZero\inputs\media\
Supported formats: .mp3, .wav, .flac, .ogg, .m4a
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileCreatedEvent = None
    # Stub class for when watchdog isn't installed
    class FileSystemEventHandler:
        pass
    print("[WARNING] watchdog not installed. Run: pip install watchdog")


class MediaFileHandler(FileSystemEventHandler):
    """Handler for media file creation events."""

    # Supported audio formats
    SUPPORTED_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'}

    # Patterns to ignore (temporary files, partial downloads, etc.)
    IGNORE_PATTERNS = {
        '.tmp', '.part', '.crdownload', '.downloading',
        '~', '.temp', '_temp'
    }

    def __init__(
        self,
        on_media_detected: Callable[[str], None],
        debounce_seconds: float = 2.0
    ):
        """
        Initialize the media file handler.

        Args:
            on_media_detected: Callback function when a new media file is detected
            debounce_seconds: Wait time before processing (handles partial writes)
        """
        super().__init__()
        self.on_media_detected = on_media_detected
        self.debounce_seconds = debounce_seconds

        # Track recently processed files to avoid duplicates
        self._processed_files: Set[str] = set()
        self._pending_files: dict = {}  # filepath -> scheduled_time

    def _is_temporary_file(self, filename: str) -> bool:
        """Check if file appears to be temporary or incomplete."""
        filename_lower = filename.lower()

        # Check ignore patterns
        for pattern in self.IGNORE_PATTERNS:
            if pattern in filename_lower:
                return True

        # Hidden files
        if filename.startswith('.'):
            return True

        return False

    def _is_supported_format(self, filename: str) -> bool:
        """Check if file is a supported audio format."""
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        filepath = event.src_path
        filename = os.path.basename(filepath)

        # Skip non-audio files
        if not self._is_supported_format(filename):
            return

        # Skip temporary files
        if self._is_temporary_file(filename):
            print(f"[MEDIA WATCHER] Ignoring temporary file: {filename}")
            return

        # Skip already processed
        if filepath in self._processed_files:
            return

        print(f"[MEDIA WATCHER] New media file detected: {filename}")

        # Schedule processing after debounce period (handles partial writes)
        self._schedule_processing(filepath)

    def _schedule_processing(self, filepath: str):
        """Schedule file processing after debounce period."""
        # Cancel any existing scheduled processing
        if filepath in self._pending_files:
            return

        self._pending_files[filepath] = time.time() + self.debounce_seconds

        # Start debounce thread
        thread = threading.Thread(
            target=self._debounced_process,
            args=(filepath,),
            daemon=True
        )
        thread.start()

    def _debounced_process(self, filepath: str):
        """Wait for debounce period then process file."""
        time.sleep(self.debounce_seconds)

        # Verify file still exists and is stable
        if not os.path.exists(filepath):
            print(f"[MEDIA WATCHER] File disappeared: {filepath}")
            self._pending_files.pop(filepath, None)
            return

        # Check file size is stable (not still writing)
        try:
            size1 = os.path.getsize(filepath)
            time.sleep(0.5)
            size2 = os.path.getsize(filepath)

            if size1 != size2:
                # File still being written, reschedule
                print(f"[MEDIA WATCHER] File still being written: {os.path.basename(filepath)}")
                self._pending_files.pop(filepath, None)
                self._schedule_processing(filepath)
                return
        except OSError:
            self._pending_files.pop(filepath, None)
            return

        # File is ready, process it
        self._pending_files.pop(filepath, None)
        self._processed_files.add(filepath)

        print(f"[MEDIA WATCHER] Processing: {os.path.basename(filepath)}")
        try:
            self.on_media_detected(filepath)
        except Exception as e:
            print(f"[MEDIA WATCHER] Error processing file: {e}")


class MediaWatcher:
    """
    Filesystem watcher for the media input folder.

    Watches F:\AlphaKayZero\inputs\media\ for new audio files
    and triggers processing via the MediaOrchestrator.
    """

    DEFAULT_WATCH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "media")

    def __init__(
        self,
        watch_path: Optional[str] = None,
        media_orchestrator = None,
        debounce_seconds: float = 2.0
    ):
        """
        Initialize the media watcher.

        Args:
            watch_path: Folder to watch (default: inputs/media/)
            media_orchestrator: MediaOrchestrator instance for processing
            debounce_seconds: Wait time before processing new files
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog not installed. Run: pip install watchdog")

        self.watch_path = Path(watch_path or self.DEFAULT_WATCH_PATH)
        self.watch_path.mkdir(parents=True, exist_ok=True)

        self.media_orchestrator = media_orchestrator
        self.debounce_seconds = debounce_seconds

        # Create event handler
        self._handler = MediaFileHandler(
            on_media_detected=self._on_media_detected,
            debounce_seconds=debounce_seconds
        )

        # Create observer
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.watch_path), recursive=False)

        self._running = False

        print(f"[MEDIA WATCHER] Initialized for: {self.watch_path}")

    def _on_media_detected(self, filepath: str):
        """Handle detected media file."""
        if self.media_orchestrator:
            result = self.media_orchestrator.process_new_audio(filepath)
            status = result.get('status', 'unknown')
            entity_id = result.get('entity_id', 'unknown')

            if status == 'new':
                print(f"[MEDIA WATCHER] New song processed: {entity_id}")
            elif status == 'reencounter':
                print(f"[MEDIA WATCHER] Re-encountered song: {entity_id}")
            else:
                print(f"[MEDIA WATCHER] Processing result: {status}")
        else:
            print(f"[MEDIA WATCHER] Media detected but no orchestrator: {filepath}")

    def set_orchestrator(self, orchestrator):
        """Set the media orchestrator (for deferred initialization)."""
        self.media_orchestrator = orchestrator

    def start(self):
        """Start watching the media folder."""
        if self._running:
            return

        self._observer.start()
        self._running = True

        print(f"[MEDIA WATCHER] Started watching: {self.watch_path}")
        print(f"[MEDIA WATCHER] Supported formats: {', '.join(MediaFileHandler.SUPPORTED_EXTENSIONS)}")

    def stop(self):
        """Stop watching the media folder."""
        if not self._running:
            return

        self._observer.stop()
        self._observer.join(timeout=5.0)
        self._running = False

        print("[MEDIA WATCHER] Stopped")

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def scan_existing_files(self) -> list:
        """
        Scan for existing files in watch folder.

        Useful for startup to process any files added while the entity was offline.

        Returns:
            List of filepaths that were processed
        """
        processed = []

        for filepath in self.watch_path.iterdir():
            if filepath.is_file():
                filename = filepath.name

                if not self._handler._is_supported_format(filename):
                    continue

                if self._handler._is_temporary_file(filename):
                    continue

                print(f"[MEDIA WATCHER] Found existing file: {filename}")
                self._on_media_detected(str(filepath))
                processed.append(str(filepath))

        return processed

    def get_watched_path(self) -> str:
        """Get the watched folder path."""
        return str(self.watch_path)

    def get_stats(self) -> dict:
        """Get watcher statistics."""
        return {
            "watch_path": str(self.watch_path),
            "running": self._running,
            "files_processed": len(self._handler._processed_files),
            "pending_files": len(self._handler._pending_files)
        }


# Testing / standalone mode
if __name__ == "__main__":
    if not WATCHDOG_AVAILABLE:
        print("watchdog not installed - cannot run standalone test")
        exit(1)

    print("Media Watcher Standalone Test")
    print("=" * 50)
    print(f"Watching: {MediaWatcher.DEFAULT_WATCH_PATH}")
    print("Drop audio files into this folder to test detection")
    print("Press Ctrl+C to stop")
    print()

    def test_callback(filepath):
        print(f"\n*** DETECTED: {filepath} ***\n")

    watcher = MediaWatcher()
    watcher._handler.on_media_detected = test_callback
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        watcher.stop()
        print("Done")
