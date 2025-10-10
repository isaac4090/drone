#pragma once
#include "IMU.h"

class AttitudeEstimator {
public:
  explicit AttitudeEstimator(float alpha=0.98f): alpha_(alpha) {}
  void reset(float roll0=0, float pitch0=0) { roll_=roll0; pitch_=pitch0; }
  // Update with SI units; dt in seconds
  void update(const SI& si, float dt);
  float roll_deg()  const { return roll_; }
  float pitch_deg() const { return pitch_; }
  float gx_dps() const { return gx_; }
  float gy_dps() const { return gy_; }
private:
  float alpha_;
  float roll_=0, pitch_=0;
  float gx_=0, gy_=0;
};