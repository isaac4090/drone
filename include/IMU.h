#pragma once
#include <Arduino.h>
#include <SPI.h>

// Minimal register set (MPU-9250/6500 family)
constexpr uint8_t REG_WHO_AM_I       = 0x75;
constexpr uint8_t REG_PWR_MGMT_1     = 0x6B;
constexpr uint8_t REG_PWR_MGMT_2     = 0x6C;
constexpr uint8_t REG_CONFIG         = 0x1A;
constexpr uint8_t REG_SMPLRT_DIV     = 0x19;
constexpr uint8_t REG_GYRO_CONFIG    = 0x1B;
constexpr uint8_t REG_ACCEL_CONFIG   = 0x1C;
constexpr uint8_t REG_ACCEL_CONFIG2  = 0x1D;
constexpr uint8_t REG_ACCEL_XOUT_H   = 0x3B;

struct SI {
  float ax_g, ay_g, az_g;   // accel in g
  float gx_dps, gy_dps, gz_dps; // gyro in dps
};

inline int16_t s16(uint8_t hi, uint8_t lo) { return (int16_t)((hi << 8) | lo); }

class IMU {
public:
  void begin(uint8_t pinCS, uint8_t sck, uint8_t miso, uint8_t mosi);
  void readRaw14(uint8_t *buf14);
  void readSI(SI &o);
  uint8_t whoAmI() const { return who; }
private:
  uint8_t cs = 255;
  uint8_t who = 0;
  void write8(uint8_t reg, uint8_t val);
  uint8_t read8(uint8_t reg);
};

