#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <esp_system.h>

class WifiLink {
public:
  enum State { WAIT_CLIENT, WAIT_HANDSHAKE, STREAMING };

  WifiLink() = default;
  ~WifiLink();

  void begin(uint16_t port, const char* ssid, const char* pass);
  void handle();

  // Read one 4-byte command (FL, FR, BL, BR). Returns true if read.
  bool readCmd4(uint8_t out[4]);

  // Write telemetry buffer (e.g., 20 bytes). Returns bytes written.
  size_t writeTelemetry(const uint8_t* buf, size_t len);

  // NOTE: these are NON-const because WiFiClient APIs are non-const.
  inline bool connected() { return _client.connected(); }
  inline bool inStreaming() { return _state == STREAMING && _client.connected(); }
  inline State state() const { return _state; }

  void closeClient();

private:
  WiFiServer* _server = nullptr;
  WiFiClient  _client;
  State _state = WAIT_CLIENT;
  bool  _bannerSentThisConn = false;

  static const char* reset_reason_str(esp_reset_reason_t r);
  void sendBannerIfNeeded();
  void acceptClientIfAny();
  void doHandshake();
};

// RTC variables are defined in the .cpp (no RTC_DATA_ATTR here)
extern bool     RTC_report_pending;
extern uint32_t RTC_boot_count;
extern esp_reset_reason_t g_last_reset_reason;
