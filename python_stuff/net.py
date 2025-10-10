from PyQt6 import QtCore
from PyQt6.QtNetwork import QTcpSocket, QAbstractSocket
from .config import PACKET_LEN

class NetClient(QtCore.QObject):
    connected    = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    errorText    = QtCore.pyqtSignal(str)
    frameReady   = QtCore.pyqtSignal(bytes)  
    bannerReceived = QtCore.pyqtSignal(str)

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
        self._expect_banner = False
        self._banner_timeout = QtCore.QElapsedTimer()

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

    def start_banner_detection(self, timeout_ms: int = 1000):
        self._expect_banner = True
        self.s.write(b"HELLO\n")
        self.s.flush()
        self._banner_timeout.start()
        self._banner_deadline_ms = int(timeout_ms)



    # private
    def _on_ready_read(self):

        # getting error/ reset reason from esc
        if self._expect_banner:
            if self._banner_timeout.hasExpired(self._banner_deadline_ms):
                self._expect_banner = False
            else:
                if self.s.canReadLine():
                    line = bytes(self.s.readLine()).decode("utf-8", "replace").strip()
                    
                    # if line.startswith("RST:"):
                    self.bannerReceived.emit(line)
                    
                    self._expect_banner = False
                else:
                    return


        self._rx.extend(self.s.readAll().data())

        # If backlog builds, drop oldest complete frames, keep most recent
        while len(self._rx) >= PACKET_LEN * 2:
            del self._rx[:PACKET_LEN]

        while len(self._rx) >= PACKET_LEN:
            frame = bytes(self._rx[:PACKET_LEN]); del self._rx[:PACKET_LEN]
            self.frameReady.emit(frame)

    