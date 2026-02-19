"""
Settings Management System for the Application
Handles theme, colors, and user preferences
"""
import json
import os
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict


class ThemeMode(Enum):
    """Theme mode enumeration"""
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


@dataclass
class ThemeColors:
    """Theme color configuration"""
    primary: str = "#4A90E2"  # Blue accent
    secondary: str = "#2A2E3E"  # Dark secondary
    background_main: str = "#0F1419"  # Main background
    background_alt: str = "#1A1E2E"  # Alternative background
    text_primary: str = "#E8EAED"  # Main text
    text_secondary: str = "#A0A7B3"  # Secondary text
    border: str = "#404855"  # Borders
    success: str = "#43A047"  # Success state
    danger: str = "#E53935"  # Danger state
    warning: str = "#FF9800"  # Warning state
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AppSettings:
    """Application settings"""
    theme_mode: str = ThemeMode.DARK.value
    save_path: str = ""
    custom_colors: dict = None
    
    def __post_init__(self):
        if self.custom_colors is None:
            self.custom_colors = {}


class SettingsManager:
    """Manages application settings and persistence"""
    
    SETTINGS_DIR = Path.home() / ".biometric_app"
    SETTINGS_FILE = SETTINGS_DIR / "settings.json"
    
    # Light theme colors
    LIGHT_THEME = ThemeColors(
        primary="#0066FF",
        secondary="#F5F5F5",
        background_main="#FFFFFF",
        background_alt="#F9F9F9",
        text_primary="#1A1A1A",
        text_secondary="#666666",
        border="#E0E0E0",
        success="#2E7D32",
        danger="#C62828",
        warning="#F57C00"
    )
    
    # Dark theme colors
    DARK_THEME = ThemeColors(
        primary="#4A90E2",
        secondary="#2A2E3E",
        background_main="#0F1419",
        background_alt="#1A1E2E",
        text_primary="#E8EAED",
        text_secondary="#A0A7B3",
        border="#404855",
        success="#43A047",
        danger="#E53935",
        warning="#FF9800"
    )
    
    def __init__(self):
        self.settings_dir = self.SETTINGS_DIR
        self.settings_file = self.SETTINGS_FILE
        self.settings_dir.mkdir(exist_ok=True)
        self._settings = None
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    self._settings = AppSettings(**data)
            else:
                self._settings = AppSettings()
        except Exception:
            self._settings = AppSettings()
    
    def save_settings(self):
        """Save settings to file"""
        try:
            data = {
                'theme_mode': self._settings.theme_mode,
                'save_path': self._settings.save_path,
                'custom_colors': self._settings.custom_colors
            }
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_theme_colors(self) -> ThemeColors:
        """Get current theme colors"""
        mode = self._settings.theme_mode
        if mode == ThemeMode.LIGHT.value:
            colors = self.LIGHT_THEME
        elif mode == ThemeMode.DARK.value:
            colors = self.DARK_THEME
        else:
            # SYSTEM: try to detect platform preference, fallback to LIGHT
            try:
                if self._system_prefers_light():
                    colors = self.LIGHT_THEME
                else:
                    colors = self.DARK_THEME
            except Exception:
                colors = self.LIGHT_THEME
        
        # Apply custom colors if set
        if self._settings.custom_colors:
            color_dict = colors.to_dict()
            color_dict.update(self._settings.custom_colors)
            colors = ThemeColors.from_dict(color_dict)
        
        return colors
    
    def set_theme_mode(self, mode: str):
        """Set theme mode"""
        if mode in [m.value for m in ThemeMode]:
            self._settings.theme_mode = mode
            self.save_settings()

    def _system_prefers_light(self) -> bool:
        """Try to detect if the OS/app prefers light theme. Returns True if light."""
        try:
            import platform
            if platform.system() == "Windows":
                try:
                    import winreg
                    registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                    key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    # AppsUseLightTheme == 1 => light
                    val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return bool(val)
                except Exception:
                    return True
            # macOS and Linux heuristics could be expanded; default to light
            return True
        except Exception:
            return True
    
    def set_save_path(self, path: str):
        """Set save path"""
        self._settings.save_path = path
        self.save_settings()
    
    def get_save_path(self) -> str:
        """Get save path"""
        return self._settings.save_path or os.getcwd()
    
    def set_custom_color(self, color_name: str, hex_color: str):
        """Set custom color"""
        self._settings.custom_colors[color_name] = hex_color
        self.save_settings()
    
    def reset_colors(self):
        """Reset colors to default"""
        self._settings.custom_colors = {}
        self.save_settings()
    
    def get_theme_mode(self) -> str:
        """Get current theme mode"""
        return self._settings.theme_mode


# Global settings manager instance
settings_manager = SettingsManager()
