import sys
import argparse, sys
from PyQt6 import QtWidgets
from PyQt6.QtGui import QGuiApplication
from .window import DroneWindow

def main(secondMonitor: bool = False, debug: bool = False, noDrone:bool = False):
    parser = argparse.ArgumentParser()
    parser.add_argument("--second-monitor", action="store_true", help="Move second monitor")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--noDrone", action="store_true", help="Enable UI-only mode (no drone connection), auto debug mode aswell")
    args, qt_args = parser.parse_known_args(sys.argv[1:])

    app = QtWidgets.QApplication([sys.argv[0]] + qt_args)
    win = DroneWindow(debug=args.debug or debug, no_drone=args.noDrone or noDrone)
    if args.second_monitor or secondMonitor:
        screens = QGuiApplication.screens()
        if len(screens) > 1:
            second = screens[2]
            geom = second.geometry()
            win.move(geom.x(), geom.y())
            if win.windowHandle():
                win.windowHandle().setScreen(second)
            win.showFullScreen()
        else:
            win.showMaximized()
    else:
        win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()