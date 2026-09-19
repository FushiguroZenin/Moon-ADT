from __future__ import annotations

import os
import sys
from pathlib import Path


class StartupPreference:
    """Opt-in Windows sign-in launch for Moon's local runtime."""

    VALUE_NAME = "MoonRuntime"
    KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @staticmethod
    def _command() -> str:
        if getattr(sys, "frozen", False):
            executable = Path(sys.executable)
            return f'"{executable}" --background'
        runtime = Path(__file__).resolve().parents[2] / "moon_runtime.py"
        return f'"{sys.executable}" "{runtime}" --background'

    def status(self) -> dict:
        if os.name != "nt":
            return {"supported": False, "enabled": False}
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.KEY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, self.VALUE_NAME)
            return {"supported": True, "enabled": bool(value), "command": value}
        except FileNotFoundError:
            return {"supported": True, "enabled": False}

    def set_enabled(self, enabled: bool) -> dict:
        if os.name != "nt":
            raise RuntimeError("Start with Windows is available only on Windows.")
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.KEY_PATH) as key:
            if enabled:
                winreg.SetValueEx(key, self.VALUE_NAME, 0, winreg.REG_SZ, self._command())
            else:
                try:
                    winreg.DeleteValue(key, self.VALUE_NAME)
                except FileNotFoundError:
                    pass
        return self.status()
