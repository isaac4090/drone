import socket, time,sys
from enum import Enum

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtNetwork import QTcpSocket,QAbstractSocket

HOST_DEFAULT = "192.168.4.1"
PORT_DEFAULT = 2323
SEND_HZ = 30

class mode(Enum):
    connect = 0
    startMotors = 1
    stopMotors = 2
    fly = 3

MotorPowers = {'FrontLeft': 0,
              'FrontRight': 0,
              'BackLeft':0,
              'BackRight':0}

fullPower = 180


    


class drone_UI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # LEFT: Controls panel with 5 big buttons (Connect, Start, Stop, Fly PS4, Fly Keyboard)
        left = QtWidgets.QFrame()
        left.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        leftLayout = QtWidgets.QVBoxLayout(left)
        leftLayout.setContentsMargins(16, 16, 16, 16)
        leftLayout.setSpacing(12)

        def big_button(text: str) -> QtWidgets.QPushButton:
            b = QtWidgets.QPushButton(text)
            b.setMinimumHeight(52)
            b.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                            QtWidgets.QSizePolicy.Policy.Fixed)
            b.setStyleSheet("font-size:16px;")
            return b

        self.btnConnect     = big_button("Connect?")
        self.btnDisconnect     = big_button("Disconnect")
        self.btnStartMotors = big_button("Start Motors")
        self.btnStopMotors  = big_button("Stop Motors")
        self.btnFlyPS4      = big_button("Fly PS4")
        self.btnFlyKeyboard = big_button("Fly Keyboard")

        leftLayout.addWidget(self.btnConnect)
        leftLayout.addWidget(self.btnDisconnect)
        leftLayout.addWidget(self.btnStartMotors)
        leftLayout.addWidget(self.btnStopMotors)
        leftLayout.addWidget(self.btnFlyPS4)
        leftLayout.addWidget(self.btnFlyKeyboard)
        leftLayout.addStretch(1)

        self.btnConnect.clicked.connect(self.on_connect_clicked)
        self.btnConnect.clicked.connect(self.on_disconnect_clicked)
        self.btnStartMotors.clicked.connect(self.on_start_clicked)

        # connect first
        self.btnDisconnect.setEnabled(False) 
        self.btnStartMotors.setEnabled(False) 
        self.btnStopMotors.setEnabled(False) 
        self.btnFlyPS4.setEnabled(False) 
        self.btnFlyKeyboard.setEnabled(False) 

        # RIGHT: placeholder area (put plot/canvas/telemetry here later)
        right = QtWidgets.QFrame()
        right.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        rightLayout = QtWidgets.QVBoxLayout(right)
        rightLayout.setContentsMargins(16, 16, 16, 16)
        rightLayout.addStretch(1)
        lbl = QtWidgets.QLabel("Right area (your plot / HUD / telemetry)")
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#666; font-size:16px;")
        rightLayout.addWidget(lbl)
        rightLayout.addStretch(1)

        # Put both halves into the main layout; make right a bit wider
        root.addWidget(left, 1)
        root.addWidget(right, 1)

        # Status bar
        self.statusBar().showMessage("Ready")

    # ----- Handlers (stubs) -----

    def on_connect_clicked(self):
        self.btnConnect.setEnabled(False)
        self.btnConnect.setText("Connecting...")
        self.btnConnect.setStyleSheet("QPushButton { background-color: orange; color: white; }")
        self.s = QTcpSocket(self)
        self.s.connected.connect(lambda: (
            self.btnConnect.setText("Connected!"),
            self.btnConnect.setStyleSheet("QPushButton { background: green; color: white; }"),
            self.btnConnect.setEnabled(False),
            self.btnDisconnect.setEnabled(True),
            self.btnStartMotors.setEnabled(True),
            self.btnStopMotors.setEnabled(True), 
            self.btnFlyPS4.setEnabled(True),
            self.btnFlyKeyboard.setEnabled(True) 
          
        ))
        self.s.errorOccurred.connect(lambda e: (
            self.btnConnect.setText("Connection failed, try again?"),
            self.btnConnect.setStyleSheet("QPushButton { background: red; color: white; }"),
            self.btnConnect.setEnabled(True)
            
        ))
        self.s.connectToHost("192.168.4.1", 2323)

    def on_disconnect_clicked(self):
        pass 

    def on_start_clicked(self):
        self.btnStartMotors.setText("Starting Motors...")
        self.btnStartMotors.setStyleSheet("QPushButton { background: orange; color: white; }")
        self.btnStartMotors.setEnabled(False)
        switch = QtWidgets.QMessageBox.information(
            self,
            "ESC Startup",
            "Make sure the swtich is off (O). \nThen press OK.",
            QtWidgets.QMessageBox.StandardButton.Ok,
        )
        if switch == QtWidgets.QMessageBox.StandardButton.Ok:
            for m in MotorPowers:
                MotorPowers[m] = fullPower
            self.send_powers()
            ret = QtWidgets.QMessageBox.information(
                self,
                "ESC Startup",
                "Turn on the switch, wait for beeping to stop.\nThen press OK.",
                QtWidgets.QMessageBox.StandardButton.Ok,
            )
            if ret == QtWidgets.QMessageBox.StandardButton.Ok:
                for m in MotorPowers:
                    MotorPowers[m] = 0
                self.send_powers()
                ret2 = QtWidgets.QMessageBox.information(
                    self,
                    "ESC Startup",
                    "Press OK once beeping has stoped",
                    QtWidgets.QMessageBox.StandardButton.Ok,
                )
                if ret2 == QtWidgets.QMessageBox.StandardButton.Ok:
                    # now send low power to check if motors are working
                    for m in MotorPowers:
                        MotorPowers[m] = 7
                    self.send_powers()
                    ret3 = QtWidgets.QMessageBox.question(
                        self,
                        "Motor Check",
                        "Are all motors spinning?",
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                        QtWidgets.QMessageBox.StandardButton.Yes,
                    )
                    if ret3 == QtWidgets.QMessageBox.StandardButton.Yes:
                        # Success state
                        for m in MotorPowers:
                            MotorPowers[m] = 0
                        self.send_powers()
                        self.statusBar().showMessage("Spin check OK")
                        self.btnStartMotors.setText("Motors Ready")
                        self.btnStartMotors.setStyleSheet("QPushButton { background: green; color: white; }")
                        self.btnStartMotors.setEnabled(False)
                    else:
                        # Not spinning — show a warning and reset UI
                        QtWidgets.QMessageBox.warning(
                            self, "Motor Check Failed",
                            "Turn off the switch!!!!"
                        )
                        self.btnStartMotors.setText("Motors failed, restart UI")
                        self.btnStartMotors.setEnabled(False)
                        self.btnStartMotors.setStyleSheet("QPushButton { background: red; color: white; }")


        
    def send_powers(self):
        if not self.s or self.s.state() != QAbstractSocket.SocketState.ConnectedState:
            return
        data = bytes([MotorPowers[m] for m in MotorPowers])  # 4 bytes
        self.s.write(data)




    def on_stop_clicked(self):
        self.statusBar().showMessage("Stop Motors clicked")
        # TODO: send DISARM / cut motors

    def on_fly_ps4_clicked(self):
        self.statusBar().showMessage("Fly PS4 clicked")
        # TODO: start gamepad loop

    def on_fly_keyboard_clicked(self):
        self.statusBar().showMessage("Fly Keyboard clicked")





def main(secondMonitor:bool = False):
    app = QtWidgets.QApplication(sys.argv)
    win = drone_UI()
    if secondMonitor:
        screens = QGuiApplication.screens()
        if len(screens) > 1:
            second = screens[2]                             # index 0 is primary, 1 is your second monitor
            geom   = second.geometry()                      # QRect(x, y, width, height)

            # Move the top‑level window to that screen…
            win.move(geom.x(), geom.y())

            # Make sure Qt knows to put it on that screen
            handle = win.windowHandle()
            if handle:
                handle.setScreen(second)

            # And go fullscreen
            win.showFullScreen()
        else:
            # Fallback if there’s only one monitor
            win.showMaximized()
    else:
        win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main(secondMonitor=False)