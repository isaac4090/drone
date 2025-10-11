import math, struct
from .config import A_SENS, VBAT_RATIO, RESET_EXPLAIN, PKT_ANGLES, PKT_DEBUG





def xor8(b: bytes) -> int:
    x = 0
    for v in b: x ^= v
    return x & 0xFF

def parse_frame(frame: bytes, debug:bool = False, ADCValue:int = None):
    """Return dict: batV, bat_adc, motors(tuple), x, y, imu14."""

    if not frame:
        return None
    
    fType = frame[0]

    if fType == PKT_ANGLES:
        out = parse_fast_frame(frame)
        # if run in debug mode. esp32 powered via usb or sperate supply, allow user set voltage
        if debug:
            if 'batV' in out:
                out['batV'] = ADCValue

    elif fType == PKT_DEBUG:
        out = parse_slow_frame(frame)
    return out

def parse_slow_frame(pkt:bytes):
    (ptype, seq, loop_us,
     e_roll_c, e_pitch_c,
     u_r_c, u_p_c, csum) = struct.unpack(">B H H h h h h B", pkt)

    recivedCsum = xor8(pkt[:-1])
    if recivedCsum != csum:
        print(f"checksum mismatch slow frame, from drone: {csum} from new calc: {recivedCsum}")
        print(ptype, seq, loop_us,e_roll_c, e_pitch_c,u_r_c, u_p_c, csum)
        return None
    
    return {
        "type": ptype,
        "seq": seq,
        "loop_us": loop_us,           # µs between slow frames
        "e_roll":  e_roll_c  / 100.0, # deg
        "e_pitch": e_pitch_c / 100.0, # deg
        "u_r":     u_r_c     / 100.0, # control effort (roll)
        "u_p":     u_p_c     / 100.0, # control effort (pitch)
    }
    


def parse_fast_frame(pkt:bytes):
    (ptype, seq, loop_us, bat_adc,
     m0, m1, m2, m3,
     roll_c, pitch_c, gx_c, gy_c, csum) = struct.unpack(">B H H H 4B h h h h B", pkt)
    
    recivedCsum = xor8(pkt[:-1])
    if recivedCsum != csum:
        print(f"checksum mismatch fast frame, from drone: {csum} from new calc: {recivedCsum}")
        print(ptype, seq, loop_us, bat_adc,
     m0, m1, m2, m3,
     roll_c, pitch_c, gx_c, gy_c, csum)
        return None
    
    roll_deg  = roll_c  / 100.0
    pitch_deg = pitch_c / 100.0
    gx_dps    = gx_c    / 100.0
    gy_dps    = gy_c    / 100.0

    batV = (bat_adc / 4095.0) * VBAT_RATIO

    x = math.sin(math.radians(roll_deg))   # side tilt
    y = math.sin(math.radians(pitch_deg))  # fore/aft tilt

    return {
        "type": ptype,
        "seq": seq,
        "loop_us": loop_us,
        "bat_adc": bat_adc,
        "batV": batV,
        "motors": (m0, m1, m2, m3),
        "roll_deg": roll_deg,
        "pitch_deg": pitch_deg,
        "gx_dps": gx_dps,
        "gy_dps": gy_dps,
        "x": x,
        "y": y,
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