#include <Arduino.h>
#include <WiFi.h>
// put function declarations here:

const char* SSID = "Drone";
const char* PASS = "bob";
const uint16_t port = 2323;

WiFiServer server(port);
WiFiClient client;

struct Packet {uint8_t us[4];};



void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(SSID, PASS);
  Serial.print("AP IP: "); Serial.println(WiFi.softAPIP()); // usually 192.168.4.1
  server.begin();
}

void loop() {
  if (!client || !client.connected()) {
    client = server.available();
    return;
  }

  // Wait until we have at least 8 bytes, then read exactly 4
  if (client.available() >= (int)sizeof(Packet)) {
    Packet p;
    client.read((uint8_t*)&p, sizeof(p));  // read 8 bytes
    Serial.printf("pkt: [%u %u %u %u]\n", p.us[0], p.us[1], p.us[2], p.us[3]);
    client.write((const uint8_t*)&p, sizeof(p)); // echo back
  }
}
