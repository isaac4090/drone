from PyQt6 import QtCore
from PyQt6.QtNetwork import QTcpSocket, QAbstractSocket
from .config import PACKET_LEN

class NetClient(QtCore.QObject):
    connected    = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    errorText    = QtCore.pyqtSignal(str)
    frameReady   = QtCore.pyqtSignal(bytes)   # emits a single 20B frame

    def __init__(self, parent=None):
        super().__init__(parent)
        self.s = QTcpSocket(self)
        self.s.setSocketOption(QAbstractSocket.SocketOption.LowDelayOption, 1)  # TCP_NODELAY
        self.s.setReadBufferSize(0)
        self.s.readyRead.connect(self._on_ready_read)
        self.s.connected.connect(self.connected)
        self.s.disconnected.connect(self.disconnected)
        self.s.errorOccurred.connect(lambda e: self.errorText.emit(self.s.errorString()))
        self._rx = bytearray()

    # public 
    def connectTo(self, host: str, port: int):
        self._rx.clear()
        self.s.connectToHost(host, port)

    def disconnect(self):
        if self.s.state() == QAbstractSocket.SocketState.ConnectedState:
            self.s.disconnectFromHost()

    def sendMotors(self, fl: int, fr: int, bl: int, br: int):
        if self.s.state() != QAbstractSocket.SocketState.ConnectedState:
            return
        self.s.write(bytes([fl & 0xFF, fr & 0xFF, bl & 0xFF, br & 0xFF]))

    # private
    def _on_ready_read(self):
        self._rx.extend(self.s.readAll().data())

        # If backlog builds, drop oldest complete frames, keep most recent
        while len(self._rx) >= PACKET_LEN * 2:
            del self._rx[:PACKET_LEN]

        while len(self._rx) >= PACKET_LEN:
            frame = bytes(self._rx[:PACKET_LEN]); del self._rx[:PACKET_LEN]
            self.frameReady.emit(frame)