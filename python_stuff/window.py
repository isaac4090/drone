from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtNetwork import QAbstractSocket
from .config import *
from .net import NetClient
from .telemetry import parse_frame
from .widgets import TiltBall, BatteryIndicator, BarPair, KeyPill, triangle_widget

class DroneWindow(QtWidgets.QMainWindow):
    def __init__(self, debug:bool = False):
        super().__init__()
        self.debug = debug
        self.setWindowTitle("Drone")
        self.MotorPowers = {n:0 for n in MOTOR_ORDER}
        self.step = STEP
        self.fullPower = FULL_POWER
        self.stopToggle = False
        self.flyKeyboardToggle = False
        self.pressed = set()
        self._latest = None

        self.switch_is_on = None 
         

        # ---- Net
        self.net = NetClient(self)
        self.net.connected.connect(self._on_connected)
        self.net.disconnected.connect(self._on_disconnected)
        self.net.errorText.connect(self._on_failed_connect)
        self.net.frameReady.connect(self._on_frame)

        # ---- UI layout
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central); root.setContentsMargins(12,12,12,12); root.setSpacing(12)

        # left column (buttons + battery + keyboard overlay)
        left = QtWidgets.QFrame(); left.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        leftLayout = QtWidgets.QVBoxLayout(left); leftLayout.setContentsMargins(16,16,16,16); leftLayout.setSpacing(12)

        def big_button(text): 
            b = QtWidgets.QPushButton(text); b.setMinimumHeight(52)
            b.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            b.setStyleSheet("font-size:16px;"); return b

        self.btnConnect     = big_button("Connect")
        self.btnDisconnect  = big_button("Disconnect")
        self.btnStartMotors = big_button("Reset ESC's")
        self.btnStopMotors  = big_button("Motors disenabled — press to enable")
        self.btnFlyPS4      = big_button("Fly PS4")
        self.btnFlyKeyboard = big_button("Fly Keyboard")

        self._base_btn_style = self.btnStopMotors.styleSheet() 

        for b in (self.btnConnect, self.btnDisconnect, self.btnStartMotors,
                  self.btnStopMotors, self.btnFlyPS4, self.btnFlyKeyboard):
            leftLayout.addWidget(b)
        leftLayout.addStretch(1)

        self.battery = BatteryIndicator(cells=3)
        leftLayout.addWidget(self.battery, 0, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom)

        # keyboard overlay (hidden until toggled)
        self.kbOverlay = QtWidgets.QGroupBox("Keyboard (pressed keys)"); self.kbOverlay.setVisible(False)
        overlayHBox = QtWidgets.QHBoxLayout(self.kbOverlay)
        self.pillW, self.pillA, self.pillS, self.pillD = KeyPill("W"), KeyPill("A"), KeyPill("S"), KeyPill("D")
        wasdTri = triangle_widget(self.pillW, self.pillA, self.pillS, self.pillD)
        wasdBox = QtWidgets.QGroupBox("WASD"); wLay = QtWidgets.QVBoxLayout(wasdBox); wLay.addWidget(wasdTri)
        self.pillUp, self.pillLeft, self.pillDown, self.pillRight = KeyPill("↑"), KeyPill("←"), KeyPill("↓"), KeyPill("→")
        arrowsTri = triangle_widget(self.pillUp, self.pillLeft, self.pillDown, self.pillRight)
        arrowsBox = QtWidgets.QGroupBox("Arrows"); aLay = QtWidgets.QVBoxLayout(arrowsBox); aLay.addWidget(arrowsTri)
        overlayHBox.addWidget(wasdBox,1); overlayHBox.addWidget(arrowsBox,1)
        leftLayout.addWidget(self.kbOverlay); leftLayout.addStretch(1)

        # right column (tilt ball + motor I/O)
        right = QtWidgets.QFrame(); right.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        rightLayout = QtWidgets.QVBoxLayout(right); rightLayout.setContentsMargins(16,16,16,16)
        self.tiltBall = TiltBall(diameter=500)
        rightLayout.addWidget(self.tiltBall, 0, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight)

        ioBox = QtWidgets.QGroupBox("Motor I/O"); ioGrid = QtWidgets.QGridLayout(ioBox)
        ioGrid.setContentsMargins(0,10,10,10); ioGrid.setHorizontalSpacing(18); ioGrid.setVerticalSpacing(8)

        ioGrid.addWidget(QtWidgets.QLabel(""), 0, 0)
        self.order = MOTOR_ORDER
        for c, name in enumerate(self.order, start=1):
            lab = QtWidgets.QLabel(name); lab.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet("color:#555; font-weight:600;"); ioGrid.addWidget(lab, 0, c)

        self.barPairs, self.txLabels, self.rxLabels = {}, {}, {}
        CELL_W, BAR_H = 120, 400
        def _mkCell():
            lbl = QtWidgets.QLabel("0")
            lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(CELL_W)
            lbl.setStyleSheet("font-family: Consolas, monospace; font-size:14px; background:#f2f2f2; border-radius:6px; padding:4px 6px;")
            return lbl

        for c, name in enumerate(self.order, start=1):
            col = QtWidgets.QWidget(); v = QtWidgets.QVBoxLayout(col); v.setContentsMargins(0,0,0,0); v.setSpacing(6)
            bp = BarPair(FULL_POWER, bar_w=CELL_W, bar_h=BAR_H); self.barPairs[name] = bp; v.addWidget(bp, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            tx, rx = _mkCell(), _mkCell(); self.txLabels[name], self.rxLabels[name] = tx, rx
            rowNums = QtWidgets.QHBoxLayout(); rowNums.setSpacing(8); rowNums.addWidget(tx); rowNums.addWidget(rx); v.addLayout(rowNums)
            ioGrid.addWidget(col, 1, c, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        rightLayout.addWidget(ioBox, 1)

        root.addWidget(left, 1); root.addWidget(right, 1)
        self.statusBar().showMessage("Ready")

        # wiring
        self.btnConnect.clicked.connect(lambda: self._connect(HOST_DEFAULT, PORT_DEFAULT))
        self.btnDisconnect.clicked.connect(self._disconnect)
        self.btnStartMotors.clicked.connect(self._start_motors)
        self.btnStopMotors.clicked.connect(self._stop_toggle)
        self.btnFlyKeyboard.clicked.connect(self._fly_keyboard_toggle)

        # initally only have connect button available
        self._gate_buttons = [
            self.btnDisconnect,
            self.btnStartMotors,
            self.btnStopMotors,
            self.btnFlyPS4,
            self.btnFlyKeyboard,
        ]

        for b in self._gate_buttons:
            b.setEnabled(False)
        self.btnConnect.setEnabled(True)

        # key capture + hold
        QtWidgets.QApplication.instance().installEventFilter(self)
        self.key_to_pill = {
            QtCore.Qt.Key.Key_W: self.pillW,
            QtCore.Qt.Key.Key_A: self.pillA,
            QtCore.Qt.Key.Key_S: self.pillS,
            QtCore.Qt.Key.Key_D: self.pillD,
            QtCore.Qt.Key.Key_Up: self.pillUp,
            QtCore.Qt.Key.Key_Down: self.pillDown,
            QtCore.Qt.Key.Key_Left: self.pillLeft,
            QtCore.Qt.Key.Key_Right: self.pillRight,
        }
        self.hold_up = False; self.hold_down = False
        self.holdTimer = QtCore.QTimer(self); self.holdTimer.setInterval(30); self.holdTimer.timeout.connect(self._tick_hold)

        # periodic UI refresh (decoupled from socket rate)
        self.uiTimer = QtCore.QTimer(self); self.uiTimer.setInterval(int(1000/UI_FPS))
        self.uiTimer.timeout.connect(self._pump_ui); self.uiTimer.start()

    # ---- Net handlers ----
    def _connect(self, host, port):
        self.btnConnect.setEnabled(False)
        if(self.debug):
            self._on_connected()
            return
        self.btnConnect.setText("Connecting...")
        self.btnConnect.setStyleSheet("QPushButton { background: orange; color: white; }")
        self.net.connectTo(host, port)

    def _disconnect(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Disconnect?",
            "Are you sure you want to disconnect from the drone?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        
        if not self.stopToggle:
            self._stop_toggle()

        if not self.debug:
            self.disconnect()
        else:
            self._on_disconnected()


    def _is_connected(self) -> bool:
        return self.debug or (
            hasattr(self.net, "s") and
            self.net.s.state() == QAbstractSocket.SocketState.ConnectedState
        )
    
    def _update_esc_button_gate(self, vpack: float):
        prev = self.switch_is_on
        if self.switch_is_on is None:
            # First reading -> classify
            self.switch_is_on = (vpack >= SWITCH_ON_TH)
        else:
            if self.switch_is_on:
                # currently ON -> only flip OFF when well below OFF threshold
                if vpack <= SWITCH_OFF_TH:
                    self.switch_is_on = False
                    self._stop_toggle()

            else:
                # currently OFF -> only flip ON when clearly above ON threshold
                if vpack >= SWITCH_ON_TH:
                    self.switch_is_on = True
                    self.btnStopMotors.setText("Motors disenabled — press to enable")

        # Gate the button: enabled only if connected and switch OFF
        allow = self._is_connected() and (self.switch_is_on is False)
        self.btnStartMotors.setEnabled(allow)
        self.btnStartMotors.setToolTip(
            "Switch is OFF — safe to reset ESCs" if allow
            else "Turn the switch OFF to reset ESCs"
        )
        

        if prev != self.switch_is_on and self.switch_is_on is not None:
            self.statusBar().showMessage(f"Switch is {'ON' if self.switch_is_on else 'OFF'} (V={vpack:.2f})")

    def _on_connected(self):
        # in debug mode turn connect into a switch flip
        if self.debug:
            self.btnConnect.setText("Connected! Press to flip switch")
            self.btnConnect.setEnabled(True)
            if self.switch_is_on is None:
                self.switch_is_on = False
                volts = 0
            else:
                self.switch_is_on = not self.switch_is_on
                if self.switch_is_on:
                    volts = 12
                else:
                    volts = 0

            # set multiple to remove smoothing effect 
            for _ in range(100):
                self.battery.set_voltage(volts)
            self._update_esc_button_gate(volts)
        else:
            self.btnConnect.setText("Connected!")
        self.btnConnect.setStyleSheet("QPushButton { background: green; color: white; }")
        self.btnStopMotors.setEnabled(True)
        self.btnDisconnect.setEnabled(True)
        # start motor send timer
        self._sendTimer = QtCore.QTimer(self); self._sendTimer.setInterval(int(1000/SEND_HZ))
        self._sendTimer.timeout.connect(self._send_current_powers); self._sendTimer.start()
        
        if not self.stopToggle:
            self._stop_toggle() # once connected motors will be in an off state





    def _on_failed_connect(self):
        self.btnConnect.setText("Connection failed, try again?")
        self.btnConnect.setStyleSheet("QPushButton { background: red; color: white; }")
        self.btnConnect.setEnabled(True)

    def _on_disconnected(self):
        self.statusBar().showMessage("Disconnected")
        self.btnConnect.setEnabled(True)
        self.btnConnect.setText("Connect")
        self.btnConnect.setStyleSheet("")
        if hasattr(self, "_sendTimer") and self._sendTimer.isActive(): self._sendTimer.stop()
        for b in self._gate_buttons:
            b.setEnabled(False)
        self.btnConnect.setEnabled(True)

    def _on_frame(self, frame: bytes):
        self._latest = parse_frame(frame)

    # ---- UI periodic refresh ----
    def _pump_ui(self):
        if not self._latest: return
        d = self._latest
        self.battery.set_voltage(d["batV"], cells=3)
        for name, val in zip(self.order, d["motors"]):
            self.rxLabels[name].setText(str(val))
            self.barPairs[name].setRX(val)
        self.tiltBall.set_xy(d["x"], d["y"])
        self._update_esc_button_gate(d["batV"])

    # ---- Motor send ----
    def _send_current_powers(self):
        fl, fr, bl, br = (self.MotorPowers[n] for n in self.order)
        self.net.sendMotors(fl, fr, bl, br)
        for name, val in zip(self.order, (fl, fr, bl, br)):
            self.txLabels[name].setText(str(val))
            self.barPairs[name].setTX(val)

    def _wait_ms(self, ms: int):
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(ms, loop.quit)
        loop.exec()

    # ---- Buttons / keys ----
    def _start_motors(self):
        for b in self._gate_buttons:
            b.setEnabled(False)
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reset ESC's?",
            "Are you sure you want to Reset the ESC's, Make sure the switch is off (O)",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        
        # Progress bar
        dlg = QtWidgets.QProgressDialog("Starting ESC reset…", "Cancel", 0, 100, self)
        dlg.setWindowTitle("ESC Reset")
        dlg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        dlg.setAutoClose(True)
        dlg.setAutoReset(True)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)

        def set_status(text, pct):
            dlg.setLabelText(text)
            dlg.setValue(pct)
            # ensure the dialog paints immediately
            QtCore.QTimer.singleShot(0, lambda: None)
            self._wait_ms(10)

        def send(pwr):
            for m in self.MotorPowers:
                self.MotorPowers[m] = pwr
            self._send_current_powers()

        if hasattr(self, "is_switch_off") and callable(self.is_switch_off):
            set_status("Checking switch is OFF…", 0)
            if not self.is_switch_off():
                dlg.cancel()
                QtWidgets.QMessageBox.warning(
                    self, "Switch must be OFF",
                    "Safety check failed: the switch is not OFF.\nTurn it OFF and try again."
                )
                return
            
        set_status("Turn switch on now.", 5)
        waited_ms = 0
        while not self.switch_is_on:
            if self.debug:
                res = QtWidgets.QMessageBox.question(
                    self,
                    "Debug: Switch ON",
                    "Debug mode: Pretend the switch was turned ON?\n\n"
                    "Press OK to continue, or Cancel to abort.",
                    QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                    QtWidgets.QMessageBox.StandardButton.Ok,
                )
                if res == QtWidgets.QMessageBox.StandardButton.Ok:
                    self._on_connected()
                else:
                    dlg.cancel()

            # Normal route
            if dlg.wasCanceled():
                send(ZERO)
                return
            self._wait_ms(100)
            waited_ms += 100
            if waited_ms >= SWITCH_TIMEOUT:
                send(ZERO,)
                QtWidgets.QMessageBox.warning(self, "Timeout", "Timed out waiting for the switch to turn ON.")
                return
            

            
        send(FULL_POWER)
        for pct in range(5, 50, 5):
            if dlg.wasCanceled():
                send(ZERO)
                return
            set_status("Holding FULL power. Beep, Beep ...", pct)
            self._wait_ms(BEEPING_TIME_MS)  

        send(ZERO)
        for pct in range(50,95,5):
            if dlg.wasCanceled():
                send(ZERO)
                return
            set_status("Cutting power to 0. Beep,Beep...", pct)
            self._wait_ms(BEEPING_TIME_MS)  
        if dlg.wasCanceled():
            return
        send(SLOW_POWER)
        set_status("Waiting for user response", 99)
        res = QtWidgets.QMessageBox.question(
            self,
            "Check motors",
            "Are ALL motors spinning smoothly at low power?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes,
        )
        if res == QtWidgets.QMessageBox.StandardButton.Yes:
            QtWidgets.QMessageBox.information(self, "ESC Reset", "ESC reset/test complete ✅")
        else:
            QtWidgets.QMessageBox.warning(
                self, "ESC Reset",
                "Some motors did not spin.\n\n"
                "• Check wiring and ESC signal/ground\n"
                "• Re-run calibration per ESC vendor procedure\n"
                "• Inspect for mechanical obstruction"
            )
        send(ZERO)
        dlg.close()

        self.btnDisconnect.setEnabled(True)
        self.btnStopMotors.setEnabled(True)
        if self.debug:
            self._update_esc_button_gate(11) 

        



    def _stop_toggle(self):
        self.stopToggle = not self.stopToggle
        if self.stopToggle or not self.switch_is_on:
            for m in self.MotorPowers: 
                self.MotorPowers[m] = 0
            self._send_current_powers()
            if not self.switch_is_on:
                self.btnStopMotors.setText("Motors disenabled — Switch is off")
                self.stopToggle = True
            else:
                self.btnStopMotors.setText("Motors disenabled — press to enable")
            self.btnStopMotors.setStyleSheet(self._base_btn_style)
            if self.flyKeyboardToggle:
                self._fly_keyboard_toggle()
            self.btnFlyKeyboard.setEnabled(False); self.btnFlyPS4.setEnabled(False)
        else:
            self.btnStopMotors.setText("Motors enabled — press to stop")
            self.btnStopMotors.setStyleSheet("QPushButton { background: green; color: white; }")
            self.btnFlyKeyboard.setEnabled(True); self.btnFlyPS4.setEnabled(True)

    def _fly_keyboard_toggle(self):
        self.flyKeyboardToggle = not self.flyKeyboardToggle
        if self.flyKeyboardToggle:
            self.kbOverlay.setVisible(True)
            self.btnFlyKeyboard.setText("Flying Keyboard")
            self.btnFlyKeyboard.setStyleSheet("QPushButton { background: green; color: white; }")
        else:
            self.kbOverlay.setVisible(False)
            self.btnFlyKeyboard.setText("Fly Keyboard")
            self.btnFlyKeyboard.setStyleSheet("")

    # ---- Key handling (hold to ramp up/down) ----
    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QtCore.QEvent.Type.KeyPress and not ev.isAutoRepeat():
            k = ev.key()
            if k == QtCore.Qt.Key.Key_Up:   self.hold_up = True;   self.holdTimer.start()
            if k == QtCore.Qt.Key.Key_Down: self.hold_down = True; self.holdTimer.start()
            self._set_key(k, True)
        elif t == QtCore.QEvent.Type.KeyRelease and not ev.isAutoRepeat():
            k = ev.key()
            if k == QtCore.Qt.Key.Key_Up:   self.hold_up = False
            if k == QtCore.Qt.Key.Key_Down: self.hold_down = False
            if not self.hold_up and not self.hold_down: self.holdTimer.stop()
            self._set_key(k, False)
        return False

    def _set_key(self, key: int, down: bool):
        pill = {
            QtCore.Qt.Key.Key_W:self.pillW, QtCore.Qt.Key.Key_A:self.pillA,
            QtCore.Qt.Key.Key_S:self.pillS, QtCore.Qt.Key.Key_D:self.pillD,
            QtCore.Qt.Key.Key_Up:self.pillUp, QtCore.Qt.Key.Key_Down:self.pillDown,
            QtCore.Qt.Key.Key_Left:self.pillLeft, QtCore.Qt.Key.Key_Right:self.pillRight,
        }.get(key)
        if pill and self.kbOverlay.isVisible(): pill.setPressed(down)

    def _tick_hold(self):
        if not self.kbOverlay.isVisible() or self.stopToggle: return
        mods = QtWidgets.QApplication.keyboardModifiers()
        step = self.step*4 if (mods & QtCore.Qt.KeyboardModifier.ShiftModifier) else self.step
        delta = (1 if self.hold_up else 0) - (1 if self.hold_down else 0)
        if delta:
            for m in self.MotorPowers:
                v = self.MotorPowers[m] + delta*step
                self.MotorPowers[m] = max(0, min(self.fullPower, v))
            self._send_current_powers()
