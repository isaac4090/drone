from PyQt6 import QtCore, QtGui, QtWidgets

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
    # 2 rows x 3 colsI
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
        self._ema_alpha = 0.5
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