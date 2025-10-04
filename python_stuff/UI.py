import socket, time,sys
from enum import Enum
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtNetwork import QTcpSocket,QAbstractSocket
import struct, math

PACKET_LEN = 20
A_SENS = 16384.0  # MPU9250/MPU6050 accel LSB/g (adjust if different)
VBAT_RATIO = 13.21 # voltage max for battery should be 12.6V dont go below 10.5V absolute minimum 9V will fuck it 

HOST_DEFAULT = "192.168.4.1"
PORT_DEFAULT = 2323
SEND_HZ = 30

class mode(Enum):
    connect = 0
    startMotors = 1
    stopMotors = 2
    fly = 3


## pin23 voltage from battery on divider

class TiltBall(QtWidgets.QWidget):
    """Unit circle with a dot at (x,y) where x,y ∈ [-1,1]."""
    def __init__(self, diameter=220, parent=None):
        super().__init__(parent)
        self._x = 0.0
        self._y = 0.0
        self._pad = 12
        self.setFixedSize(diameter, diameter)

    def set_xy(self, x: float, y: float):
        # clamp to [-1,1]
        x = max(-1.0, min(1.0, float(x)))
        y = max(-1.0, min(1.0, float(y)))
        if x != self._x or y != self._y:
            self._x, self._y = x, y
            self.update()

    # optional: convenience from accelerometer in g's
    def set_from_g(self, ax_g: float, ay_g: float, az_g: float):
        g = (ax_g*ax_g + ay_g*ay_g + az_g*az_g) ** 0.5 or 1.0
        self.set_xy(ax_g / g, ay_g / g)

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        r = self.rect().adjusted(self._pad, self._pad, -self._pad, -self._pad)
        center = QtCore.QPointF(r.center())
        radius = min(r.width(), r.height()) / 2.0

        # background
        p.fillRect(self.rect(), QtGui.QColor("#ffffff"))

        # grid cross
        pen_grid = QtGui.QPen(QtGui.QColor("#d0d0d0"), 1)
        p.setPen(pen_grid)
        p.drawLine(int(center.x()), r.top(), int(center.x()), r.bottom())
        p.drawLine(r.left(), int(center.y()), r.right(), int(center.y()))

        # unit circle
        pen_circle = QtGui.QPen(QtGui.QColor("#888"), 2)
        p.setPen(pen_circle)
        p.drawEllipse(center, radius, radius)

        # ball
        px = center.x() + self._x * radius
        py = center.y() - self._y * radius  # invert Y for screen coords
        dot_r = 8
        p.setBrush(QtGui.QBrush(QtGui.QColor("#2e8b57")))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawEllipse(QtCore.QPointF(px, py), dot_r, dot_r)

        # axis ticks (optional)
        p.setPen(QtGui.QPen(QtGui.QColor("#bbb"), 1))
        for t in (-0.5, 0.5):
            p.drawLine(int(center.x() + t*radius), int(center.y()-4),
                       int(center.x() + t*radius), int(center.y()+4))
            p.drawLine(int(center.x()-4), int(center.y() - t*radius),
                       int(center.x()+4), int(center.y() - t*radius))

        # text
        p.setPen(QtGui.QPen(QtGui.QColor("#666")))
        p.drawText(self.rect().adjusted(4, 4, -4, -4),
                   QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft,
                   f"x={self._x:+.2f}  y={self._y:+.2f}")
        p.end()

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

class BarPair(QtWidgets.QWidget):
    """Two vertical bars (TX | RX) for a single motor."""
    def __init__(self, max_value=255,bar_w=56, bar_h=140, parent=None):
        super().__init__(parent)
        self.tx = QtWidgets.QProgressBar(); self.tx.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.rx = QtWidgets.QProgressBar(); self.rx.setOrientation(QtCore.Qt.Orientation.Vertical)
        for bar in (self.tx, self.rx):
            bar.setRange(0, max_value)
            bar.setTextVisible(False)
            bar.setFixedSize(bar_w, bar_h)
            bar.setStyleSheet("""
                QProgressBar { background:#eee; border:1px solid #ccc; border-radius:3px; }
                QProgressBar::chunk { background:#2e8b57; }
            """)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(6)
        lay.addWidget(self.tx); lay.addWidget(self.rx)

    def setMax(self, m: int):
        self.tx.setRange(0, m); self.rx.setRange(0, m)

    def setTX(self, v: int):
        self.tx.setValue(max(0, min(self.tx.maximum(), int(v))))

    def setRX(self, v: int):
        self.rx.setValue(max(0, min(self.rx.maximum(), int(v))))

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

