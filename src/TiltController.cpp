#include "TiltController.h"
static inline float clampf(float x,float a,float b){ return x<a?a:(x>b?b:x); }

void TiltController::update(float des_roll, float des_pitch,
                            float m_roll, float m_pitch,
                            float gx, float gy,
                            float dt,
                            uint8_t bFL,uint8_t bFR,uint8_t bBL,uint8_t bBR,
                            uint8_t& oFL,uint8_t& oFR,uint8_t& oBL,uint8_t& oBR)
{
  float er = des_roll  - m_roll;
  float ep = des_pitch - m_pitch;

  ir_ += er*dt; ip_ += ep*dt;
  clampIntegrators(50.0f);

  ur = gr_.Kp*er + gr_.Ki*ir_ - gr_.Kd*gx; 
  up = gp_.Kp*ep + gp_.Ki*ip_ - gp_.Kd*gy;

  float FL = float(bFL) - up + ur;
  float FR = float(bFR) - up - ur;
  float BL = float(bBL) + up + ur;
  float BR = float(bBR) + up - ur;

  oFL = (uint8_t)clampf(FL, 0.f, 255.f);
  oFR = (uint8_t)clampf(FR, 0.f, 255.f);
  oBL = (uint8_t)clampf(BL, 0.f, 255.f);
  oBR = (uint8_t)clampf(BR, 0.f, 255.f);
}
