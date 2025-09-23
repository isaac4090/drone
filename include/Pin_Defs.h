#ifndef PIN_DEFS_H
#define PIN_DEFS_H

// Define pins for a motor controller

constexpr int motorFLpin = 27; 
constexpr int motorFRpin = 14; 
constexpr int motorBLpin = 33;
constexpr int motorBRpin = 12; 


// max power
constexpr int powerLimit = 180;

// WiFi stuff
const char* SSID = "Drone";
const char* PASS = "bob";
const uint16_t port = 2323;



// ====== Pins (VSPI defaults on ESP32) ======
static const int PIN_MOSI = 23;
static const int PIN_MISO = 19;
static const int PIN_SCK  = 18;
static const int PIN_CS   = 5;

// ====== MPU-9250 registers ======
#define REG_WHO_AM_I      0x75  // expect 0x71 (MPU9250) or 0x73 (MPU6500/9255)
#define REG_PWR_MGMT_1    0x6B
#define REG_PWR_MGMT_2    0x6C
#define REG_CONFIG        0x1A
#define REG_SMPLRT_DIV    0x19
#define REG_GYRO_CONFIG   0x1B
#define REG_ACCEL_CONFIG  0x1C
#define REG_ACCEL_CONFIG2 0x1D
#define REG_ACCEL_XOUT_H  0x3B  // 14 bytes: AccelX..AccelZ, Temp, GyroX..GyroZ


#endif