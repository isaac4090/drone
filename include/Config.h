#pragma once

#define SERIAL_DEBUG 0

#if SERIAL_DEBUG
  #define DBG_BEGIN(baud)   do { Serial.begin(baud); } while(0)
  #define DBGF(...)         Serial.printf(__VA_ARGS__)
  #define DBGLN(...)        Serial.println(__VA_ARGS__)
  #define DBG(...)          Serial.print(__VA_ARGS__)
#else
  #define DBG_BEGIN(baud)   do {} while(0)
  #define DBGF(...)         do {} while(0)
  #define DBGLN(...)        do {} while(0)
  #define DBG(...)          do {} while(0)
#endif

namespace cfg {
    // Wi-Fi
    constexpr char SSID[] = "Drone";
    constexpr char PASS[] = "bob";
    constexpr uint16_t PORT = 2323;

    // ESC timing
    constexpr uint16_t PWM_MIN = 1000; // µs
    constexpr uint16_t PWM_MAX = 2000; // µs
    constexpr uint8_t  PWM_HZ  = 50;

    // Telemetry rate
    constexpr uint16_t TELEMETRY_HZ = 50; // 100 Hz => period 10 ms

    // Define pins for a motor controller
    constexpr int motorFLpin = 33; 
    constexpr int motorFRpin = 27;  
    constexpr int motorBLpin = 12;  
    constexpr int motorBRpin = 14;  

    // Battery ADC
    constexpr uint8_t  VBAT_PIN = 34;      // ADC1
    constexpr auto     VBAT_ATT = ADC_11db;

    // Gyro SPI pins
    static const int PIN_MOSI = 23;
    static const int PIN_MISO = 19;
    static const int PIN_SCK  = 18;
    static const int PIN_CS   = 5;
    constexpr float ACC_G_PER_LSB    = 1.0f / 16384.0f;
    constexpr float GYRO_DPS_PER_LSB = 1.0f / 16.4f;

    // Tilt hold rate 
    constexpr uint16_t TILT_CONTR_HZ = 500;



}