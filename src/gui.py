import sys
from PyQt5.QtWidgets import (QMainWindow, QAction, QVBoxLayout, QWidget, QLabel,
                             QTextEdit, QListWidget, QPushButton, QMessageBox, QDialog,
                             QFormLayout, QDialogButtonBox, QComboBox, QDockWidget,
                             QApplication, QLineEdit)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QPropertyAnimation, QRect
import pyautogui, keyboard
from src.macro_manager import set_macro, save_macros, reload_macros, delete_macro
from src.serial_manager import SerialManager

class GuiUpdater(QObject):
    updateTextSignal = pyqtSignal(str)
    executeMacroSignal = pyqtSignal(str)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        layout = QFormLayout(self)
        self.portInput = QLineEdit(self)
        self.portInput.setPlaceholderText('COM20')
        layout.addRow('Serial Port:', self.portInput)
        self.baudRateInput = QLineEdit(self)
        self.baudRateInput.setPlaceholderText('115200')
        layout.addRow('Baud Rate:', self.baudRateInput)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def getSettings(self):
        return self.portInput.text(), self.baudRateInput.text()

class MacroPadApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_manager = SerialManager(self.handle_received_data, 'COM1', 115200)
        self.decodedVar = ""
        self.guiUpdater = GuiUpdater()
        self.guiUpdater.updateTextSignal.connect(self.updateReceivedDataDisplay)
        self.guiUpdater.executeMacroSignal.connect(self.execute_macro)

        self.initUI()
        self.load_macros_and_update_list()

    def initUI(self):
        self.setWindowTitle('MacroPad Serial Interface')
        self.setGeometry(100, 100, 800, 600)
        self.createSidebar()

        main_layout = QVBoxLayout()
        self.statusLabel = QLabel("Ready")
        main_layout.addWidget(self.statusLabel)

        self.receivedDataDisplay = QTextEdit()
        self.receivedDataDisplay.setReadOnly(True)
        main_layout.addWidget(self.receivedDataDisplay)

        self.macroList = QListWidget()
        main_layout.addWidget(self.macroList)

        self.actionTypeSelect = QComboBox()
        self.actionTypeSelect.addItems(["Keyboard Key", "Media Control", "Function Key", "Modifier Key"])
        self.actionTypeSelect.currentIndexChanged.connect(self.updateActionOptions)
        main_layout.addWidget(self.actionTypeSelect)

        self.actionSelect = QComboBox()
        main_layout.addWidget(self.actionSelect)

        self.setMacroButton = QPushButton("Set/Edit Macro")
        self.setMacroButton.clicked.connect(self.set_or_edit_macro)
        main_layout.addWidget(self.setMacroButton)

        self.removeMacroButton = QPushButton("Remove Selected Macro")
        self.removeMacroButton.clicked.connect(self.remove_selected_macro)
        main_layout.addWidget(self.removeMacroButton)

        centralWidget = QWidget()
        centralWidget.setLayout(main_layout)
        self.setCentralWidget(centralWidget)

        self.load_stylesheet()

    def createSidebar(self):
        self.sidebar = QDockWidget("", self)
        self.sidebar.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.sidebar.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.sidebar.setTitleBarWidget(QWidget())  # Remove the title bar

        sidebar_contents = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_contents)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        self.sidebar.setWidget(sidebar_contents)
        self.sidebar.setMinimumWidth(300)  # Adjust this value as needed

        logo_label = QLabel()
        logo_pixmap = QPixmap('Assets/Images/logo.png')
        logo_label.setPixmap(logo_pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        sidebar_layout.addWidget(logo_label)

        settings_button = QPushButton('Settings')
        settings_button.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(settings_button)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar)

    def load_stylesheet(self):
        try:
            with open('Data/style.css', 'r') as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
                print("Stylesheet loaded successfully.")
        except Exception as e:
            print(f"Failed to load stylesheet: {e}")
            
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            port, baud_rate = dialog.getSettings()
            self.serial_manager.update_settings(port, baud_rate)
            self.statusLabel.setText(f"Serial port set to {port} at {baud_rate} baud")
               
    def set_or_edit_macro(self):
        command = self.decodedVar
        action_type = self.actionTypeSelect.currentText()
        macro_action = self.actionSelect.currentText()
        
        if not macro_action:
            QMessageBox.warning(self, "Invalid Macro", "Macro action cannot be empty.")
            return
        
        # Set macro, save macros, and refresh the list
        set_macro(command, action_type, macro_action)
        save_macros()  # This will save the current state of the macros to the file
        self.refresh_macros()  # Refresh the macro list to reflect the new changes
        
        self.statusLabel.setText(f"Macro set for {command}: {action_type} - {macro_action}")


    def refresh_macros(self):
        self.MacroPadApp = reload_macros()
        self.update_macro_list()
        self.statusLabel.setText("Macros refreshed successfully.")

    def save_macros(self):
        save_macros()
        self.statusLabel.setText("Macros saved successfully.")

    def remove_selected_macro(self):
        item = self.macroList.currentItem()
        if item:
            full_text = item.text()
            # It's important to extract the full key exactly as it's stored in the macros dictionary.
            # Assuming your list items are in the format "1: Pressed: Media Control - play/pause",
            # you would split by ':' and take the first two parts to reconstruct "1: Pressed".
            command_key = ':'.join(full_text.split(':')[:2]).strip()

            try:
                if command_key in self.MacroPadApp:
                    delete_macro(command_key)
                    self.refresh_macros()
                    self.statusLabel.setText(f"Removed macro for {command_key}")
                else:
                    QMessageBox.warning(self, "Error", f"No macro found for command '{command_key}'")
            except KeyError as e:
                QMessageBox.warning(self, "Deletion Error", str(e))
        else:
            QMessageBox.warning(self, "Select Macro", "Please select a macro to remove.")

    def updateActionOptions(self, index):
        self.actionSelect.clear()

        if index == 0:  # Keyboard Key (Alphabets, Numbers, and Common Keys)
            keyboard_keys = [
                'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
                'backspace', 'tab', 'enter', 'space',
                'esc', 'capslock', 'numlock', 'scrolllock', 'printscreen', 'menu'
            ]
            self.actionSelect.addItems(keyboard_keys)

        elif index == 1:  # Media Control Keys
            media_controls = [
                'play/pause', 'stop', 'previous_track', 'next_track', 'volume_mute', 
                'volume_up', 'volume_down'
            ]
            self.actionSelect.addItems(media_controls)

        elif index == 2:  # Function Keys
            function_keys = [
                'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12'
            ]
            self.actionSelect.addItems(function_keys)

        elif index == 3:  # Modifier Keys
            modifier_keys = [
                'alt', 'ctrl', 'shift', 'win',
                'delete', 'pause', 'insert', 'home', 'end', 'pageup', 'pagedown'  # Added these system control keys
            ]
            self.actionSelect.addItems(modifier_keys)

    def load_macros_and_update_list(self):
        # Load macros from file
        self.MacroPadApp = reload_macros()
        self.update_macro_list()
                    
    def update_macro_list(self):
        self.macroList.clear()
        for command, details in self.MacroPadApp.items():
            list_item = f"{command}: {details['type']} - {details['action']}"
            self.macroList.addItem(list_item)
            
    def handle_received_data(self, data):
        try:
            decoded_data = data.decode('utf-8').strip()
            print(f"Received data: {decoded_data}")  # Debug print
            self.guiUpdater.updateTextSignal.emit(decoded_data)
            self.decodedVar = decoded_data
            self.execute_macro(decoded_data)
        except UnicodeDecodeError:
            print("Received non-UTF-8 data")
            
    def execute_macro(self, command):
        macro = self.MacroPadApp.get(command)
        if macro:
            action_type = macro["type"]
            macro_action = macro["action"]
            
            if action_type == "Keyboard Key":
                keyboard.send(macro_action)  # Use send for simpler direct key press
            elif action_type == "Media Control":
                # Using keyboard for media controls. Make sure to handle exceptions if keys are not available
                keyboard.send(macro_action)
            elif action_type == "Function Key":
                keyboard.send(macro_action)  # Function keys are handled similarly to normal keys
            elif action_type == "Modifier Key":
                # Modifier keys include both traditional modifiers and other keys categorized here for macros
                # Handling individual key presses; consider adding functionality for combinations if needed
                keyboard.send(macro_action)
                
            self.statusLabel.setText(f"Executed {action_type} macro for {command}: {macro_action}")
        else:
            self.statusLabel.setText("No macro assigned for this command")



    def updateReceivedDataDisplay(self, text):
        self.receivedDataDisplay.append(text)
