"""
Desktop application entrypoint for CDC Import & Cut-Stock Manager.
Runs Streamlit in a background thread and opens a native desktop window via pywebview.
"""
import os
import sys
import time
import socket
import threading
import urllib.request
from pathlib import Path
import webview

# Ensure correct base path whether running as a script or packaged binary
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

APP_PATH = BASE_DIR / "app.py"


def find_free_port(start_port=8510):
    port = start_port
    while port < 9000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return 8501


def wait_for_server(url, timeout=25):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=1) as resp:
                if resp.getcode() == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def run_streamlit(port):
    import streamlit.web.bootstrap as bootstrap

    # Disable signal handler registration which requires the main thread
    bootstrap._set_up_signal_handler = lambda server: None

    flag_options = {
        "server.port": port,
        "server.address": "127.0.0.1",
        "server.headless": True,
        "global.developmentMode": False,
        "browser.gatherUsageStats": False,
    }
    bootstrap.load_config_options(flag_options=flag_options)
    bootstrap.run(str(APP_PATH), is_hello=False, args=[], flag_options=flag_options)


def main():
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(target=run_streamlit, args=(port,), daemon=True)
    server_thread.start()

    if not wait_for_server(url):
        print(f"Failed to start Streamlit server on {url}", file=sys.stderr)
        sys.exit(1)

    # Launch native webview desktop window
    window = webview.create_window(
        title="CDC Import & Cut-Stock Manager",
        url=url,
        width=1320,
        height=880,
        min_size=(960, 640),
        text_select=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
