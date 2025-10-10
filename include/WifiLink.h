#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <esp_system.h>

static constexpr uint8_t PKT_FAST = 0xA1;
static constexpr uint8_t PKT_ANGLES = 0xA2;


static inline uint16_t htobe16_u16(uint16_t v) {
  // swap little ended to big ended
  return (uint16_t)((v << 8) | (v >> 8));   
}


static inline uint8_t xor8_sum (const uint8_t* p, size_t n){
  uint8_t x = 0;
  for (size_t i =0; i < n; i++){
    x ^= p[i];
  }
  return x;
}

struct __attribute__((packed)) FastPkt {
  uint8_t  type;
  uint16_t seq_be;
  uint16_t loop_us_be;
  uint16_t bat_adc_be;
  uint8_t  mot[4];     // FL,FR,BL,BR
  int16_t  ax_be, ay_be, az_be;
  int16_t  gx_be, gy_be, gz_be;
  uint8_t  csum;
};

struct __attribute__((packed)) AnglesPkt {
  uint8_t  type;
  uint16_t seq_be;
  uint16_t loop_us_be;
  uint16_t bat_adc_be;
  uint8_t  mot[4];
  int16_t  roll_c_be;   // deg * 100
  int16_t  pitch_c_be;  // deg * 100
  int16_t  gx_c_be;     // dps * 100
  int16_t  gy_c_be;     // dps * 100
  uint8_t  csum;
};

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

  // Build and send a 0xA1 fast telemetry frame
  size_t sendFastTelemetry(uint16_t loop_us,
                                     uint16_t bat_adc,
                                     const uint8_t mot[4],
                                     float roll_deg, float pitch_deg,
                                     float gx_dps,  float gy_dps);

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
  uint16_t _txSeq = 0;     // running telemetry sequence

  static const char* reset_reason_str(esp_reset_reason_t r);
  void sendBannerIfNeeded();
  void acceptClientIfAny();
  void doHandshake();
};

// RTC variables are defined in the .cpp (no RTC_DATA_ATTR here)
extern bool     RTC_report_pending;
extern uint32_t RTC_boot_count;
extern esp_reset_reason_t g_last_reset_reason;
