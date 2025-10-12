from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from collections import deque
import math

class TiltBall(QtWidgets.QWidget):
    """Unit circle with two dots: actual and desired.
       Degree-based full scale (edge of circle = full_scale_deg).
    """
    def __init__(self, diameter=220, parent=None, full_scale_deg=30.0):
        super().__init__(parent)
        self._pad = 12
        self.setFixedSize(diameter, diameter)

        # actual and desired in degrees (roll=x, pitch=y)
        self._act_roll = 0.0
        self._act_pitch = 0.0
        self._des_roll = 0.0
        self._des_pitch = 0.0

        self._full_scale_deg = float(full_scale_deg)  # circle edge = ±full_scale_deg

    # --- new degree-based API ---
    def set_actual_deg(self, roll_deg: float, pitch_deg: float):
        r = float(roll_deg); p = float(pitch_deg)
        if r != self._act_roll or p != self._act_pitch:
            self._act_roll, self._act_pitch = r, p
            self.update()

    def set_desired_deg(self, roll_deg: float, pitch_deg: float):
        r = float(roll_deg); p = float(pitch_deg)
        if r != self._des_roll or p != self._des_pitch:
            self._des_roll, self._des_pitch = r, p
            self.update()

    def set_fullscale_deg(self, deg: float):
        self._full_scale_deg = max(1.0, float(deg))
        self.update()

    def set_from_g(self, ax_g: float, ay_g: float, az_g: float):
        g = (ax_g*ax_g + ay_g*ay_g + az_g*az_g) ** 0.5 or 1.0
        x = ax_g / g
        y = ay_g / g
        self.set_xy(x, y)

    def _deg_to_norm(self, roll_deg: float, pitch_deg: float) -> tuple[float, float]:
        fs = self._full_scale_deg
        # small-angle: normalize directly by full-scale degrees
        x = max(-1.0, min(1.0, roll_deg / fs))
        y = max(-1.0, min(1.0, pitch_deg / fs))
        return x, y

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        r = self.rect().adjusted(self._pad, self._pad, -self._pad, -self._pad)
        center = QtCore.QPointF(r.center())
        radius = min(r.width(), r.height()) / 2.0

        # background
        p.fillRect(self.rect(), QtGui.QColor("#ffffff"))

        # grid cross
        p.setPen(QtGui.QPen(QtGui.QColor("#d0d0d0"), 1))
        p.drawLine(int(center.x()), r.top(), int(center.x()), r.bottom())
        p.drawLine(r.left(), int(center.y()), r.right(), int(center.y()))

        # unit circle
        p.setPen(QtGui.QPen(QtGui.QColor("#888"), 2))
        p.drawEllipse(center, radius, radius)

        # ticks (±full-scale and mid)
        p.setPen(QtGui.QPen(QtGui.QColor("#bbb"), 1))
        for t in (-0.5, 0.0, 0.5):
            # vertical tick positions
            p.drawLine(int(center.x() + t*radius), int(center.y()-4),
                       int(center.x() + t*radius), int(center.y()+4))
            p.drawLine(int(center.x()-4), int(center.y() - t*radius),
                       int(center.x()+4), int(center.y() - t*radius))

        # desired dot (orange)
        dx, dy = self._deg_to_norm(self._des_roll, self._des_pitch)
        p.setBrush(QtGui.QBrush(QtGui.QColor("#ff7f0e")))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        px = center.x() + dx * radius
        py = center.y() - dy * radius
        p.drawEllipse(QtCore.QPointF(px, py), 8, 8)

        # actual dot (green)
        ax, ay = self._deg_to_norm(self._act_roll, self._act_pitch)
        p.setBrush(QtGui.QBrush(QtGui.QColor("#2e8b57")))
        px = center.x() + ax * radius
        py = center.y() - ay * radius
        p.drawEllipse(QtCore.QPointF(px, py), 8, 8)

        # legend text
        p.setPen(QtGui.QPen(QtGui.QColor("#666")))
        fs = self._full_scale_deg
        p.drawText(self.rect().adjusted(4, 4, -4, -4),
                   QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft,
                   f"Actual: roll={self._act_roll:+.1f}°, pitch={self._act_pitch:+.1f}°\n"
                   f"Desired: roll={self._des_roll:+.1f}°, pitch={self._des_pitch:+.1f}°  (FS={fs:.0f}°)")
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


