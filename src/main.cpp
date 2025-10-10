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

// --- Tilt-hold state & tuning ---
static float g_roll_deg = 0.0f, g_pitch_deg = 0.0f;   // complementary-filter angles
static float gi_roll = 0.0f, gi_pitch = 0.0f;         // integrators



// Motor limits for your writeRaw() (uint8_t -> 0..255)
static constexpr float M_MIN = 0.0f;
static constexpr float M_MAX = 255.0f;


/////////////////

// Loop timers helpers
static uint32_t lastCtrlUs = 0;
static uint32_t nextCtrlDueUs = 0;

static uint32_t lastTxUs = 0;
static uint32_t nextTxDueUs = 0;

uint8_t mFL = 0, mFR = 0, mBL = 0, mBR = 0;
uint8_t oFL = 0, oFR = 0, oBL = 0, oBR = 0;
uint32_t lastTxMs = 0;


struct Periodic {
  uint32_t next_us=0, period_us=0;
  void start(uint32_t now, uint32_t period){ next_us=now+period; period_us=period; }
  bool due(uint32_t now) const { return (int32_t)(now - next_us) >= 0; }
  void advance(uint32_t now){ do { next_us += period_us; } while ((int32_t)(now - next_us) >= 0); }
};

// Start small; increase Kp until it resists tilt crisply, then add a bit of Ki to kill residual bias.
static float Kp_roll  = 0.12f, Ki_roll  = 0.02f, Kd_roll  = 0.0015f;
static float Kp_pitch = 0.12f, Ki_pitch = 0.02f, Kd_pitch = 0.0015f;


IMU imu;
AttitudeEstimator est(0.98f);
TiltController ctrl({Kp_roll, Ki_roll,Kd_roll},{Kp_pitch,Ki_pitch,Kd_pitch});
Motors motors;
Battery batt;
WifiLink wifi;

Periodic ctrlTick, telemTick;



void setup() {
  motors.begin();
  wifi.begin(cfg::PORT, cfg::SSID, cfg::PASS);
  imu.begin(cfg::PIN_CS, cfg::PIN_SCK, cfg::PIN_MISO, cfg::PIN_MOSI);
  batt.begin();

  DBG_BEGIN(baud);
  DBG("AP IP: "); DBGLN(WiFi.softAPIP());
  DBGF("WHO_AM_I = 0x%02X\n", imu.whoAmI());

  uint32_t t0 = micros();
  ctrlTick.start(t0, 1000000u / cfg::TILT_CONTR_HZ);
  telemTick.start(t0,1000000u / cfg::TELEMETRY_HZ );
}



void loop() {
  wifi.handle();

  // wait until streaming
  if (!wifi.inStreaming()) { delay(10); return;}

  // read rtc microseconds
  uint32_t nowUs = micros();

  // read motor commands
  uint8_t cmd[4];
  while (wifi.readCmd4(cmd)) {
    mFL = cmd[0]; mFR = cmd[1]; mBL = cmd[2]; mBR = cmd[3];
  }

  if (ctrlTick.due(nowUs)) {
    ctrlTick.advance(nowUs);

    SI si;
    imu.readSI(si);

    static bool first = true;
    static uint32_t last = 0;
    float dt;

    if (first) {
      // initialize on first run
      last = nowUs;
      dt = 1.0f / cfg::TILT_CONTR_HZ;
      first = false;
    } else {
      dt = (nowUs - last) * 1e-6f;
      if (dt <= 0) dt = 1.0f / cfg::TILT_CONTR_HZ;  // wrap safety
      last = nowUs;
    }

    est.update(si, dt);

    ctrl.update(
      0.0f, 0.0f,                  
      est.roll_deg(), est.pitch_deg(),
      est.gx_dps(), est.gy_dps(),
      dt,
      mFL, mFR, mBL, mBR,
      oFL, oFR, oBL, oBR
    );
    motors.writeRaw(oFL, oFR, oBL, oBR);
  }
  if (telemTick.due(nowUs)) {
    // uint16_t dt32 = nowUs - lastTxUs;
    // if (dt32 > 65535u) dt32 = 65535u;
    // uint16_t loop_us = (uint16_t) dt32;

    // lastTxUs = nowUs;

    // while ((int32_t)(nowUs - nextTxDueUs) >= 0){
    //   nextTxDueUs += txPeriodUs;
    // }

    telemTick.advance(nowUs);

    uint8_t mot[4] = { oFL, oFR, oBL, oBR };
    uint16_t adc   = batt.readADC();
    uint16_t loop_us = (uint16_t)min<uint32_t>(telemTick.period_us, 65535u);
    wifi.sendFastTelemetry(loop_us, adc, mot,
                            est.roll_deg(), est.pitch_deg(),est.gx_dps(),est.gy_dps());

    DBGF(
      "loop_us=%u, adc=%u, mot=[%u,%u,%u,%u], roll=%.2f, pitch=%.2f, gx=%.2f, gy=%.2f\n",
      loop_us, adc,
      mot[0], mot[1], mot[2], mot[3],
      roll_deg, pitch_deg, gx_dps, gy_dps
      );
  }
}
