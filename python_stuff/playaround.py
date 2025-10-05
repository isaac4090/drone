import socket,struct,  math, time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

HOST, PORT = "192.168.4.1", 2323

MotorPowers = {'FrontLeft': 0,
              'FrontRight': 0,
              'BackLeft':0,
              'BackRight':0}



def set_motors():
    for motor in MotorPowers.keys():
        MotorPowers[motor] = int(input("input" + motor + ": "))

def send_powers():
    with socket.create_connection((HOST, PORT)) as s:
        data  = bytes([MotorPowers[m] for m in MotorPowers])
        s.sendall(data)
        echo = s.recv(4)
        print("sent:", list(data), " echo:", list(echo))


A_SENS = 16384.0

def recv_exact(s, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed")
        buf.extend(chunk)
    return bytes(buf)

def latest14(s):
    """Drop all queued complete frames except the newest, then read that newest 14-byte frame."""
    # Peek at queued bytes without removing them
    queued = len(s.recv(65535, socket.MSG_PEEK))
    # How many full 14-byte frames are waiting?
    frames = queued // 14
    # Discard all but the last full frame (if any)
    if frames > 1:
        s.recv((frames - 1) * 14)
    # Now read exactly the newest frame
    return recv_exact(s, 14)

def sample_xy(s):
    raw = latest14(s)  
    ax, ay, az, _, _, _, _ = struct.unpack(">7h", raw)  # big-endian signed shorts
    ax_g, ay_g, az_g = ax / A_SENS, ay / A_SENS, az / A_SENS
    g = math.sqrt(ax_g*ax_g + ay_g*ay_g + az_g*az_g) or 1.0
    x = ax_g / g
    y = ay_g / g 
    print(ax, ay, az) 
    return x, y


def ball_on_plot():
    with socket.create_connection((HOST, PORT), timeout=5) as s:
        # Matplotlib setup
        fig, ax = plt.subplots()
        ax.set_xlabel("X tilt (|ax|/|g|)")
        ax.set_ylabel("Y tilt (|ay|/|g|)")
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True)
        dot, = ax.plot([1], [0], marker="o", markersize=12)

        # initial
        x_ema, y_ema = 0.0, 0.0

        def update(_frame):
            nonlocal x_ema, y_ema
            try:
                x, y = sample_xy(s)
            except Exception:
                return dot,

            dot.set_data([x], [y])
            ax.set_title(f"x={x:.2f}, y={y:.2f}")
            return dot,

        ani = FuncAnimation(fig, update, blit=True)
        plt.show()


for i in range(20):
    set_motors()
    send_powers()

