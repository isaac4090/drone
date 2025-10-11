#pragma once
#include <stdint.h>

struct Gains { float Kp, Ki, Kd; };

class TiltController {
public:
  TiltController(Gains roll, Gains pitch)
    : gr_(roll), gp_(pitch) {}

  void zeroIntegrators() { ir_=0; ip_=0; }
  void clampIntegrators(float lim){ if(ir_>lim)ir_=lim; if(ir_<-lim)ir_=-lim; if(ip_>lim)ip_=lim; if(ip_<-lim)ip_=-lim; }

  float I_roll() const { return ir_; }
  float I_pitch() const { return ip_; }
  float U_roll() const { return ur; }
  float U_pitch() const { return up; }
  void update(float des_roll, float des_pitch,
              float m_roll, float m_pitch,
              float gx_dps, float gy_dps,
              float dt,
              uint8_t mFL_in, uint8_t mFR_in, uint8_t mBL_in, uint8_t mBR_in,
              uint8_t& outFL, uint8_t& outFR, uint8_t& outBL, uint8_t& outBR);
private:
  Gains gr_, gp_;
  float ir_=0, ip_=0, ur = 0, up = 0;
};