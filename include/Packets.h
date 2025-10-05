#pragma once
#include <stdint.h>

namespace pkt {
  struct Cmd { uint8_t us[4]; };           // incoming motor powers
  constexpr uint8_t IMU_RAW_LEN = 14;       // ACCEL_XOUT_H .. GYRO_ZOUT_L
  constexpr uint8_t FRAME_LEN   = 20;       // 2 (bat raw) + 4 (motors) + 14 (imu)
}