# Protocol and timing
MAX_BUF = 400 # max wifi buffer lenght
PKT_ANGLES = 0xA2
PKT_DEBUG = 0xA3
CMD_MAGIC = 0xC1 # send pkt magic byte/ identity
MODE_STOP = 0
MODE_FLY  = 1
PKT_SIZES = {PKT_ANGLES: 20, PKT_DEBUG: 14}
SEND_HZ = 30 # how often the motor powers are send computer -> drone
UI_FPS = 30 # How often UI repaints last telemetry drome -> computer changes UI

# IMU
A_SENS = 16384.0  # MPU9250/MPU6050 accel LSB/g 

# battery scaling
VBAT_RATIO = 13.21 # voltage max for battery should be 12.6V dont go below 10.5V absolute minimum 9V will fuck it 
SWITCH_ON_TH  = 8  
SWITCH_OFF_TH = 5
DEBUG_ADC_HIGH = 12
DEBUG_ADC_LOW = -0

# Wifi defualts
HOST_DEFAULT = "192.168.4.1"
PORT_DEFAULT = 2323

# Motor stuff
MOTOR_ORDER = ("FrontLeft","FrontRight","BackLeft","BackRight")
FULL_POWER  = 180
STEP        = 1
SLOW_POWER = 5
ZERO = 0
BEEPING_TIME_MS = 700  
SWITCH_TIMEOUT = 30000

RESET_EXPLAIN = {
    "POWERON":   "Power cycled. Likely switch toggled or intermittent power/regulator/connector.",
    "BROWNOUT":  "3.3V rail dipped below brown-out threshold (~2.9–3.0 V). Check power/loads/wiring.",
    "SW_RESET":  "Software restart (esp_restart was called).",
    "WDT":       "Watchdog timeout. A task or loop blocked too long.",
    "TASK_WDT":  "Task watchdog timeout. A specific task stalled.",
    "INT_WDT":   "Interrupt watchdog timeout.",
    "PANIC":     "Crash/exception (Guru Meditation). Check serial logs/backtrace.",
    "EXT_PIN":   "External reset pin toggled (EN/RST).",
    "DEEPSLEEP": "Woke up from deep sleep.",
    "SDIO":      "Reset via SDIO (rare).",
    "OK":        "Normal reconnect (no new reset).",
}