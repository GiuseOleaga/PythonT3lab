"""
Theme Engine - Generates QSS stylesheets dynamically
"""
from settings import ThemeColors


class ThemeEngine:
    """Dynamically generates QSS stylesheets based on color theme"""
    
    @staticmethod
    def generate_stylesheet(colors: ThemeColors) -> str:
        """Generate complete QSS stylesheet from theme colors"""
        
        # Pre-calculate light/dark color variations for use in f-string
        primary_light_20 = ThemeEngine._lighten_color(colors.primary, 20)
        primary_light_15 = ThemeEngine._lighten_color(colors.primary, 15)
        primary_dark_20 = ThemeEngine._darken_color(colors.primary, 20)
        secondary_light_10 = ThemeEngine._lighten_color(colors.secondary, 10)
        danger_light_10 = ThemeEngine._lighten_color(colors.danger, 10)
        success_light_10 = ThemeEngine._lighten_color(colors.success, 10)
        background_alt_light_5 = ThemeEngine._lighten_color(colors.background_alt, 5)
        border_light_20 = ThemeEngine._lighten_color(colors.border, 20)
        
        qss = f"""
/* ===================================================================================== */
/* AUTO-GENERATED PROFESSIONAL THEME */
/* ===================================================================================== */

/* ========================== Main Window & Base ========================== */
QWidget {{
    background-color: {colors.background_main};
    color: {colors.text_primary};
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 12px;
}}

/* ========================== Scrollbar ========================== */
QScrollBar:vertical {{
    background-color: {colors.background_alt};
    width: 12px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {colors.primary};
    border-radius: 6px;
    min-height: 20px;
    margin: 2px 0px 2px 0px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {primary_light_20};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

/* ========================== Labels ========================== */
QLabel {{
    color: {colors.text_primary};
    font-size: 12px;
    padding: 2px 0px;
}}

QLabel#title {{
    font-size: 16px;
    font-weight: 600;
    color: {colors.primary};
    padding: 4px 0px;
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {colors.text_secondary};
    padding: 2px 0px;
}}

/* ========================== Buttons - Primary ========================== */
QPushButton {{
    background-color: {colors.primary};
    color: white;
    font-size: 12px;
    font-weight: 600;
    padding: 12px 18px;
    border: none;
    border-radius: 8px;
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: {primary_light_15};
}}

QPushButton:pressed {{
    background-color: {primary_dark_20};
}}

QPushButton:disabled {{
    background-color: {colors.secondary};
    color: {colors.text_secondary};
}}

/* ========================== Buttons - Secondary ========================== */
QPushButton#secondary {{
    background-color: {colors.secondary};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
}}

QPushButton#secondary:hover {{
    background-color: {secondary_light_10};
    border: 1px solid {colors.primary};
}}

/* ========================== Buttons - Danger ========================== */
QPushButton#danger {{
    background-color: {colors.danger};
    color: white;
}}

QPushButton#danger:hover {{
    background-color: {danger_light_10};
}}

/* ========================== Buttons - Success ========================== */
QPushButton#success {{
    background-color: {colors.success};
    color: white;
}}

QPushButton#success:hover {{
    background-color: {success_light_10};
}}

/* ========================== ComboBox & LineEdit ========================== */
QComboBox, QLineEdit {{
    background-color: {colors.background_alt};
    color: {colors.text_primary};
    font-size: 12px;
    padding: 10px 14px;
    border: 1px solid {colors.border};
    border-radius: 6px;
    min-height: 36px;
    selection-background-color: {colors.primary};
}}

QComboBox:focus, QLineEdit:focus {{
    border: 2px solid {colors.primary};
    background-color: {background_alt_light_5};
}}

QComboBox:hover, QLineEdit:hover {{
    border: 1px solid {border_light_20};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {colors.border};
}}

QComboBox QAbstractItemView {{
    background-color: {colors.background_alt};
    color: {colors.text_primary};
    selection-background-color: {colors.primary};
    border: 1px solid {colors.border};
}}

/* ========================== GroupBox ========================== */
QGroupBox {{
    border: 1px solid {colors.border};
    border-radius: 8px;
    margin-top: 16px;
    font-weight: 600;
    font-size: 13px;
    padding: 16px;
    color: {colors.primary};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    margin-left: 8px;
    color: {colors.primary};
}}

/* ========================== Slider ========================== */
QSlider::groove:horizontal {{
    border: none;
    height: 8px;
    background: {colors.secondary};
    border-radius: 4px;
    margin: 6px 0;
}}

QSlider::handle:horizontal {{
    background: {colors.primary};
    border: none;
    width: 20px;
    margin: -6px 0;
    border-radius: 10px;
}}

QSlider::handle:horizontal:hover {{
    background: {primary_light_15};
}}

/* ========================== CheckBox ========================== */
QCheckBox {{
    color: {colors.text_primary};
    spacing: 10px;
    font-size: 12px;
    padding: 4px 0px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {colors.border};
    background-color: {colors.background_alt};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {colors.primary};
    background-color: {background_alt_light_5};
}}

QCheckBox::indicator:checked {{
    background-color: {colors.primary};
    border: 1px solid {colors.primary};
}}

/* ========================== SpinBox ========================== */
QSpinBox, QDoubleSpinBox {{
    background-color: {colors.background_alt};
    color: {colors.text_primary};
    padding: 8px 12px;
    border: 1px solid {colors.border};
    border-radius: 6px;
    min-height: 36px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {colors.primary};
}}

/* ========================== Video Display ========================== */
QLabel#video_label {{
    border: 2px solid {colors.border};
    background-color: #000000;
    border-radius: 8px;
}}

/* ========================== ScrollArea ========================== */
QScrollArea {{
    background-color: {colors.background_main};
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: {colors.background_main};
}}

/* ========================== Dialog ========================== */
QDialog {{
    background-color: {colors.background_main};
}}

QDialog QLabel {{
    color: {colors.text_primary};
}}

QDialog QPushButton {{
    min-width: 80px;
}}

/* ========================== Menu ========================== */
QMenuBar {{
    background-color: {colors.background_alt};
    color: {colors.text_primary};
    border-bottom: 1px solid {colors.border};
}}

QMenuBar::item:selected {{
    background-color: {colors.primary};
}}

QMenu {{
    background-color: {colors.background_alt};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
}}

QMenu::item:selected {{
    background-color: {colors.primary};
    color: white;
}}

/* ========================== Tabs ========================== */
QTabBar::tab {{
    background-color: {colors.secondary};
    color: {colors.text_primary};
    padding: 8px 20px;
    border: 1px solid {colors.border};
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {colors.primary};
    color: white;
}}

QTabWidget::pane {{
    border: 1px solid {colors.border};
}}

/* ========================== TreeView/ListView ========================== */
QTreeView, QListView {{
    background-color: {colors.background_alt};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    gridline-color: {colors.border};
    selection-background-color: {colors.primary};
}}

QTreeView::item:selected, QListView::item:selected {{
    background-color: {colors.primary};
}}

/* ========================== HeaderView ========================== */
QHeaderView::section {{
    background-color: {colors.secondary};
    color: {colors.text_primary};
    padding: 5px;
    border: 1px solid {colors.border};
}}

/* ========================== ProgressBar ========================== */
QProgressBar {{
    border: 1px solid {colors.border};
    border-radius: 6px;
    background-color: {colors.background_alt};
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {colors.primary};
    border-radius: 4px;
}}

/* ========================== ToolTip ========================== */
QToolTip {{
    background-color: {colors.secondary};
    color: {colors.text_primary};
    border: 1px solid {colors.border};
    border-radius: 4px;
    padding: 4px;
}}
"""
        return qss
    
    @staticmethod
    def _lighten_color(hex_color: str, amount: int) -> str:
        """Lighten a hex color by a percentage"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(min(255, int(c + (255 - c) * amount / 100)) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    @staticmethod
    def _darken_color(hex_color: str, amount: int) -> str:
        """Darken a hex color by a percentage"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        rgb = tuple(max(0, int(c * (1 - amount / 100))) for c in rgb)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
