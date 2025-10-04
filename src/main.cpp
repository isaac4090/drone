#include <Arduino.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include "Pin_Defs.h"
#include <SPI.h>

namespace prints{
  bool printSerial = true;
  bool printWiFi = true;
}

// const char* SSID = "Drone";
// const char* PASS = "bob";
// const uint16_t port = 2323;

enum class mode: uint8_t {connect, startMotors,stopMotors ,fly};

WiFiServer server(port);
WiFiClient client;

struct Packet {uint8_t us[4];};

struct MotorPowers {uint8_t m[4];}; //FL,FR,BL,BR

uint8_t mFL=0, mFR=0, mBL=0, mBR=0; //latest motors
Servo motorFL, motorFR, motorBL, motorBR;
uint32_t lastTxMs = 0;

void setup_motors(){

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  // Attach the servos to different pins with respective timers
  motorFL.attach(motorFLpin, 1000, 2000); // Using GPIO 19 for Front Left
  motorFR.attach(motorFRpin, 1000, 2000); // Using GPIO 22 for Front Right
  motorBL.attach(motorBLpin, 1000, 2000); // Using GPIO 18 for Back Left
  motorBR.attach(motorBRpin, 1000, 2000); // Using GPIO 21 for Back Right

  motorFR.setPeriodHertz(50);
  motorFL.setPeriodHertz(50);
  motorBL.setPeriodHertz(50);
  motorBR.setPeriodHertz(50);
}

///////////////////////////

SPIClass *vspi = nullptr;

// Simple SPI helpers (MPU-9250 uses R/W bit in MSB)
uint8_t mpuRead8(uint8_t reg) {
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(reg | 0x80);
  uint8_t v = SPI.transfer(0x00);
  digitalWrite(PIN_CS, HIGH);
  return v;
}

void mpuReadN(uint8_t reg, uint8_t *buf, size_t n) {
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(reg | 0x80);
  for (size_t i = 0; i < n; ++i) buf[i] = SPI.transfer(0x00);
  digitalWrite(PIN_CS, HIGH);
}

void mpuWrite8(uint8_t reg, uint8_t val) {
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(reg & 0x7F);
  SPI.transfer(val);
  digitalWrite(PIN_CS, HIGH);
}

static inline int16_t be16(const uint8_t *p) { return (int16_t)((p[0] << 8) | p[1]); }

void setup_gyro(){
  // SPI @ 1MHz, mode 3 (works reliably for InvenSense parts)
  pinMode(PIN_CS, OUTPUT);
  digitalWrite(PIN_CS, HIGH);

  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI);
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE3));

  // Reset, then wake and basic config
  mpuWrite8(REG_PWR_MGMT_1, 0x80); // reset
  delay(100);
  mpuWrite8(REG_PWR_MGMT_1, 0x01); // clock = PLL
  mpuWrite8(REG_PWR_MGMT_2, 0x00); // enable accel+gyro
  mpuWrite8(REG_CONFIG,        0x03); // DLPF ~44Hz for gyro
  mpuWrite8(REG_SMPLRT_DIV,    0x04); // sample ~200Hz (if base 1kHz)
  mpuWrite8(REG_GYRO_CONFIG,   0x18); // FS = ±2000 dps
  mpuWrite8(REG_ACCEL_CONFIG,  0x00); // FS = ±2g
  mpuWrite8(REG_ACCEL_CONFIG2, 0x03); // accel DLPF

  // Verify WHO_AM_I
  uint8_t who = mpuRead8(REG_WHO_AM_I);
  Serial.printf("WHO_AM_I = 0x%02X (expect 0x71 or 0x73)\n", who);
  if (who != 0x71 && who != 0x73) {
    Serial.println("!! Unexpected WHO_AM_I. Check wiring/CS pin/board supports SPI.");
  }
}


///////////////////////

void setup() {
  // put your setup code here, to run once:
  if (prints::printSerial) Serial.begin(115200);
  setup_motors();
  WiFi.mode(WIFI_AP);
  WiFi.softAP(SSID, PASS);
  if (prints::printSerial) Serial.print("AP IP: "); Serial.println(WiFi.softAPIP()); // usually 192.168.4.1
  server.begin();

  /////////////////////////
  setup_gyro();

  //// Battery setup
  analogReadResolution(12);
  analogSetPinAttenuation(34, ADC_11db);
  

}

void loop() {
  if (!client || !client.connected()) {
    client = server.available();
    return;
  }

  // Wait until we have at least 4 bytes, then read exactly 4

  if (client.available() >= (int)sizeof(Packet)) {
    Packet p;
    size_t got = client.read((uint8_t*)&p, sizeof(p));  // read 8 bytes
    if (got == sizeof(p)){
      mFL = p.us[0]; mFR = p.us[1]; mBL = p.us[2]; mBR = p.us[3];
      if (prints::printSerial) Serial.printf("FL: %u, FR: %u, BL: %u, BR %u \n", mFL, mFR, mBL, mBR);
      motorFL.write(mFL);
      motorFR.write(mFR);
      motorBL.write(mBL);
      motorBR.write(mBR);
    }
  }
  
  uint32_t now = millis();
  if (now - lastTxMs >= 10) {           // 10 ms = 100 Hz
    lastTxMs = now;

    // read 14 bytes starting at ACCEL_XOUT_H (ax,ay,az,temp,gx,gy,gz)
    uint8_t raw14[14];
    mpuReadN(REG_ACCEL_XOUT_H, raw14, sizeof(raw14));

    // read battery
    uint16_t bat = analogRead(34);
    // build 18-byte frame: 4 motors + 14 IMU bytes
    uint8_t frame[20];
    frame[0] = (bat >> 8) & 0xFF;
    frame[1] = bat & 0xFF;
    frame[2]=mFL; frame[3]=mFR; frame[4]=mBL; frame[5]=mBR;
    memcpy(frame+6, raw14, 14);

    client.write(frame, sizeof(frame)); // one complete frame
    // client.flush(); // optional
  }
}