class GraphsPanel3x2(QtWidgets.QFrame):
    """Inline 3x2 graphs (same layout as full window) + fullscreen button.
       Public API:
         - append_fast(roll_deg, pitch_deg, gx_dps, gy_dps, motors, batV, baseline, tsec)
         - append_sample(e_roll, e_pitch, u_r, u_p, tsec)
         - clear()
         - requestFullscreen (signal)
    """
    requestFullscreen = QtCore.pyqtSignal()

    def __init__(self, history_secs: float = 20.0, refresh_hz: int = 30, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setObjectName("GraphsPanel3x2")
        self.setStyleSheet("""
            #GraphsPanel3x2 {
                background: #fafafa;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # Header row with title + fullscreen tool button
        hdr = QtWidgets.QHBoxLayout()
        lab = QtWidgets.QLabel("Telemetry (Fast + Control)")
        lab.setStyleSheet("font-weight:600; color:#333;")
        hdr.addWidget(lab)
        hdr.addStretch(1)
        self._btnFull = QtWidgets.QToolButton()
        self._btnFull.setToolTip("Open full-screen graphs")
        self._btnFull.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self._btnFull.clicked.connect(self.requestFullscreen.emit)
        hdr.addWidget(self._btnFull)
        outer.addLayout(hdr)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        outer.addLayout(grid)

        # Timebases
        max_pts = int(history_secs * 200)
        self._tx_fast = deque(maxlen=max_pts)  # A2
        self._tx_ctrl = deque(maxlen=max_pts)  # A3

        def mkplot(title: str, legend=False) -> pg.PlotWidget:
            pw = pg.PlotWidget(title=title)
            pw.showGrid(x=True, y=True)
            pw.setClipToView(True)
            pw.setDownsampling(mode='peak')
            if legend:
                pw.addLegend()
            return pw

        # ---------- FAST (A2) ----------
        self._roll  = deque(maxlen=max_pts); self._pitch = deque(maxlen=max_pts)
        self._gx    = deque(maxlen=max_pts); self._gy    = deque(maxlen=max_pts)
        self._m0 = deque(maxlen=max_pts); self._m1 = deque(maxlen=max_pts)
        self._m2 = deque(maxlen=max_pts); self._m3 = deque(maxlen=max_pts)
        self._mbase = deque(maxlen=max_pts)
        self._batV  = deque(maxlen=max_pts)

        self._p_att = mkplot("Attitude (deg)", legend=True)
        self._cur_roll  = self._p_att.plot(name='roll',  pen=pg.mkPen('#1f77b4', width=2))  # blue
        self._cur_pitch = self._p_att.plot(name='pitch', pen=pg.mkPen('#ff7f0e', width=2))  # orange
        grid.addWidget(self._p_att, 0, 0)

        self._p_rates = mkplot("Rates (deg/s)", legend=True)
        self._cur_gx = self._p_rates.plot(name='gx', pen=pg.mkPen('#9467bd', width=2))  # purple
        self._cur_gy = self._p_rates.plot(name='gy', pen=pg.mkPen('#2ca02c', width=2))  # green
        grid.addWidget(self._p_rates, 0, 1)

        self._p_mot = mkplot("Motors + Baseline", legend=True)
        self._p_mot.setYRange(0, 255)
        self._cur_m0 = self._p_mot.plot(name='FL', pen=pg.mkPen('#d62728', width=2))  # red
        self._cur_m1 = self._p_mot.plot(name='FR', pen=pg.mkPen('#2ca02c', width=2))  # green
        self._cur_m2 = self._p_mot.plot(name='BL', pen=pg.mkPen('#1f77b4', width=2))  # blue
        self._cur_m3 = self._p_mot.plot(name='BR', pen=pg.mkPen('#ff7f0e', width=2))  # orange
        self._cur_mbase = self._p_mot.plot(name='baseline',
                                           pen=pg.mkPen('#7f7f7f', width=2,
                                                        style=QtCore.Qt.PenStyle.DashLine))
        grid.addWidget(self._p_mot, 1, 0)

        self._p_bat = mkplot("Battery (V)")
        self._cur_bat = self._p_bat.plot(name='V', pen=pg.mkPen('#17becf', width=2))  # teal
        grid.addWidget(self._p_bat, 1, 1)

        # ---------- CONTROL (A3) ----------
        self._e_roll = deque(maxlen=max_pts); self._e_pitch = deque(maxlen=max_pts)
        self._u_r    = deque(maxlen=max_pts); self._u_p     = deque(maxlen=max_pts)

        self._p_err = mkplot("Error (deg)", legend=True)
        self._cur_e_roll  = self._p_err.plot(name='e_roll',  pen=pg.mkPen('#1f77b4', width=2))   # blue
        self._cur_e_pitch = self._p_err.plot(name='e_pitch', pen=pg.mkPen('#ff7f0e', width=2))   # orange
        grid.addWidget(self._p_err, 2, 0)

        self._p_eff = mkplot("Effort", legend=True)
        self._cur_u_r = self._p_eff.plot(name='u_roll', pen=pg.mkPen('#9467bd', width=2))        # purple
        self._cur_u_p = self._p_eff.plot(name='u_pitch', pen=pg.mkPen('#2ca02c', width=2))       # green
        grid.addWidget(self._p_eff, 2, 1)

        for c in (0, 1): grid.setColumnStretch(c, 1)
        for r in (0, 1, 2): grid.setRowStretch(r, 1)

        # repaint timer
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._redraw)
        self._timer.start(int(1000 / refresh_hz))

    # ---------- Public API ----------
    def append_fast(self, roll_deg, pitch_deg, gx_dps, gy_dps, motors, batV, baseline, tsec):
        self._tx_fast.append(float(tsec))

        def f(x):
            try:
                v = float(x);  return v if math.isfinite(v) else 0.0
            except Exception:
                return 0.0

        self._roll.append(f(roll_deg));   self._pitch.append(f(pitch_deg))
        self._gx.append(f(gx_dps));       self._gy.append(f(gy_dps))
        m0, m1, m2, m3 = motors
        self._m0.append(int(m0)); self._m1.append(int(m1))
        self._m2.append(int(m2)); self._m3.append(int(m3))
        if baseline is None:
            self._mbase.append((int(m0)+int(m1)+int(m2)+int(m3))/4.0)
        else:
            self._mbase.append(f(baseline))
        self._batV.append(f(batV))

    def append_sample(self, e_roll, e_pitch, u_r, u_p, tsec):
        self._tx_ctrl.append(float(tsec))

        def f(x):
            try:
                v = float(x);  return v if math.isfinite(v) else 0.0
            except Exception:
                return 0.0

        self._e_roll.append(f(e_roll));   self._e_pitch.append(f(e_pitch))
        self._u_r.append(f(u_r));         self._u_p.append(f(u_p))

    def clear(self):
        for dq in (self._tx_fast, self._tx_ctrl,
                   self._roll, self._pitch, self._gx, self._gy,
                   self._m0, self._m1, self._m2, self._m3, self._mbase, self._batV,
                   self._e_roll, self._e_pitch, self._u_r, self._u_p):
            dq.clear()

    # ---------- redraw ----------
    def _redraw(self):
        # FAST
        if self._tx_fast:
            xf = list(self._tx_fast)
            self._cur_roll.setData(xf, list(self._roll))
            self._cur_pitch.setData(xf, list(self._pitch))
            self._cur_gx.setData(xf, list(self._gx))
            self._cur_gy.setData(xf, list(self._gy))
            self._cur_m0.setData(xf, list(self._m0))
            self._cur_m1.setData(xf, list(self._m1))
            self._cur_m2.setData(xf, list(self._m2))
            self._cur_m3.setData(xf, list(self._m3))
            self._cur_mbase.setData(xf, list(self._mbase))
            self._cur_bat.setData(xf, list(self._batV))
            tmaxf = xf[-1]; tminf = max(0.0, tmaxf - 10.0)
            for pw in (self._p_att, self._p_rates, self._p_mot, self._p_bat):
                pw.setXRange(tminf, tmaxf)

        # CONTROL
        if self._tx_ctrl:
            xc = list(self._tx_ctrl)
            self._cur_e_roll.setData(xc, list(self._e_roll))
            self._cur_e_pitch.setData(xc, list(self._e_pitch))
            self._cur_u_r.setData(xc, list(self._u_r))
            self._cur_u_p.setData(xc, list(self._u_p))
            tmaxc = xc[-1]; tminc = max(0.0, tmaxc - 10.0)
            for pw in (self._p_err, self._p_eff):
                pw.setXRange(tminc, tmaxc)

class TelemetryWindow(QtWidgets.QMainWindow):
    def __init__(self, history_secs=20.0, refresh_hz=30, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Drone Telemetry (Full)")
        self.panel = GraphsPanel3x2(history_secs=history_secs, refresh_hz=refresh_hz, parent=self)
        self.setCentralWidget(self.panel)

    # pass-through API so caller can feed it exactly like the inline panel
    def append_fast(self, *args, **kwargs):   self.panel.append_fast(*args, **kwargs)
    def append_sample(self, *a, **k):         self.panel.append_sample(*a, **k)
    def clear(self):                          self.panel.clear()