import math, struct
from .config import A_SENS, VBAT_RATIO, RESET_EXPLAIN

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

def reset_banner_str(line: str):
    p = {}
    for tok in line.strip().split(','):
        if ':' in tok:
            k, v = tok.split(':', 1)
            p[k.strip().upper()] = v.strip()

    reason = p.get("RST", "UNKNOWN").upper()
    boot   = p.get("BOOT", None)
    pend   = p.get("PEND", None)

    base = RESET_EXPLAIN.get(reason, f"Unknown reset reason '{reason}'.")
    notes = []

    if reason == "POWERON":
        notes.append("Likely power switch toggled or intermittent regulator/connector.")
    elif reason == "BROWNOUT":
        notes.append("Check supply/battery C-rating, wiring resistance, and load steps.")
    elif reason in ("WDT", "TASK_WDT", "INT_WDT"):
        notes.append("Look for blocking loops/I/O; add yields/delays; check long SPI/I2C ops.")
    elif reason == "PANIC":
        notes.append("Open Serial at 115200 to capture stack/backtrace for the exact crash site.")
    elif reason == "EXT_PIN":
        notes.append("Check EN/RST wiring and pull-ups; avoid noise/glitches.")
    elif reason == "SW_RESET":
        notes.append("Search code for esp_restart(); confirm it's intentional (OTA/fatal state).")

    lines = [
        f"Reset reason: {reason}",
        f"Explanation: {base}",
    ]
    if boot is not None:
        lines.append(f"Boot count: {boot}")
    if pend is not None:
        lines.append(f"First connect since reset: {'Yes' if pend == '1' else 'No'}")
    if notes:
        lines.append("Notes: " + " ".join(notes))
    return "\n".join(lines)