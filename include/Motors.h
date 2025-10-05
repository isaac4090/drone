#pragma once
#include <ESP32Servo.h>
#include "Config.h"

class Motors {
public:
  void begin() {
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    fl.setPeriodHertz(cfg::PWM_HZ);
    fr.setPeriodHertz(cfg::PWM_HZ);
    bl.setPeriodHertz(cfg::PWM_HZ);
    br.setPeriodHertz(cfg::PWM_HZ);

    fl.attach(cfg::motorFLpin, cfg::PWM_MIN, cfg::PWM_MAX);
    fr.attach(cfg::motorFRpin, cfg::PWM_MIN, cfg::PWM_MAX);
    bl.attach(cfg::motorBLpin, cfg::PWM_MIN, cfg::PWM_MAX);
    br.attach(cfg::motorBRpin, cfg::PWM_MIN, cfg::PWM_MAX);

    safeStop();
  }

  inline void safeStop() {
    fl.write(0); fr.write(0); bl.write(0); br.write(0); 
  }

  inline void writeRaw(uint8_t fl_, uint8_t fr_, uint8_t bl_, uint8_t br_) {
    fl.write(fl_); fr.write(fr_); bl.write(bl_); br.write(br_);
  }

private:
  Servo fl, fr, bl, br;
};