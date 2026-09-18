"""Windows-friendly local launcher for the Dera1.4 runtime."""

from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from dera.interface.api import app


HOST = "127.0.0.1"
PORT = 8765
SETUP_URL = f"http://{HOST}:{PORT}/app/setup.html"
DASHBOARD_URL = f"http://{HOST}:{PORT}/app/"


def runtime_is_running() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.4):
            return True
    except OSError:
        return False


def open_when_ready(url: str) -> None:
    for _ in range(40):
        if runtime_is_running():
            webbrowser.open(url)
            return
        time.sleep(0.25)


def _open_in_browser(url: str) -> None:
    webbrowser.open(url)


def _run_with_tray() -> None:
    """Keep the local runtime visible and controllable from the Windows tray."""
    try:
        from PIL import Image, ImageDraw
        import pystray
    except ImportError:
        logging.warning("Tray dependencies are unavailable; running Moon without a tray icon.")
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
        return

    image = Image.new("RGBA", (64, 64), (8, 17, 35, 255))
    drawing = ImageDraw.Draw(image)
    drawing.ellipse((8, 8, 56, 56), fill=(71, 115, 192, 255), outline=(201, 222, 255, 255), width=2)
    drawing.ellipse((18, 15, 43, 44), fill=(215, 231, 255, 255))
    drawing.ellipse((27, 11, 50, 35), fill=(71, 115, 192, 255))

    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, log_level="warning"))
    server_thread = threading.Thread(target=server.run, daemon=True, name="moon-local-runtime")
    server_thread.start()

    def show_status(icon, _item) -> None:
        message = "Moon is running locally at 127.0.0.1:8765." if runtime_is_running() else "Moon is starting. Please wait a moment."
        icon.notify(message, "Moon")

    def quit_moon(icon, _item) -> None:
        logging.info("Moon local runtime stopped from the tray.")
        server.should_exit = True
        icon.stop()

    icon = pystray.Icon(
        "Moon",
        image,
        "Moon — local runtime",
        menu=pystray.Menu(
            pystray.MenuItem("Open Moon", lambda _icon, _item: _open_in_browser(DASHBOARD_URL)),
            pystray.MenuItem("Open setup", lambda _icon, _item: _open_in_browser(SETUP_URL)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Check runtime status", show_status),
            pystray.MenuItem("Quit Moon", quit_moon),
        ),
    )
    icon.run()
    server_thread.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Moon's local Dera1.4 runtime.")
    parser.add_argument("--background", action="store_true", help="Run without opening Moon in a browser.")
    parser.add_argument("--setup", action="store_true", help="Open the first-launch setup page instead of the dashboard.")
    args = parser.parse_args()
    app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Moon"
    os.environ.setdefault("MOON_DATA_DIR", str(app_data / "data"))
    os.environ.setdefault("MOON_GUIDANCE_ONLY", "1")
    log_directory = app_data / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    try:
        logging.basicConfig(filename=log_directory / "MoonRuntime.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    except OSError:
        # A locked log must never stop the localhost runtime from starting.
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Moon local runtime launch requested.")
    launch_url = SETUP_URL if args.setup else DASHBOARD_URL
    if runtime_is_running():
        if not args.background:
            webbrowser.open(launch_url)
        return
    if not args.background:
        threading.Thread(target=open_when_ready, args=(launch_url,), daemon=True).start()
    if sys.platform == "win32":
        _run_with_tray()
    else:
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
