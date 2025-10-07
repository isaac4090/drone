#include <Arduino.h>
#include <WiFi.h>
#include "Config.h"
#include "Packets.h"
#include "Motors.h"
#include "IMU.h"
#include "Battery.h"
#include <esp_system.h> 
#include "WifiLink.h"




Motors motors;
IMU imu;
Battery batt;
WifiLink wifi;

uint8_t mFL = 0, mFR = 0, mBL = 0, mBR = 0;
uint32_t lastTxMs = 0;

void setup() {
  motors.begin();
  wifi.begin(cfg::PORT, cfg::SSID, cfg::PASS);
  imu.begin(cfg::PIN_CS, cfg::PIN_SCK, cfg::PIN_MISO, cfg::PIN_MOSI);
  batt.begin();

  #ifdef SERIAL_DEBUG
    Serial.begin(115200);
    Serial.print("AP IP: "); Serial.println(WiFi.softAPIP());
    Serial.printf("WHO_AM_I = 0x%02X\n", imu.whoAmI());
  #endif
}

void loop() {
  wifi.handle();

  if (wifi.inStreaming()) {
    // (A) commands
    uint8_t cmd[4];
    while (wifi.readCmd4(cmd)) {
      mFL = cmd[0]; mFR = cmd[1]; mBL = cmd[2]; mBR = cmd[3];
      motors.writeRaw(mFL, mFR, mBL, mBR);
    }
    // (B) telemetry at fixed rate
    static uint32_t lastTxMs = 0;
    const uint32_t periodMs = 1000u / cfg::TELEMETRY_HZ;
    uint32_t now = millis();
    if (now - lastTxMs >= periodMs) {
      lastTxMs = now;

      uint8_t raw14[pkt::IMU_RAW_LEN];
      imu.readRaw14(raw14);
      uint16_t adc = batt.readADC();

      uint8_t frame[pkt::FRAME_LEN];
      frame[0] = (uint8_t)(adc >> 8);
      frame[1] = (uint8_t)(adc & 0xFF);
      frame[2] = mFL; frame[3] = mFR; frame[4] = mBL; frame[5] = mBR;
      memcpy(frame + 6, raw14, pkt::IMU_RAW_LEN);

      wifi.writeTelemetry(frame, sizeof(frame));
    }
  }
}
