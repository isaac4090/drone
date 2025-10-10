#include "IMU.h"
#include "config.h"

void IMU::begin(uint8_t pinCS, uint8_t sck, uint8_t miso, uint8_t mosi) {
  cs = pinCS;
  pinMode(cs, OUTPUT);
  digitalWrite(cs, HIGH);

  SPI.begin(sck, miso, mosi);
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE3));

  // Reset & basic config
  write8(REG_PWR_MGMT_1, 0x80); delay(100);
  write8(REG_PWR_MGMT_1, 0x01); // PLL
  write8(REG_PWR_MGMT_2, 0x00); // enable accel+gyro
  write8(REG_CONFIG,        0x03);
  write8(REG_SMPLRT_DIV,    0x04);
  write8(REG_GYRO_CONFIG,   0x18); // ±2000 dps
  write8(REG_ACCEL_CONFIG,  0x00); // ±2g
  write8(REG_ACCEL_CONFIG2, 0x03);

  who = read8(REG_WHO_AM_I);
}

void IMU::readRaw14(uint8_t *buf14) {
  digitalWrite(cs, LOW);
  SPI.transfer(REG_ACCEL_XOUT_H | 0x80);
  for (int i=0;i<14;i++) buf14[i] = SPI.transfer(0x00);
  digitalWrite(cs, HIGH);
}

void IMU::write8(uint8_t reg, uint8_t val) {
  digitalWrite(cs, LOW);
  SPI.transfer(reg & 0x7F);
  SPI.transfer(val);
  digitalWrite(cs, HIGH);
}

uint8_t IMU::read8(uint8_t reg) {
  digitalWrite(cs, LOW);
  SPI.transfer(reg | 0x80);
  uint8_t v = SPI.transfer(0x00);
  digitalWrite(cs, HIGH);
  return v;
}

void IMU::readSI(SI &o){
  uint8_t r[14];
  readRaw14(r);

  const int16_t ax = s16(r[0],  r[1]);
  const int16_t ay = s16(r[2],  r[3]);
  const int16_t az = s16(r[4],  r[5]);

  const int16_t gx = s16(r[8],  r[9]);
  const int16_t gy = s16(r[10], r[11]);
  const int16_t gz = s16(r[12], r[13]);

  o.ax_g   = ax * cfg::ACC_G_PER_LSB;
  o.ay_g   = ay * cfg::ACC_G_PER_LSB;
  o.az_g   = az * cfg::ACC_G_PER_LSB;

  o.gx_dps = gx * cfg::GYRO_DPS_PER_LSB;
  o.gy_dps = gy * cfg::GYRO_DPS_PER_LSB;
  o.gz_dps = gz * cfg::GYRO_DPS_PER_LSB;


}