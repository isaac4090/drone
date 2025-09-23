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


## pin23 voltage from battery on divider


class KeyPill(QtWidgets.QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(36)
        self.setMinimumWidth(44)
        self.setStyleSheet(self._style(False))

    def setPressed(self, pressed: bool):
        self.setStyleSheet(self._style(pressed))

    @staticmethod
    def _style(pressed: bool) -> str:
        if pressed:
            return """
            QLabel {
              background-color: #2e8b57;  /* green */
              color: white;
              border-radius: 18px;
              padding: 6px 12px;
              font-weight: 600;
            }"""
        else:
            return """
            QLabel {
              background-color: #e0e0e0;
              color: #444;
              border-radius: 18px;
              padding: 6px 12px;
            }"""
    
# ---- A triangle layout: apex on top row center, 3-key base on second row ----
def triangle_widget(apex: QtWidgets.QWidget, base_left: QtWidgets.QWidget,
                    base_center: QtWidgets.QWidget, base_right: QtWidgets.QWidget) -> QtWidgets.QWidget:
    w = QtWidgets.QWidget()
    g = QtWidgets.QGridLayout(w)
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(8)
    g.setVerticalSpacing(8)
    # 2 rows x 3 cols
    g.addWidget(apex,        0, 1)      # top center
    g.addWidget(base_left,   1, 0)
    g.addWidget(base_center, 1, 1)
    g.addWidget(base_right,  1, 2)
    for c in range(3): g.setColumnStretch(c, 1)
    for r in range(2): g.setRowStretch(r, 1)
    return w


class drone_UI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone")

        self.MotorPowers = {'FrontLeft': 0,
              'FrontRight': 0,
              'BackLeft':0,
              'BackRight':0}

        self.step = 1

        self.fullPower = 180

        self.pressed = set()

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


        #####
        self.kbOverlay = QtWidgets.QGroupBox("Keyboard (pressed keys)")
        self.kbOverlay.setVisible(False)  # hidden until you enable it
        overlayHBox = QtWidgets.QHBoxLayout(self.kbOverlay)
        overlayHBox.setContentsMargins(12, 12, 12, 12)
        overlayHBox.setSpacing(16)

        # Left half of left column: WASD triangle
        self.pillW = KeyPill("W")
        self.pillA = KeyPill("A")
        self.pillS = KeyPill("S")
        self.pillD = KeyPill("D")
        wasdTri = triangle_widget(self.pillW, self.pillA, self.pillS, self.pillD)

        wasdBox = QtWidgets.QGroupBox("WASD")
        wasdLay = QtWidgets.QVBoxLayout(wasdBox)
        wasdLay.setContentsMargins(8, 8, 8, 8)
        wasdLay.addWidget(wasdTri)
        #####

        # Right half of left column: Arrow triangle (↑ apex; ← ↓ → base)
        self.pillUp   = KeyPill("↑")
        self.pillLeft = KeyPill("←")
        self.pillDown = KeyPill("↓")
        self.pillRight= KeyPill("→")
        arrowsTri = triangle_widget(self.pillUp, self.pillLeft, self.pillDown, self.pillRight)

        arrowsBox = QtWidgets.QGroupBox("Arrows")
        arrowsLay = QtWidgets.QVBoxLayout(arrowsBox)
        arrowsLay.setContentsMargins(8, 8, 8, 8)
        arrowsLay.addWidget(arrowsTri)

        overlayHBox.addWidget(wasdBox, 1)
        overlayHBox.addWidget(arrowsBox, 1)

        leftLayout.addWidget(self.kbOverlay)
        leftLayout.addStretch(1)

        # Status
        self.statusBar().showMessage("Press W/A/S/D or Arrow keys (window must be focused)")

        # App-wide key capture
        QtWidgets.QApplication.instance().installEventFilter(self)
        central.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Mapping: Qt key -> pill
        self.key_to_pill = {
            QtCore.Qt.Key.Key_W: self.pillW,
            QtCore.Qt.Key.Key_A: self.pillA,
            QtCore.Qt.Key.Key_S: self.pillS,
            QtCore.Qt.Key.Key_D: self.pillD,
            QtCore.Qt.Key.Key_Up:    self.pillUp,
            QtCore.Qt.Key.Key_Down:  self.pillDown,
            QtCore.Qt.Key.Key_Left:  self.pillLeft,
            QtCore.Qt.Key.Key_Right: self.pillRight,
        }


        ####




        self.btnConnect.clicked.connect(self.on_connect_clicked)
        self.btnConnect.clicked.connect(self.on_disconnect_clicked)
        self.btnStartMotors.clicked.connect(self.on_start_clicked)
        self.btnStopMotors.clicked.connect(self.on_stop_clicked)
        self.btnFlyKeyboard.clicked.connect(self.on_fly_keyboard_clicked)


        self.stopToggle = False
        self.flyKeyboardToggle = False

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

        # hold-to-ramp state + timer
        self.hold_up = False
        self.hold_down = False
        self.holdTimer = QtCore.QTimer(self)
        self.holdTimer.setInterval(30)  # ~33 Hz; tweak to taste
        self.holdTimer.timeout.connect(self._tick_hold)

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
            for m in self.MotorPowers:
                self.MotorPowers[m] = self.fullPower
            self.send_powers()
            ret = QtWidgets.QMessageBox.information(
                self,
                "ESC Startup",
                "Turn on the switch, wait for beeping to stop.\nThen press OK.",
                QtWidgets.QMessageBox.StandardButton.Ok,
            )
            if ret == QtWidgets.QMessageBox.StandardButton.Ok:
                for m in self.MotorPowers:
                    self.MotorPowers[m] = 0
                self.send_powers()
                ret2 = QtWidgets.QMessageBox.information(
                    self,
                    "ESC Startup",
                    "Press OK once beeping has stoped",
                    QtWidgets.QMessageBox.StandardButton.Ok,
                )
                if ret2 == QtWidgets.QMessageBox.StandardButton.Ok:
                    # now send low power to check if motors are working
                    for m in self.MotorPowers:
                        self.MotorPowers[m] = 7
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
                        for m in self.MotorPowers:
                            self.MotorPowers[m] = 0
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
        data = bytes([self.MotorPowers[m] for m in self.MotorPowers])  # 4 bytes
        self.s.write(data)

    def on_stop_clicked(self):
        self.stopToggle = not self.stopToggle
        if self.stopToggle:
            self.btnStopMotors.setText("Motors stoped, press to enable")
            self.btnStopMotors.setStyleSheet("QPushButton { background: red; color: white; }")
            for m in self.MotorPowers:
                self.MotorPowers[m] = 0
            self.send_powers()
            self.btnFlyKeyboard.setEnabled(False)
            self.btnFlyPS4.setEnabled(False)
            if self.flyKeyboardToggle:
                self.on_fly_keyboard_clicked()
        else:
            self.btnStopMotors.setText("Motors enabled, press to stop")
            self.btnStopMotors.setStyleSheet("QPushButton { background: green; color: white; }")
            self.btnFlyKeyboard.setEnabled(True)
            self.btnFlyPS4.setEnabled(True)
            
        



    def on_fly_ps4_clicked(self):
        pass


    def on_fly_keyboard_clicked(self):
        self.flyKeyboardToggle = not self.flyKeyboardToggle
        if self.flyKeyboardToggle:
            self.btnFlyKeyboard.setText("Flying Keyboard")
            self.btnFlyKeyboard.setStyleSheet("QPushButton { background: green; color: white; }")
            self.btnFlyPS4.setEnabled(False)
            self.kbOverlay.setVisible(True)
        else:
            self.btnFlyKeyboard.setText("Flying Keyboard OFF")
            self.btnFlyKeyboard.setStyleSheet("QPushButton { background: orange; color: white; }")
            self.btnFlyPS4.setEnabled(True)
            self.kbOverlay.setVisible(False)
        
    def _set_key(self, key: int, down: bool):
        # (optional) track which keys are down
        if down:
            self.pressed.add(key)
        else:
            self.pressed.discard(key)

        # highlight the pill when the keyboard overlay is visible
        pill = self.key_to_pill.get(key)
        if pill is not None and self.kbOverlay.isVisible():
            pill.setPressed(down)

    def eventFilter(self, obj, ev):
        if ev.type() == QtCore.QEvent.Type.KeyPress and not ev.isAutoRepeat():
            key = ev.key()
            # start holding
            if key == QtCore.Qt.Key.Key_Up:
                self.hold_up = True
                if not self.holdTimer.isActive():
                    self.holdTimer.start()
            elif key == QtCore.Qt.Key.Key_Down:
                self.hold_down = True
                if not self.holdTimer.isActive():
                    self.holdTimer.start()
            self._set_key(key, True)
            return False

        elif ev.type() == QtCore.QEvent.Type.KeyRelease and not ev.isAutoRepeat():
            key = ev.key()
            # stop holding
            if key == QtCore.Qt.Key.Key_Up:
                self.hold_up = False
            elif key == QtCore.Qt.Key.Key_Down:
                self.hold_down = False
            # stop timer if nothing held
            if not self.hold_up and not self.hold_down and self.holdTimer.isActive():
                self.holdTimer.stop()
            # (your existing pill highlight)
            self._set_key(key, False)
            return False

        return False

    def _tick_hold(self):
        # only act when keyboard overlay is visible and motors enabled
        if not self.kbOverlay.isVisible() or self.stopToggle:
            return
        mods = QtWidgets.QApplication.keyboardModifiers()
        step_size = self.step*4 if (mods & QtCore.Qt.KeyboardModifier.ShiftModifier) else self.step
        delta = ((1 if self.hold_up else 0) - (1 if self.hold_down else 0)) * step_size
        if delta != 0:
            self._bump_all(delta)
        else:
            # nothing held anymore; stop timer
            self.holdTimer.stop()

    def _bump_all(self, delta: int):
        for m in self.MotorPowers:
            pwr = self.MotorPowers[m] + delta
            if pwr > self.fullPower:
                self.MotorPowers[m] = self.fullPower 
            elif pwr < 0: 
               self.MotorPowers[m] = 0
            else: 
                self.MotorPowers[m] = pwr
        self.send_powers()



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
    main(secondMonitor=True)