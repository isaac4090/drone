# Protocol and timing
PACKET_LEN = 20 # lenght of packet sent for the drone
SEND_HZ = 30 # how often the motor powers are send computer -> drone
UI_FPS = 30 # How often UI repaints last telemetry drome -> computer changes UI

# IMU
A_SENS = 16384.0  # MPU9250/MPU6050 accel LSB/g 

# battery scaling
VBAT_RATIO = 13.21 # voltage max for battery should be 12.6V dont go below 10.5V absolute minimum 9V will fuck it 
SWITCH_ON_TH  = 8  
SWITCH_OFF_TH = 3

# Wifi defualts
HOST_DEFAULT = "192.168.4.1"
PORT_DEFAULT = 2323

# Motor stuff
MOTOR_ORDER = ("FrontLeft","FrontRight","BackLeft","BackRight")
FULL_POWER  = 180
STEP        = 1