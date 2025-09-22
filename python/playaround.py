import socket

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

set_motors()
send_powers()

