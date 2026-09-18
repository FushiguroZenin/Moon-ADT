from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any
import winreg


class WindowsApplicationsObserver:
    """Read-only Windows registry and Startup-folder observation."""

    RUN_KEYS = ((winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "current_user"), (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "all_users"))

    def startup_entries(self) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for hive, key_path, scope in self.RUN_KEYS:
            try:
                with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ) as key:
                    index = 0
                    while True:
                        try:
                            name, command, _ = winreg.EnumValue(key, index)
                            entries.append({"name": name, "command": command, "source": f"registry:{scope}"})
                            index += 1
                        except OSError:
                            break
            except OSError:
                continue
        startup_folder = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup_folder.is_dir():
            for item in startup_folder.iterdir():
                if item.name.lower() == "desktop.ini":
                    continue
                entries.append({"name": item.name, "command": str(item), "source": "startup_folder:current_user"})
        return entries

    def inspect_startup_entry(self, name: str) -> dict[str, Any]:
        entry = next((item for item in self.startup_entries() if item["name"].lower() == name.lower()), None)
        if not entry:
            raise ValueError(f"Startup entry was not found: {name}")
        command = entry["command"].strip()
        candidate = command.split('"')[1] if command.startswith('"') and '"' in command[1:] else shlex.split(command, posix=False)[0]
        path = Path(os.path.expandvars(candidate))
        result: dict[str, Any] = {"entry": entry, "target_path": str(path), "target_exists": path.exists()}
        if path.is_file():
            stat = path.stat()
            result["metadata"] = {"extension": path.suffix.lower(), "size_mb": round(stat.st_size / 1024**2, 2), "modified_at": stat.st_mtime}
        return result

    def installed_applications(self, limit: int = 200) -> list[dict[str, Any]]:
        paths = (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")
        apps: dict[str, dict[str, str]] = {}
        for key_path in paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, index)) as child:
                                name = winreg.QueryValueEx(child, "DisplayName")[0]
                                apps[str(name)] = {"name": str(name), "version": str(self._value(child, "DisplayVersion") or "unknown"), "publisher": str(self._value(child, "Publisher") or "unknown")}
                        except OSError:
                            continue
            except OSError:
                continue
        return sorted(apps.values(), key=lambda app: app["name"].lower())[:limit]

    @staticmethod
    def _value(key: Any, name: str) -> str | None:
        try:
            return winreg.QueryValueEx(key, name)[0]
        except OSError:
            return None
