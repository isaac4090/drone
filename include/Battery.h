#pragma once
#include <Arduino.h>
#include "Config.h"

class Battery {
public:
  void begin() {
    analogReadResolution(12);
    analogSetPinAttenuation(cfg::VBAT_PIN, cfg::VBAT_ATT);
  }
  // Raw ADC code (0..4095). Keep this to preserve your existing 20-byte format.
  uint16_t readADC() {
    return (uint16_t) analogRead(34);
  }
};