class BatteryIndicator(QtWidgets.QWidget):
    """
    Battery symbol with percentage and voltage.
    Call set_voltage(volts, cells=3) to update (percent auto-calculated).
    """
    def __init__(self, cells: int = 3, parent=None):
        super().__init__(parent)
        self._cells = cells
        self._volts = 0.0
        self._percent = 0.0
        self._ema = None   # simple smoothing
        self._ema_alpha = 0.15
        self.setFixedSize(500, 120)
        self.setToolTip("Battery")

    # --- public API ---
    def set_voltage(self, volts: float, cells: int | None = None):
        if cells: self._cells = cells
        # light smoothing so it doesn't jump around
        v = float(volts)
        self._ema = v if self._ema is None else (1-self._ema_alpha)*self._ema + self._ema_alpha*v
        self._volts = self._ema
        self._percent = self._estimate_soc_percent(self._volts / max(1, self._cells))
        self.update()

    def set_percent(self, percent: float, volts: float | None = None):
        self._percent = max(0.0, min(100.0, float(percent)))
        if volts is not None:
            self._volts = float(volts)
        self.update()

    # --- LiPo OCV table (rough, per-cell, at rest) & interpolation ---
    def _estimate_soc_percent(self, vpc: float) -> float:
        table = [
            (4.20, 100), (4.15, 95), (4.10, 90), (4.05, 85),
            (4.00, 78), (3.95, 70), (3.90, 62), (3.85, 56),
            (3.80, 45), (3.75, 35), (3.70, 25), (3.65, 18),
            (3.60, 12), (3.55,  9), (3.50,  7), (3.45,  4),
            (3.40,  2), (3.30,  0),
        ]
        if vpc >= table[0][0]: return 100.0
        if vpc <= table[-1][0]: return 0.0
        for i in range(len(table)-1):
            v1, p1 = table[i]
            v2, p2 = table[i+1]
            if v2 <= vpc <= v1:
                t = (vpc - v2) / (v1 - v2)
                return p2 + t*(p1 - p2)
        return 0.0

    def _fill_color(self):
        p = self._percent
        if p >= 60: return QtGui.QColor("#2e8b57")  # green
        if p >= 30: return QtGui.QColor("#f9a825")  # yellow
        return QtGui.QColor("#d32f2f")              # red

    # --- painting ---
    def paintEvent(self, ev):
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(8, 8, -8, -8)

        # battery body + cap geometry
        body = QtCore.QRectF(rect.left(), rect.top(), rect.width()-18, rect.height())
        cap_w = 10
        cap_h = body.height() * 0.45
        cap = QtCore.QRectF(body.right()+2, body.center().y()-cap_h/2, cap_w, cap_h)

        # outline
        p.setPen(QtGui.QPen(QtGui.QColor("#666"), 2))
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, 6, 6)
        p.drawRoundedRect(cap, 3, 3)

        # fill
        inner = body.adjusted(4, 4, -4, -4)
        pct = max(0.0, min(1.0, self._percent/100.0))
        fill_w = inner.width() * pct
        fill_rect = QtCore.QRectF(inner.left(), inner.top(), fill_w, inner.height())
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(self._fill_color())
        p.drawRoundedRect(fill_rect, 4, 4)

        # text (volts + percent)
        p.setPen(QtGui.QPen(QtGui.QColor("#333")))
        txt = f"{self._volts:4.2f} V  ({self._percent:3.0f}%)"
        p.drawText(self.rect().adjusted(0, 0, -6, -6),
                   QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignBottom, txt)
        p.end()

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
        self.battery = BatteryIndicator(cells=3)  # 3S LiPo
        leftLayout.addWidget(self.battery, 0,
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom)


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

        self.tiltBall = TiltBall(diameter=500)

        # make sure it sits in the top-right corner
        rightLayout.addWidget(self.tiltBall, 0, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight)


        self.order = ('FrontLeft','FrontRight','BackLeft','BackRight')

        # bars row (TX|RX pair per motor)
        self.barPairs, self.txLabels, self.rxLabels = {}, {}, {}
        CELL_W, BAR_H = 120,400

        ioBox = QtWidgets.QGroupBox("Motor I/O")
        ioBox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                            QtWidgets.QSizePolicy.Policy.Expanding)
        ioGrid = QtWidgets.QGridLayout(ioBox)
        ioGrid.setContentsMargins(0,10,10,10)
        ioGrid.setHorizontalSpacing(18)
        ioGrid.setVerticalSpacing(8)

        # header row
        ioGrid.addWidget(QtWidgets.QLabel(""), 0, 0)
        for c, name in enumerate(self.order, start=1):
            lab = QtWidgets.QLabel(name)
            lab.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lab.setStyleSheet("color:#555; font-weight:600;")
            ioGrid.addWidget(lab, 0, c)

        # helper to make numeric "bubble"
        def _mkCell():
            lbl = QtWidgets.QLabel("0")
            lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(CELL_W)  # <- match bar width
            lbl.setStyleSheet("font-family: Consolas, monospace; font-size:14px; "
                            "background:#f2f2f2; border-radius:6px; padding:4px 6px;")
            return lbl

        # one column per motor: bars (TX|RX) on top, numbers (TX RX) on one line below
        for c, name in enumerate(self.order, start=1):
            col = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(col)
            v.setContentsMargins(0,0,0,0); v.setSpacing(6)

            bp = BarPair(self.fullPower, bar_w=CELL_W, bar_h=BAR_H)
            self.barPairs[name] = bp
            v.addWidget(bp, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

            rowNums = QtWidgets.QHBoxLayout(); rowNums.setSpacing(8)
            tx = _mkCell(); rx = _mkCell()
            self.txLabels[name] = tx; self.rxLabels[name] = rx
            rowNums.addWidget(tx); rowNums.addWidget(rx)
            v.addLayout(rowNums)

            ioGrid.addWidget(col, 1, c, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

        # Put it at the bottom of the right column
        rightLayout.addWidget(ioBox, 1)

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
        self.rxbuf = bytearray()
        self.s.readyRead.connect(self._on_ready_read)
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
        for name, val in zip(self.order, data):
            self.txLabels[name].setText(str(val))
            self.barPairs[name].setTX(val)

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

    def _on_ready_read(self):
        # accumulate bytes
        self.rxbuf.extend(self.s.readAll().data())
        # process whole frames
        while len(self.rxbuf) >= PACKET_LEN:
            frame = bytes(self.rxbuf[:PACKET_LEN])
            del self.rxbuf[:PACKET_LEN]
            self._handle_frame(frame)


    def _handle_frame(self, frame: bytes):
        # 0..3: motor bytes, 4..17: IMU payload (14 bytes)
        bat_adc = (frame[0] << 8) | frame[1]
        batV = (bat_adc / 4095) * VBAT_RATIO
        if hasattr(self, "battery"):
            self.battery.set_voltage(batV, cells=3)

        

        m0, m1, m2, m3 = frame[2], frame[3], frame[4], frame[5]
        # Update RX numbers + bars
        try:
            order = self.order  # ('FrontLeft','FrontRight','BackLeft','BackRight')
        except AttributeError:
            order = ('FrontLeft','FrontRight','BackLeft','BackRight')
        for name, val in zip(order, (m0, m1, m2, m3)):
            if hasattr(self, "rxLabels"):   self.rxLabels[name].setText(str(val))
            if hasattr(self, "barPairs"):   self.barPairs[name].setRX(val)

        imu = frame[6:20]  # 14 bytes
        # 7 big-endian int16: ax, ay, az, gx, gy, gz, temp(or spare)
        try:
            ax, ay, az, gx, gy, gz, _ = struct.unpack(">7h", imu)
        except struct.error:
            return
        ax_g, ay_g, az_g = ax / A_SENS, ay / A_SENS, az / A_SENS
        # normalize to unit vector and update ball
        gmag = math.sqrt(ax_g*ax_g + ay_g*ay_g + az_g*az_g) or 1.0
        x = ax_g / gmag
        y = ay_g / gmag
        if hasattr(self, "tiltBall"):
            self.tiltBall.set_xy(x, y)

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