import math, struct
from .config import A_SENS, VBAT_RATIO

def parse_frame(frame: bytes):
    """Return dict: batV, bat_adc, motors(tuple), x, y, imu14."""
    bat_adc = (frame[0] << 8) | frame[1]
    m0, m1, m2, m3 = frame[2], frame[3], frame[4], frame[5]
    imu14 = frame[6:20]

    # accel/gyro as big-endian int16
    ax, ay, az, gx, gy, gz, _ = struct.unpack(">7h", imu14)
    ax_g, ay_g, az_g = ax / A_SENS, ay / A_SENS, az / A_SENS
    g = math.sqrt(ax_g*ax_g + ay_g*ay_g + az_g*az_g) or 1.0
    x = ax_g / g
    y = ay_g / g

    # battery from ADC -> voltage
    batV = (bat_adc / 4095.0) * VBAT_RATIO

    return {
        "bat_adc": bat_adc,
        "batV": batV,
        "motors": (m0, m1, m2, m3),
        "x": x, "y": y,
        "imu14": imu14,
    }
