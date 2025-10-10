#include "AttitudeEstimator.h"
#include <math.h>

void AttitudeEstimator::update(const SI& s, float dt){
  gx_=s.gx_dps; gy_=s.gy_dps;
  float roll_acc  = atan2f(s.ay_g, s.az_g) * 57.29578f;
  float pitch_acc = atan2f(-s.ax_g, sqrtf(s.ay_g*s.ay_g + s.az_g*s.az_g)) * 57.29578f;
  roll_  = alpha_*(roll_  + gx_*dt) + (1.0f-alpha_)*roll_acc;
  pitch_ = alpha_*(pitch_ + gy_*dt) + (1.0f-alpha_)*pitch_acc;
}
