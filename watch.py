import threading
import subprocess
import time
import os
from pathlib import Path


def _watch_file_worker(path, interval, file_path):
    """
    Internal loop:
      • Ensure file exists.
      • Read & strip non-blank lines (assumed to be URLs).
      • For each URL, run `curl -sSL <url>` and print the first 120 bytes
        of the response (or handle the output however you like).
      • Rewrite the file with any URLs that failed.
      • Sleep `interval` seconds and repeat.
    """
    keep_going = True
    while keep_going:
        if keep_going == True:
            # 1) guarantee the file is there
            path.touch(exist_ok=True)

            # 2) snapshot & clear the file in a single open call
            with path.open("r+", encoding="utf-8") as f:
                urls = [ln.strip() for ln in f if ln.strip()]
                f.seek(0)
                f.truncate()          # blank the file right away

        leftovers: list[str] = []

        # 3) process each URL
        for url in urls:
            
            try:
                # use curl so redirects/https just work
                result = subprocess.run(
                    ["curl", "-sSL", url],
                    text=True,
                    capture_output=True,
                    timeout=5,
                    check=True,
                )
                # demo: print a short snippet; swap in your own handler
                snippet = result.stdout[:120].replace("\n", " ") + "..."
                print(f"[{time.ctime()}] {url} → {len(result.stdout):,} B | {snippet}")
                keep_going = False
                os.remove(file_path)
            except Exception as exc:
                print(f"[{time.ctime()}] ERROR fetching {url}: {exc}")
                leftovers.append(url)

        # 4) rewrite any that failed
        if leftovers:
            with path.open("a", encoding="utf-8") as f:
                f.writelines(url + "\n it failed " +f({path}) for url in leftovers)
                keep_going = False
                os.remove(file_path)

        time.sleep(interval)


def start_url_watcher(file_path: str = "urls.txt", interval: float = 1.0) -> threading.Thread:
    """
    Launch the watcher thread.
    Returns the Thread object (daemon=True, so it won’t block interpreter exit).
    """
    thread = threading.Thread(
        target=_watch_file_worker,
        args=(Path(file_path).expanduser(), interval,file_path),
        daemon=True,
        name="URLWatcher",
    )
    thread.start()
    return thread

start_url_watcher("urls.txt", 1.0)
