"""
Settings Dialog - Professional settings interface
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, 
    QPushButton, QComboBox, QLineEdit, QFileDialog, QGroupBox, 
    QGridLayout, QMessageBox, QColorDialog, QScrollArea
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
import subprocess
import os
from pathlib import Path
from settings import SettingsManager, ThemeMode, ThemeColors


class SettingsDialog(QDialog):
    """Professional settings dialog with theme and color customization"""
    
    def __init__(self, parent=None, on_theme_changed=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings")
        self.setMinimumSize(600, 500)
        self.settings_manager = SettingsManager()
        self.on_theme_changed = on_theme_changed
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        
        # Tabs
        tabs = QTabWidget()
        
        # General tab
        general_widget = self.create_general_tab()
        tabs.addTab(general_widget, "🏠 General")
        
        # Theme tab
        theme_widget = self.create_theme_tab()
        tabs.addTab(theme_widget, "🎨 Theme")
        
        # Colors tab
        colors_widget = self.create_colors_tab()
        tabs.addTab(colors_widget, "🌈 Colors")
        
        # About tab
        about_widget = self.create_about_tab()
        tabs.addTab(about_widget, "ℹ️ About")
        
        layout.addWidget(tabs)
        
        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        close_btn = QPushButton("✓ Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Save path
        path_group = QGroupBox("📁 Save Path")
        path_layout = QVBoxLayout()
        
        path_label = QLabel("Files will be saved to:")
        path_layout.addWidget(path_label)
        
        path_input_layout = QHBoxLayout()
        self.save_path_input = QLineEdit()
        self.save_path_input.setReadOnly(True)
        path_input_layout.addWidget(self.save_path_input)
        
        browse_btn = QPushButton("🗂️ Browse")
        browse_btn.clicked.connect(self.browse_save_path)
        path_input_layout.addWidget(browse_btn)
        
        path_layout.addLayout(path_input_layout)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # Logging
        log_group = QGroupBox("📝 Logging")
        log_layout = QVBoxLayout()
        
        log_label = QLabel("View application logs:")
        log_layout.addWidget(log_label)
        
        log_btn = QPushButton("📄 Open Log File")
        log_btn.clicked.connect(self.open_log_file)
        log_layout.addWidget(log_btn)
        
        clear_log_btn = QPushButton("🗑️ Clear Logs")
        clear_log_btn.clicked.connect(self.clear_logs)
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Info
        info_group = QGroupBox("ℹ️ Application Info")
        info_layout = QVBoxLayout()
        
        info_layout.addWidget(QLabel("Save Path:"))
        self.info_save_path = QLabel()
        info_layout.addWidget(self.info_save_path)
        
        info_layout.addWidget(QLabel("\nLog File Location:"))
        self.info_log_path = QLabel()
        info_layout.addWidget(self.info_log_path)
        
        info_layout.addWidget(QLabel("\nSettings Location:"))
        self.info_settings_path = QLabel()
        info_layout.addWidget(self.info_settings_path)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_theme_tab(self) -> QWidget:
        """Create theme settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Theme mode selection
        theme_group = QGroupBox("🎭 Theme Mode")
        theme_layout = QVBoxLayout()
        
        theme_desc = QLabel("Choose application theme:")
        theme_layout.addWidget(theme_desc)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 Dark", ThemeMode.DARK.value)
        self.theme_combo.addItem("☀️ Light", ThemeMode.LIGHT.value)
        self.theme_combo.addItem("💻 System", ThemeMode.SYSTEM.value)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed_combo)
        theme_layout.addWidget(self.theme_combo)
        
        theme_preview = QLabel(
            "Dark: Professional dark theme with blue accents\n"
            "Light: Clean light theme with blue accents\n"
            "System: Follow your system preference"
        )
        theme_preview.setStyleSheet("color: gray; font-size: 11px;")
        theme_layout.addWidget(theme_preview)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Theme demo
        demo_group = QGroupBox("👁️ Preview")
        demo_layout = QVBoxLayout()
        
        demo_label = QLabel("Sample buttons in current theme:")
        demo_layout.addWidget(demo_label)
        
        demo_btn_layout = QHBoxLayout()
        
        demo_primary = QPushButton("Primary Button")
        demo_primary.setEnabled(True)
        demo_btn_layout.addWidget(demo_primary)
        
        demo_secondary = QPushButton("Secondary")
        demo_secondary.setObjectName("secondary")
        demo_btn_layout.addWidget(demo_secondary)
        
        demo_success = QPushButton("Success")
        demo_success.setObjectName("success")
        demo_btn_layout.addWidget(demo_success)
        
        demo_danger = QPushButton("Danger")
        demo_danger.setObjectName("danger")
        demo_btn_layout.addWidget(demo_danger)
        
        demo_layout.addLayout(demo_btn_layout)
        demo_group.setLayout(demo_layout)
        layout.addWidget(demo_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_colors_tab(self) -> QWidget:
        """Create color customization tab"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout()
        
        # Color picker group
        color_group = QGroupBox("🎨 Accent Colors")
        color_layout = QGridLayout()
        
        self.color_buttons = {}
        colors_to_show = [
            ('primary', 'Primary Accent'),
            ('secondary', 'Secondary Background'),
            ('border', 'Borders'),
            ('success', 'Success Color'),
            ('danger', 'Danger Color'),
            ('warning', 'Warning Color'),
        ]
        
        row = 0
        for color_key, color_label in colors_to_show:
            label = QLabel(color_label)
            color_layout.addWidget(label, row, 0)
            
            # Color preview button
            btn = QPushButton()
            btn.setMaximumWidth(60)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, key=color_key: self.pick_color(key))
            self.color_buttons[color_key] = btn
            color_layout.addWidget(btn, row, 1)
            
            # Hex input
            hex_input = QLineEdit()
            hex_input.setPlaceholderText("#XXXXXX")
            hex_input.setMaximumWidth(100)
            hex_input.textChanged.connect(lambda text, key=color_key: self.on_hex_color_changed(key, text))
            self.color_buttons[f'{color_key}_input'] = hex_input
            color_layout.addWidget(hex_input, row, 2)
            
            row += 1
        
        color_layout.setColumnStretch(3, 1)
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Reset colors
        reset_colors_btn = QPushButton("🔄 Reset Colors to Default")
        reset_colors_btn.clicked.connect(self.reset_colors)
        layout.addWidget(reset_colors_btn)
        
        # Info
        info_label = QLabel(
            "💡 Tip: Click color buttons to pick colors, or enter hex values directly.\n"
            "Changes apply immediately."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_about_tab(self) -> QWidget:
        """Create about tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🔐 Security System")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Version
        layout.addWidget(QLabel("Version: 2.0.0\nEnterprise Edition"))
        
        # Features
        layout.addSpacing(20)
        layout.addWidget(QLabel("Features:"))
        features = QLabel(
            "✓ Face Detection with Haar Cascade\n"
            "✓ YOLO Neural Network Object Detection\n"
            "✓ USB Phone Camera Support\n"
            "✓ IP Camera Streaming\n"
            "✓ Motion-triggered Recording\n"
            "✓ Object Recognition & Learning\n"
            "✓ Professional Theme System\n"
            "✓ Customizable Colors & Accents"
        )
        features.setStyleSheet("color: gray;")
        layout.addWidget(features)
        
        # Technology
        layout.addSpacing(20)
        layout.addWidget(QLabel("Technology Stack:"))
        tech = QLabel(
            "• Python 3.8+\n"
            "• PySide6 (Qt Framework)\n"
            "• OpenCV\n"
            "• YOLO (Ultralytics)\n"
            "• Android Debug Bridge (ADB)"
        )
        tech.setStyleSheet("color: gray;")
        layout.addWidget(tech)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def browse_save_path(self):
        """Browse for save path"""
        path = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if path:
            self.save_path_input.setText(path)
            self.settings_manager.set_save_path(path)
            self.update_info_labels()
    
    def open_log_file(self):
        """Open log file in system editor"""
        log_file = Path("logs") / "faceapp_logging.log"
        if log_file.exists():
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(log_file.parent)
                else:  # Linux/Mac
                    subprocess.Popen(['xdg-open', str(log_file.parent)])
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open log file: {e}")
        else:
            QMessageBox.information(self, "Info", "Log file not found yet. Start the application to generate logs.")
    
    def clear_logs(self):
        """Clear log file"""
        log_file = Path("logs") / "faceapp_logging.log"
        if log_file.exists():
            reply = QMessageBox.question(
                self, "Confirm",
                "Clear all logs? This action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    log_file.write_text("")
                    QMessageBox.information(self, "Success", "Logs cleared.")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not clear logs: {e}")
    
    def pick_color(self, color_key: str):
        """Open color picker"""
        current_color = self.color_buttons[f'{color_key}_input'].text()
        
        try:
            color = QColorDialog.getColor(QColor(current_color) if current_color.startswith('#') else QColor(0, 166, 226))
            if color.isValid():
                hex_color = color.name()
                self.color_buttons[f'{color_key}_input'].setText(hex_color)
                self.settings_manager.set_custom_color(color_key, hex_color)
                self.update_color_buttons()
                if self.on_theme_changed:
                    self.on_theme_changed()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Color picker error: {e}")
    
    def on_hex_color_changed(self, color_key: str, hex_color: str):
        """Handle hex color input change"""
        if hex_color.startswith('#') and len(hex_color) == 7:
            try:
                QColor(hex_color)
                self.settings_manager.set_custom_color(color_key, hex_color)
                self.update_color_buttons()
                if self.on_theme_changed:
                    self.on_theme_changed()
            except Exception:
                pass
    
    def on_theme_changed_combo(self):
        """Handle theme change"""
        mode = self.theme_combo.currentData()
        self.settings_manager.set_theme_mode(mode)
        if self.on_theme_changed:
            self.on_theme_changed()
    
    def reset_colors(self):
        """Reset colors to default"""
        reply = QMessageBox.question(
            self, "Confirm",
            "Reset all colors to default?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_colors()
            self.load_settings()
            if self.on_theme_changed:
                self.on_theme_changed()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self, "Confirm",
            "Reset all settings to defaults? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_colors()
            self.settings_manager.set_theme_mode(ThemeMode.DARK.value)
            self.load_settings()
            if self.on_theme_changed:
                self.on_theme_changed()
    
    def load_settings(self):
        """Load current settings into UI"""
        # Load theme
        theme_mode = self.settings_manager.get_theme_mode()
        index = self.theme_combo.findData(theme_mode)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        # Load save path
        self.save_path_input.setText(self.settings_manager.get_save_path())
        
        # Update color buttons
        self.update_color_buttons()
        
        # Update info labels
        self.update_info_labels()
    
    def update_color_buttons(self):
        """Update color button displays"""
        colors = self.settings_manager.get_theme_colors()
        color_dict = colors.to_dict()
        
        for color_key in self.color_buttons:
            if not color_key.endswith('_input'):
                hex_color = color_dict.get(color_key, '#000000')
                self.color_buttons[color_key].setStyleSheet(
                    f"background-color: {hex_color}; border-radius: 4px; border: 1px solid gray;"
                )
                self.color_buttons[f'{color_key}_input'].setText(hex_color)
    
    def update_info_labels(self):
        """Update information labels"""
        save_path = self.settings_manager.get_save_path()
        self.info_save_path.setText(save_path)
        
        log_path = Path("logs") / "faceapp_logging.log"
        self.info_log_path.setText(str(log_path.absolute()))
        
        settings_path = self.settings_manager.settings_file
        self.info_settings_path.setText(str(settings_path.absolute()))
