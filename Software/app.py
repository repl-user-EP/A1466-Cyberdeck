import sys
import os
import time
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QLineEdit,
    QGridLayout
)

from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QThread, Signal
import ctypes
import serial.tools.list_ports
import serial

class SerialThread(QThread): # Background serial thread
    #Signal is basically a "Yo I've got data"
    received = Signal(str) #Signal for recvd data
    disconnected = Signal() #Sends 'disconnected' sig thru thread

    def __init__(self, serial_port):
        super().__init__()
        # Serial port object for figuring out what to talk to (in this case the arduino)
        self.serial_port = serial_port
        self.running = True #Part of the stop thread later

    def run(self): #Auto start when thread.start()

        while self.running: # loop until break

            try:

                if self.serial_port.in_waiting: #waiting for data to come thru, if 0, arduino no sent stuff

                    line = ( # Read a single line from Duino
                        self.serial_port
                        .readline() # gets bytes
                        .decode(errors="ignore") # make into str
                        .strip() # get rid of \n
                    ) #takes data from the serial connection

                    self.received.emit(line) # tell GUI that its got a new bit of text, emit to main thread
                else: # nothing to read, do nothing for 10ms
                    time.sleep(0.01)
            except Exception:
                #if no worky, then stop thread. disconnected arduino
                self.disconnected.emit() #if disconnected tell rest of program yup i disconnected
                break #stop loop
    # for when it needs to stop reading the serial
    def stop(self):
        self.running = False
class moduleWidg(QWidget):
    pass

class MainWindow(QMainWindow):
    def closeEvent(self, event): # QT calls when I close window
        if hasattr(self, "serial_thread"): # if theres a serial thread (variable exist?)
            self.serial_thread.stop() # tell background thread stop reading the serial port
            self.serial_thread.wait() # wait before close program
        if self.serial_port: #close COM if still open
            self.serial_port.close()
        event.accept() # tell Qt you're good to close program

    def connect_serial(self):
        self.baud = 9600
        port = self.port_selector.currentText()
        #ports = serial.tools.list_ports.comports() #list serial ports
        if not port:
            self.status.setText("Error: No port selected.")
            return
        try:
            print(f"Connecting to {port}")
            self.serial_port = serial.Serial(port,self.baud,timeout=1)
            self.serial_thread = SerialThread(self.serial_port)

            self.serial_thread.received.connect(self.serial_received)

            self.serial_thread.disconnected.connect(self.serial_disconnected)

            self.serial_thread.start()

            self.status.setText(f"● [NEMESIS MCU] connected on {port}")
            self.connect_button.setText("Disconnect")
        except Exception as e: #if something goes wrong exception shows
            self.status.setText(str(e))
    def sendtx(self):
        cmd = self.cmdinput.text()
        if not cmd:
            return
        if not self.serial_port:
            self.status.setText("MCU Not Connected")
            return
        try:
            self.serial_port.write((cmd + "\n").encode()) # convert to bytes readable by MCU
            self.serial_console.appendPlainText(f"TX -> {cmd}") #cmd in console
            self.cmdinput.clear() #clear input
        except Exception as e:
            self.status.setText(f"TX ERR {e}")
    def serial_received(self, text): # called every line arduino sends, changes label
        self.last_message.setText(text)

        self.serial_console.appendPlainText(f"RX -> {text}") #recvd send to console

    def serial_disconnected(self): # if arduino disconnects, say so

        self.status.setText("● [DISCONNECTED]") #status label
        self.serial_console.appendPlainText(f"SYS -> NEMESIS MCU Disconnected") #console
        self.connect_button.setText("Connect")

        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception as e:
                print(e)
        self.serial_port = None
    def refresh_serial(self):
        self.port_selector.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_selector.addItem(port.device)

    def __init__(self): # when new MainWindow, what does it look like
        super().__init__()

        self.serial_port = None #variable thing for serial ports
        self.setWindowTitle("NEMESIS Master Control")
        self.resize(1024,640)
        header = QHBoxLayout()
        title = QLabel("NEMESIS MASTER CONTROL")
        self.status = QLabel("● [DISCONNECTED]")
        self.status.setObjectName("Status")
        self.status.setProperty("state", "connected")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)

        layout = QVBoxLayout() #Main layout
        dashboard_layout = QGridLayout()
        dashboard_title = QLabel("SYSTEM STATUS")
        dashboard_layout.addWidget(dashboard_title,0,1)

        self.port_selector = QComboBox()
        self.refresh = QPushButton("Refresh")
        self.refresh.setObjectName("refresh")
        self.refresh.clicked.connect(self.refresh_serial) # connect to button, call function if clicked.
        self.last_message = QLabel("No data")
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        self.connect_button.move(100,250)
        self.connect_button.setObjectName("Connector")

        connect_handle = QHBoxLayout()
        connect_handle.addWidget(self.port_selector, stretch=1)
        connect_handle.addWidget(self.refresh, stretch=1)
        connect_handle.addStretch(2)
        connect_handle.addWidget(self.connect_button, stretch=1)


        self.serial_console = QPlainTextEdit() #Console Log
        self.serial_console.setReadOnly(True)

        self.cmdinput = QLineEdit()
        self.cmdinput.setPlaceholderText("User TX:")
        self.sendbtn = QPushButton("TX Send")
        self.sendbtn.clicked.connect(self.sendtx)
        self.cmdinput.returnPressed.connect(self.sendtx)

        layout.addLayout(header)
        layout.addLayout(connect_handle)
        layout.addLayout(dashboard_layout)
        #layout.addWidget(self.port_selector)
        #layout.addWidget(self.refresh)
        #layout.addWidget(self.status)
        layout.addWidget(self.last_message)
        #layout.addWidget(self.connect_button)
        layout.addWidget(self.cmdinput)
        layout.addWidget(self.sendbtn)
        layout.addWidget(self.serial_console)
        layout.addStretch()
        

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.refresh_serial()

if __name__ == "__main__":
    # Register unique App ID with Windows BEFORE QApplication
    if sys.platform == "win32":
        myappid = 'mycompany.cyberdeck.mcu.v1'  # Keep unique
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    
    # Point to PNG file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "AppIcon_fixed.png")  # <-- CHANGED TO PNG
    app_icon = QIcon(icon_path)
    
    # Apply icon globally to clear Python taskbar logo
    app.setWindowIcon(app_icon)

    try:
        with open("style.css", "r") as f: #ref to stylesheet
            app.setStyleSheet(f.read())
    except FileNotFoundError: # If no stylesheet fallback
        print("CSS file not found, loading default fallback styles.")

    window = MainWindow()
    window.setWindowIcon(app_icon) # Sets the top-left window frame icon
    window.show()

    sys.exit(app.exec())
