#pragma once
#include "IMU.h"

class AttitudeEstimator {
public:
  explicit AttitudeEstimator(float alpha=0.98f): alpha_(alpha) {}
  void reset(float roll0=0, float pitch0=0) { roll_=roll0; pitch_=pitch0; }
  void update(const SI& si, float dt);
  float roll_deg()  const { return roll_ + trim_roll_deg_; }
  float pitch_deg() const { return pitch_ + trim_pitch_deg_; }
  float gx_dps() const { return gx_; }
  float gy_dps() const { return gy_; }
  bool startLevelCal(uint32_t window_ms = 1500);
  bool isLevelCalRunning() const;
  bool isLevelCalDone() const;   // true when trims applied
  bool cancelLevelCal();
private:
  float alpha_;
  float roll_=0, pitch_=0;
  float gx_=0, gy_=0;
  float trim_roll_deg_ = 0.0f;
  float trim_pitch_deg_ = 0.0f;
  bool cal_running_ = false, cal_done_ = false;
  uint32_t cal_t0_ = 0, cal_ms_ = 0;
  uint32_t cal_n_ = 0;
  double cal_sR_ = 0.0, cal_sP_ = 0.0;
};