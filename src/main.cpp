#include <Arduino.h>
#include <WiFi.h>
#include "Config.h"
#include "Packets.h"
#include "Motors.h"
#include "IMU.h"
#include "Battery.h"

namespace prints{
  bool printSerial = true;
  bool printWiFi = true;
}

WiFiServer server(cfg::PORT);
WiFiClient client;

Motors motors;
IMU imu;
Battery batt;

uint8_t mFL = 0, mFR = 0, mBL = 0, mBR = 0;
uint32_t lastTxMs = 0;



void setup() {
  // put your setup code here, to run once:
  if (prints::printSerial) Serial.begin(115200);
  motors.begin();
  WiFi.mode(WIFI_AP);
  WiFi.softAP(cfg::SSID, cfg::PASS);
  if (prints::printSerial) Serial.print("AP IP: "); Serial.println(WiFi.softAPIP()); // usually 192.168.4.1
  server.begin();

  imu.begin(cfg::PIN_CS, cfg::PIN_SCK, cfg::PIN_MISO, cfg::PIN_MOSI);
  if (prints::printSerial) {
    Serial.printf("WHO_AM_I = 0x%02X\n", imu.whoAmI());
  }

  batt.begin();
}

void loop() {
  if (!client || !client.connected()) {
    client = server.available();
    if (!client){
      motors.safeStop();
      return;
    }
    client.setNoDelay(true);
  }

  // Wait until we have at least 4 bytes, then read exactly 4

  if (client.available() >= (int)sizeof(pkt::Cmd)) {
    pkt::Cmd p;
    size_t got = client.read((uint8_t*)&p, sizeof(p));  // read 8 bytes
    if (got == sizeof(p)){
      mFL = p.us[0]; mFR = p.us[1]; mBL = p.us[2]; mBR = p.us[3];
      if (prints::printSerial) Serial.printf("FL: %u, FR: %u, BL: %u, BR %u \n", mFL, mFR, mBL, mBR);
      motors.writeRaw(mFL, mFR, mBL, mBR);
    }
  }
  
  const uint32_t periodMs = 1000u / cfg::TELEMETRY_HZ;
  uint32_t now = millis();
   if (now - lastTxMs >= periodMs) {
    lastTxMs = now;

    // IMU block
    uint8_t raw14[pkt::IMU_RAW_LEN];
    imu.readRaw14(raw14);

    // Battery raw ADC code (0..4095) to keep your current PC parser
    uint16_t adc = batt.readADC();

    // Frame: [bat_hi,bat_lo, mFL,mFR,mBL,mBR, imu14...]
    uint8_t frame[pkt::FRAME_LEN];
    frame[0] = (uint8_t)(adc >> 8);
    frame[1] = (uint8_t)(adc & 0xFF);
    frame[2] = mFL; frame[3] = mFR; frame[4] = mBL; frame[5] = mBR;
    memcpy(frame + 6, raw14, pkt::IMU_RAW_LEN);

    client.write(frame, sizeof(frame));
  }
}
