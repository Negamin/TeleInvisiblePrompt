#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Invisible Teleprompter
A transparent, always-on-top teleprompter that's invisible to screen capture software.
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                            QSlider, QComboBox, QColorDialog, QShortcut, QFrame, QSizeGrip)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QFont, QColor, QKeySequence, QPalette, QFontDatabase

class TeleprompterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window attributes to make it transparent and always on top
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool  # This helps with not showing in taskbar
        )
        # Force window to stay on top
        self.setWindowFlag(Qt.X11BypassWindowManagerHint)
        
        # Add resize handles
        self.setMinimumSize(300, 200)  # Set minimum size
        self.resize_enabled = True
        
        # State variables
        self.locked = False
        self.scrolling = False
        self.scroll_speed = 1
        self.transparency = 0.8  # 80% opaque by default
        self.font_color = QColor(255, 255, 255)  # White by default
        self.font_size = 18
        self.font_family = "Arial"
        self.dragging = False
        self.drag_position = None
        # Initialize UI
        self.init_ui()
        
        # Setup shortcuts
        self.setup_shortcuts()
        
        # Create a special emergency unlock shortcut that always works
        # Using installEventFilter to ensure shortcuts work even when locked
        self.installEventFilter(self)
        
        # Create emergency unlock shortcut
        self.emergency_unlock_shortcut = QShortcut(QKeySequence("Ctrl+Alt+U"), self)
        self.emergency_unlock_shortcut.activated.connect(self.emergency_unlock)
        
        # Auto-scroll timer
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.auto_scroll)

    def init_ui(self):
        # Main container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Set transparent background
        self.central_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        
        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        
        # Control panel (initially visible)
        self.control_panel = QFrame()
        self.control_panel.setFrameShape(QFrame.StyledPanel)
        self.control_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 0.8);
                border-radius: 10px;
                padding: 5px;
            }
            QPushButton {
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                border-radius: 5px;
                padding: 5px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 0.9);
            }
            QLabel {
                color: white;
            }
            QComboBox, QSlider {
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                border-radius: 5px;
            }
        """)
        
        control_layout = QVBoxLayout(self.control_panel)
        
        # Font selection
        font_layout = QHBoxLayout()
        font_label = QLabel("Font:")
        font_label.setStyleSheet("color: white;")
        self.font_combo = QComboBox()
        self.load_fonts()
        self.font_combo.currentTextChanged.connect(self.change_font_family)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_combo)
        control_layout.addLayout(font_layout)
        
        # Font size
        size_layout = QHBoxLayout()
        size_label = QLabel("Size:")
        size_label.setStyleSheet("color: white;")
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(8)
        self.size_slider.setMaximum(72)
        self.size_slider.setValue(self.font_size)
        self.size_slider.valueChanged.connect(self.change_font_size)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        control_layout.addLayout(size_layout)
        
        # Font color
        color_layout = QHBoxLayout()
        color_label = QLabel("Font Color:")
        color_label.setStyleSheet("color: white;")
        self.color_button = QPushButton("")
        self.color_button.setToolTip("Clique para mudar a cor da fonte (Ctrl+C)")
        self.color_button.setStyleSheet(f"background-color: rgb({self.font_color.red()}, {self.font_color.green()}, {self.font_color.blue()}); min-width: 30px; min-height: 20px; border-radius: 3px;")
        self.color_button.clicked.connect(self.change_font_color)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_button)
        control_layout.addLayout(color_layout)
        
        # Transparency
        trans_layout = QHBoxLayout()
        trans_label = QLabel("Transparency:")
        trans_label.setStyleSheet("color: white;")
        self.trans_slider = QSlider(Qt.Horizontal)
        self.trans_slider.setMinimum(10)  # 10% minimum opacity
        self.trans_slider.setMaximum(100)  # 100% maximum opacity
        self.trans_slider.setValue(int(self.transparency * 100))
        self.trans_slider.valueChanged.connect(self.change_transparency)
        trans_layout.addWidget(trans_label)
        trans_layout.addWidget(self.trans_slider)
        control_layout.addLayout(trans_layout)
        
        # Scroll speed
        scroll_layout = QHBoxLayout()
        scroll_label = QLabel("Scroll Speed:")
        scroll_label.setStyleSheet("color: white;")
        self.scroll_slider = QSlider(Qt.Horizontal)
        self.scroll_slider.setMinimum(1)
        self.scroll_slider.setMaximum(10)
        self.scroll_slider.setValue(self.scroll_speed)
        self.scroll_slider.valueChanged.connect(self.change_scroll_speed)
        scroll_layout.addWidget(scroll_label)
        scroll_layout.addWidget(self.scroll_slider)
        control_layout.addLayout(scroll_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.lock_button = QPushButton("Lock Position")
        self.lock_button.clicked.connect(self.toggle_lock)
        
        self.scroll_button = QPushButton("Start Scrolling")
        self.scroll_button.clicked.connect(self.toggle_scrolling)
        
        button_layout.addWidget(self.lock_button)
        button_layout.addWidget(self.scroll_button)
        control_layout.addLayout(button_layout)
        
        # Text edit area
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(20, 20, 20, 0.3);
                color: rgb({self.font_color.red()}, {self.font_color.green()}, {self.font_color.blue()});
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 5px;
                padding: 5px;
            }}
        """)
        # Set placeholder text
        self.text_edit.setPlaceholderText("Digite ou cole seu texto aqui...")
        self.text_edit.setFont(QFont(self.font_family, self.font_size))
        
        # Add widgets to main layout
        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(self.text_edit)
        
        # Add size grip
        size_grip = QSizeGrip(self.central_widget)
        size_grip.setStyleSheet("background-color: rgba(40, 40, 40, 0.8); border-radius: 5px;")
        main_layout.addWidget(size_grip, alignment=Qt.AlignBottom | Qt.AlignRight)
        
        # Set default size and position
        self.resize(600, 400)
        self.move(100, 100)
        
        # Show the window
        self.show()
        
        # Set window opacity
        self.setWindowOpacity(self.transparency)

    def load_fonts(self):
        """Load system fonts into the font combo box"""
        font_db = QFontDatabase()
        for family in font_db.families():
            self.font_combo.addItem(family)
        
        # Set default font
        index = self.font_combo.findText(self.font_family)
        if index >= 0:
            self.font_combo.setCurrentIndex(index)

    def setup_shortcuts(self):
        # Lock/unlock shortcut (Ctrl+L)
        self.lock_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.lock_shortcut.activated.connect(self.toggle_lock)
        
        # Toggle scrolling (Ctrl+S)
        self.scroll_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.scroll_shortcut.activated.connect(self.toggle_scrolling)
        
        # Font color shortcut (Ctrl+C)
        self.color_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.color_shortcut.activated.connect(self.change_font_color)
        
        # Increase scroll speed (Ctrl+Up)
        self.speed_up_shortcut = QShortcut(QKeySequence("Ctrl+Up"), self)
        self.speed_up_shortcut.activated.connect(self.increase_scroll_speed)
        
        # Decrease scroll speed (Ctrl+Down)
        self.speed_down_shortcut = QShortcut(QKeySequence("Ctrl+Down"), self)
        self.speed_down_shortcut.activated.connect(self.decrease_scroll_speed)
        
        # Manual scroll up (Shift+Up)
        self.scroll_up_shortcut = QShortcut(QKeySequence("Shift+Up"), self)
        self.scroll_up_shortcut.activated.connect(self.scroll_up)
        
        # Manual scroll down (Shift+Down)
        self.scroll_down_shortcut = QShortcut(QKeySequence("Shift+Down"), self)
        self.scroll_down_shortcut.activated.connect(self.scroll_down)
        
        # Toggle control panel visibility (Ctrl+H)
        self.hide_controls_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        self.hide_controls_shortcut.activated.connect(self.toggle_controls)

    def toggle_lock(self):
        self.locked = not self.locked
        
        if self.locked:
            # When locked, enable partial click-through but keep on top
            self.setWindowFlags(
                Qt.FramelessWindowHint | 
                Qt.WindowStaysOnTopHint | 
                Qt.Tool |
                Qt.X11BypassWindowManagerHint
            )
            self.lock_button.setText("Unlock Position")
            # Desabilitar controles e edição
            self.font_combo.setEnabled(False)
            self.size_slider.setEnabled(False)
            self.color_button.setEnabled(False)
            self.trans_slider.setEnabled(False)
            self.scroll_slider.setEnabled(False)
            self.text_edit.setReadOnly(True)
            # Só manter botões de lock e scroll habilitados
            self.lock_button.setEnabled(True)
            self.scroll_button.setEnabled(True)
            print("Teleprompter travado. Use Ctrl+Alt+U para destravar em caso de emergência.")
        else:
            # When unlocked, disable click-through completamente
            self.setWindowFlags(
                Qt.FramelessWindowHint | 
                Qt.WindowStaysOnTopHint | 
                Qt.Tool |
                Qt.X11BypassWindowManagerHint
            )
            self.lock_button.setText("Lock Position")
            # Habilitar tudo de novo
            self.font_combo.setEnabled(True)
            self.size_slider.setEnabled(True)
            self.color_button.setEnabled(True)
            self.trans_slider.setEnabled(True)
            self.scroll_slider.setEnabled(True)
            self.text_edit.setReadOnly(False)
            self.lock_button.setEnabled(True)
            self.scroll_button.setEnabled(True)
        self.show()
        self.activateWindow()
        self.raise_()

    def toggle_scrolling(self):
        self.scrolling = not self.scrolling
        
        if self.scrolling:
            # Start scrolling
            self.scroll_timer.start(50)  # Update every 50ms
            self.scroll_button.setText("Stop Scrolling")
        else:
            # Stop scrolling
            self.scroll_timer.stop()
            self.scroll_button.setText("Start Scrolling")

    def auto_scroll(self):
        # Move the scroll bar down by the current scroll speed
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + self.scroll_speed)

    def scroll_up(self):
        # Manual scroll up
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - 10)

    def scroll_down(self):
        # Manual scroll down
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + 10)

    def increase_scroll_speed(self):
        # Increase scroll speed
        self.scroll_speed = min(self.scroll_speed + 1, 10)
        self.scroll_slider.setValue(self.scroll_speed)

    def decrease_scroll_speed(self):
        # Decrease scroll speed
        self.scroll_speed = max(self.scroll_speed - 1, 1)
        self.scroll_slider.setValue(self.scroll_speed)

    def change_scroll_speed(self, value):
        # Update scroll speed from slider
        self.scroll_speed = value

    def change_font_family(self, family):
        # Update font family
        self.font_family = family
        font = self.text_edit.font()
        font.setFamily(family)
        self.text_edit.setFont(font)

    def change_font_size(self, size):
        # Update font size
        self.font_size = size
        font = self.text_edit.font()
        font.setPointSize(size)
        self.text_edit.setFont(font)

    def change_font_color(self):
        # Open color dialog always on top and beside the main window
        dialog = QColorDialog(self.font_color, self)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        # Position dialog to the right of the main window
        geo = self.geometry()
        dialog.move(geo.x() + geo.width() + 10, geo.y())
        if dialog.exec_():
            color = dialog.selectedColor()
            if color.isValid():
                self.font_color = color
                # Update the color button to show the selected color
                self.color_button.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); min-width: 30px; min-height: 20px; border-radius: 3px;")
                # Update the text edit color
                self.text_edit.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: rgba(20, 20, 20, 0.3);
                        color: rgb({color.red()}, {color.green()}, {color.blue()});
                        border: 1px solid rgba(100, 100, 100, 0.5);
                        border-radius: 5px;
                        padding: 5px;
                    }}
                """)

    def change_transparency(self, value):
        # Update window transparency
        self.transparency = value / 100.0
        self.setWindowOpacity(self.transparency)

    def toggle_controls(self):
        # Toggle visibility of control panel
        self.control_panel.setVisible(not self.control_panel.isVisible())

    def emergency_unlock(self):
        """Destrava o teleprompter em caso de emergência."""
        if self.locked:
            self.toggle_lock()


    def mousePressEvent(self, event):
        # Check for resize operations in the corners and edges
        rect = self.rect()
        corner_size = 20
        
        # Bottom-right corner (resize)
        if self.resize_enabled and rect.bottomRight().x() - event.x() < corner_size and rect.bottomRight().y() - event.y() < corner_size:
            self.setCursor(Qt.SizeFDiagCursor)
            self.dragging = False
            self.resizing = True
            self.resize_start_pos = event.globalPos()
            self.resize_start_size = self.size()
            event.accept()
            return
        
        # Allow clicking the lock button even when locked
        if self.locked and self.lock_button.underMouse():
            self.toggle_lock()
            return
            
        if not self.locked and event.button() == Qt.LeftButton:
            self.dragging = True
            self.resizing = False
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        # Handle resizing
        if self.resize_enabled and hasattr(self, 'resizing') and self.resizing and event.buttons() == Qt.LeftButton:
            diff = event.globalPos() - self.resize_start_pos
            new_width = max(self.minimumWidth(), self.resize_start_size.width() + diff.x())
            new_height = max(self.minimumHeight(), self.resize_start_size.height() + diff.y())
            self.resize(new_width, new_height)
            event.accept()
            return
            
        # Handle dragging
        if not self.locked and self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
        # Show resize cursor when hovering over corner
        if self.resize_enabled:
            rect = self.rect()
            corner_size = 20
            if rect.bottomRight().x() - event.x() < corner_size and rect.bottomRight().y() - event.y() < corner_size:
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            if hasattr(self, 'resizing'):
                self.resizing = False
            event.accept()

    def eventFilter(self, obj, event):
        """Event filter to ensure shortcuts work even when locked"""
        if event.type() == event.KeyPress:
            # Sempre permitem destravar e start/stop scroll
            if event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
                self.toggle_lock()
                return True
            elif event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
                self.toggle_scrolling()
                return True
            if self.locked:
                # Bloquear todos os outros atalhos quando travado
                return True
            # Quando destravado, atalhos normais
            if event.key() == Qt.Key_Up and event.modifiers() == Qt.ShiftModifier:
                self.scroll_up()
                return True
            elif event.key() == Qt.Key_Down and event.modifiers() == Qt.ShiftModifier:
                self.scroll_down()
                return True
            elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
                self.change_font_color()
                return True
            elif event.key() == Qt.Key_H and event.modifiers() == Qt.ControlModifier:
                self.toggle_controls()
                return True
            elif event.key() == Qt.Key_Up and event.modifiers() == Qt.ControlModifier:
                self.increase_scroll_speed()
                return True
            elif event.key() == Qt.Key_Down and event.modifiers() == Qt.ControlModifier:
                self.decrease_scroll_speed()
                return True
        return super().eventFilter(obj, event)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Invisible Teleprompter")
    app.setOrganizationName("Teleprompter")
    
    # Create and show the teleprompter window
    teleprompter = TeleprompterWindow()
    teleprompter.activateWindow()
    teleprompter.raise_()
    
    # Print instructions for emergency unlock
    print("\nTeleprompter iniciado!")
    print("Atalhos de teclado:")
    print("  Ctrl+L: Travar/destravar posição")
    print("  Ctrl+Alt+U: Destravar em caso de emergência")
    print("  Ctrl+S: Iniciar/parar rolagem")
    print("  Ctrl+C: Mudar cor da fonte")
    print("  Ctrl+H: Mostrar/esconder painel de controle")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
