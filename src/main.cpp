#include <Arduino.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include "Pin_Defs.h"
// put function declarations here:

namespace prints{
  bool printSerial = true;
  bool printWiFi = true;
}

const char* SSID = "Drone";
const char* PASS = "bob";
const uint16_t port = 2323;

WiFiServer server(port);
WiFiClient client;

struct Packet {uint8_t us[4];};
struct MotorPowers {uint8_t m[4];}; //FL,FR,BL,BR
Servo motorFL, motorFR, motorBL, motorBR;

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


void setup() {
  // put your setup code here, to run once:
  if (prints::printSerial) Serial.begin(115200);
  setup_motors();
  WiFi.mode(WIFI_AP);
  WiFi.softAP(SSID, PASS);
  if (prints::printSerial) Serial.print("AP IP: "); Serial.println(WiFi.softAPIP()); // usually 192.168.4.1
  server.begin();
}

void loop() {
  if (!client || !client.connected()) {
    client = server.available();
    return;
  }

  // Wait until we have at least 4 bytes, then read exactly 4
  if (client.available() >= (int)sizeof(Packet)) {
    Packet p;
    client.read((uint8_t*)&p, sizeof(p));  // read 8 bytes
    if (prints::printSerial) Serial.printf("pkt: [%u %u %u %u]\n", p.us[0], p.us[1], p.us[2], p.us[3]);
    client.write((const uint8_t*)&p, sizeof(p)); // echo back
    if (prints::printSerial){
      Serial.print("    FL power: ");
      Serial.print(p.us[0]);
      Serial.print("    FR power:  ");
      Serial.print(p.us[1]);
      Serial.print("    BL power:  ");
      Serial.print(p.us[2]);
      Serial.print("     FR power :  ");
      Serial.println(p.us[3]);
    }
    motorBL.write(p.us[0]);
    motorFL.write(p.us[1]);
    motorBR.write(p.us[2]);
    motorFR.write(p.us[3]);
  }
  
  
}
