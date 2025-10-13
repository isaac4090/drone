#include <Arduino.h>
#include <WiFi.h>
#include "Config.h"
#include "Packets.h"
#include "Motors.h"
#include "IMU.h"
#include "Battery.h"
#include <esp_system.h> 
#include "WifiLink.h"
#include "AttitudeEstimator.h"
#include "TiltController.h"

uint8_t oFL = 0, oFR = 0, oBL = 0, oBR = 0;

static CmdState cmd;

struct Periodic {
  uint32_t next_us=0, period_us=0,last_fire_us = 0;
  void start(uint32_t now, uint32_t period){ next_us=now+period; period_us=period; last_fire_us = now; }
  bool due(uint32_t now) const { return (int32_t)(now - next_us) >= 0; }
  uint32_t advance(uint32_t now){ 
    do { next_us += period_us; } while ((int32_t)(now - next_us) >= 0); 
    uint32_t dt = now - last_fire_us;
    last_fire_us = now;
    return dt;
  }
};

static float Kp_roll  = 0.12f, Ki_roll  = 0.02f, Kd_roll  = 0.0015f;
static float Kp_pitch = 0.12f, Ki_pitch = 0.02f, Kd_pitch = 0.0015f;


IMU imu;
AttitudeEstimator est(0.98f);
TiltController ctrl({Kp_roll, Ki_roll,Kd_roll},{Kp_pitch,Ki_pitch,Kd_pitch});
Motors motors;
Battery batt;
WifiLink wifi;

Periodic ctrlTick, telemTick, slowTelemTick;

static bool wasStreaming = false;

void setup() {
  motors.begin();
  wifi.begin(cfg::PORT, cfg::SSID, cfg::PASS);
  imu.begin(cfg::PIN_CS, cfg::PIN_SCK, cfg::PIN_MISO, cfg::PIN_MOSI);
  batt.begin();

  DBG_BEGIN(115200);
  DBG("AP IP: "); DBGLN(WiFi.softAPIP());
  DBGF("WHO_AM_I = 0x%02X\n", imu.whoAmI());

}

void loop() {
  wifi.handle();

  bool streaming = wifi.inStreaming();

  if(streaming && !wasStreaming){
    // streaming entry, start timers, reset estimator, and controler intergrator
    uint32_t t0 = micros();
    ctrlTick.start(t0, 1000000u / cfg::TILT_CONTR_HZ);
    telemTick.start(t0,1000000u / cfg::TELEMETRY_HZ );
    slowTelemTick.start(t0,1000000u / cfg::SLOWTELMETRY_HZ);
    est.reset(0, 0);
    ctrl.zeroIntegrators();
  }

  if (!streaming && wasStreaming) {
    // streaming stoped, set motors 0
    motors.writeRaw(0,0,0,0);
  }

  wasStreaming = streaming;

  // wait until streaming
  if (!streaming) { delay(10); return; }

  // Should be streaming

  // read rtc microseconds
  uint32_t nowUs = micros();

  wifi.pollCommands(cmd);


  if (ctrlTick.due(nowUs)) {
    uint32_t dt_us = ctrlTick.advance(nowUs);
    float dt = (float)dt_us * 1e-6f;
    if (dt <= 0.f) dt = 1.0f / cfg::TILT_CONTR_HZ;

    SI si;
    imu.readSI(si);

    est.update(si, dt);
    
    if (cmd.mode == 0){
      oFL = 0; oFR=0; oBL =0; oBR = 0;
      motors.writeRaw(oFL, oFR, oBL, oBR);
      ctrl.zeroIntegrators();
    } else{

      ctrl.update(
        cmd.des_roll, cmd.des_pitch,                  
        est.roll_deg(), est.pitch_deg(),
        est.gx_dps(), est.gy_dps(),
        dt,
        cmd.base, cmd.base, cmd.base, cmd.base,
        oFL, oFR, oBL, oBR
      );
      motors.writeRaw(oFL, oFR, oBL, oBR);
    }
  }

  if (telemTick.due(nowUs)) {
    uint32_t dt_us = telemTick.advance(nowUs);
    if (dt_us > 65535u) dt_us = 65535u;
    uint16_t loop_us = (uint16_t)dt_us;
    uint8_t mot[4] = { oFL, oFR, oBL, oBR };
    uint16_t adc   = batt.readADC();
    wifi.sendFastTelemetry(loop_us, adc, mot,
                            est.roll_deg(), est.pitch_deg(),est.gx_dps(),est.gy_dps());

    DBGF(
      "loop_us=%u, adc=%u, mot=[%u,%u,%u,%u], roll=%.2f, pitch=%.2f, gx=%.2f, gy=%.2f\n",
      loop_us, adc,
      mot[0], mot[1], mot[2], mot[3],
      est.roll_deg(), est.pitch_deg(),est.gx_dps(),est.gy_dps()
      );
  }

  if(slowTelemTick.due(nowUs)){
    uint16_t dt_us = slowTelemTick.advance(nowUs);
    if (dt_us > 65535u) dt_us = 65535u;
    uint16_t loop_us = (uint16_t) dt_us;
    const float des_roll = 0.f, des_pitch = 0.f;
    wifi.sendSlowTelemetry(loop_us, ctrl.E_roll(),ctrl.E_pitch(), ctrl.U_roll(), ctrl.U_pitch());
  }
}
