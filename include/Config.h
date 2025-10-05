#pragma once
#include <Arduino.h>

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
    constexpr uint8_t  VBAT_PIN = 34;      // ADC1, OK with Wi-Fi
    constexpr auto     VBAT_ATT = ADC_11db; // or ADC_0db if your pin ~0.3–0.4 V

    // Gyro SPI pins
    static const int PIN_MOSI = 23;
    static const int PIN_MISO = 19;
    static const int PIN_SCK  = 18;
    static const int PIN_CS   = 5;
}