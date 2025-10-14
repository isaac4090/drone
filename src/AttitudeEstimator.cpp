#include "AttitudeEstimator.h"
#include <math.h>


bool AttitudeEstimator::startLevelCal(uint32_t window_ms) {
  cal_running_ = true; cal_done_ = false;
  cal_t0_ = millis(); cal_ms_ = window_ms;
  cal_n_ = 0; cal_sR_ = cal_sP_ = 0.0;
  return true;
}

bool AttitudeEstimator::isLevelCalRunning() const { return cal_running_; }
bool AttitudeEstimator::isLevelCalDone() const    { return cal_done_; }

bool AttitudeEstimator::cancelLevelCal() {
  cal_running_ = cal_done_ = false;
  return true;
}

void AttitudeEstimator::update(const SI& s, float dt){
  gx_=s.gx_dps; gy_=s.gy_dps;
  const float roll_acc  = atan2f(s.ay_g, s.az_g) * 57.29578f;
  const float pitch_acc = atan2f(-s.ax_g, sqrtf(s.ay_g*s.ay_g + s.az_g*s.az_g)) * 57.29578f;
  roll_  = alpha_*(roll_  + gx_*dt) + (1.0f-alpha_)*roll_acc;
  pitch_ = alpha_*(pitch_ + gy_*dt) + (1.0f-alpha_)*pitch_acc;

  // If calibrating, accumulate *after* fusion so we trim what the UI/controller see
  if (cal_running_) {
    cal_sR_ += roll_;
    cal_sP_ += pitch_;
    ++cal_n_;
    if (millis() - cal_t0_ >= cal_ms_) {
      if (cal_n_ >= 200) {
        trim_roll_deg_  = -(float)(cal_sR_ / cal_n_);
        trim_pitch_deg_ = -(float)(cal_sP_ / cal_n_);
      }
      cal_running_ = false;
      cal_done_ = true;
    }
  }
}