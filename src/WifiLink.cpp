#include "WifiLink.h"

// Put RTC_DATA_ATTR only on the definition (here)
RTC_DATA_ATTR bool     RTC_report_pending = false;
RTC_DATA_ATTR uint32_t RTC_boot_count     = 0;
esp_reset_reason_t     g_last_reset_reason = ESP_RST_UNKNOWN;

WifiLink::~WifiLink() {
  if (_client.connected()) _client.stop();
  if (_server) { _server->stop(); delete _server; _server = nullptr; }
}

static void wifiPrintIP() {
  Serial.print("AP IP: "); Serial.println(WiFi.softAPIP());
}

const char* WifiLink::reset_reason_str(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON:   return "POWERON";
    case ESP_RST_EXT:       return "EXT_PIN";
    case ESP_RST_SW:        return "SW_RESET";
    case ESP_RST_PANIC:     return "PANIC";
    case ESP_RST_INT_WDT:   return "INT_WDT";
    case ESP_RST_TASK_WDT:  return "TASK_WDT";
    case ESP_RST_WDT:       return "WDT";
    case ESP_RST_DEEPSLEEP: return "DEEPSLEEP";
    case ESP_RST_BROWNOUT:  return "BROWNOUT";
    case ESP_RST_SDIO:      return "SDIO";
    default:                return "UNKNOWN";
  }
}

void WifiLink::begin(uint16_t port, const char* ssid, const char* pass) {
  g_last_reset_reason = esp_reset_reason();
  RTC_boot_count++;
  RTC_report_pending = true;

  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, pass);
  wifiPrintIP();

  _server = new WiFiServer(port);
  _server->begin();

  _state = WAIT_CLIENT;
  _bannerSentThisConn = false;
}

void WifiLink::acceptClientIfAny() {
  if (_state != WAIT_CLIENT) return;
  WiFiClient c = _server->available();
  if (c) {
    if (_client.connected()) _client.stop();  // drop stale
    _client = c;
    _client.setNoDelay(true);
    _client.setTimeout(20);                   // small timeout for readStringUntil
    _state = WAIT_HANDSHAKE;
#ifdef SERIAL_DEBUG
    Serial.println("[NET] Client connected, waiting HELLO");
#endif
  }
}

void WifiLink::doHandshake() {
  if (_state != WAIT_HANDSHAKE) return;
  if (!_client.connected()) { closeClient(); return; }

  if (_client.available()) {
    String line = _client.readStringUntil('\n');  // waits up to setTimeout()
    line.trim();
#ifdef SERIAL_DEBUG
    Serial.printf("[NET] Handshake line: '%s'\n", line.c_str());
#endif
    if (line == "HELLO") {
      sendBannerIfNeeded();
      _state = STREAMING;
#ifdef SERIAL_DEBUG
      Serial.println("[NET] Handshake OK -> STREAMING");
#endif
    } else if (line == "BYE") {
#ifdef SERIAL_DEBUG
      Serial.println("[NET] BYE -> closing");
#endif
      closeClient();
    } else {
      // ignore unknown lines during handshake
    }
  }
}

void WifiLink::sendBannerIfNeeded() {
  if (!_client.connected()) return;
  if (RTC_report_pending) {
    _client.printf("RST:%s,BOOT:%lu,PEND:1\n",
                   reset_reason_str(g_last_reset_reason),
                   (unsigned long)RTC_boot_count);
    _client.flush();
    RTC_report_pending = false;  // once per boot
  } else {
    _client.print("RST:OK,BOOT:NA,PEND:0\n");
    _client.flush();
  }
  _bannerSentThisConn = true;
}

void WifiLink::handle() {
  if (_state == WAIT_CLIENT) { acceptClientIfAny(); return; }
  if (!_client.connected())  { closeClient(); return; }
  if (_state == WAIT_HANDSHAKE) { doHandshake(); return; }
  // STREAMING: user code will call readCmd4()/writeTelemetry()
}

bool WifiLink::readCmd4(uint8_t out[4]) {
  if (_state != STREAMING || !_client.connected()) return false;
  if (_client.available() < 4) return false;
  size_t got = _client.read(out, 4);
  return got == 4;
}

size_t WifiLink::writeTelemetry(const uint8_t* buf, size_t len) {
  if (_state != STREAMING || !_client.connected()) return 0;
  return _client.write(buf, len);
}

void WifiLink::closeClient() {
  if (_client.connected()) _client.stop();
  _state = WAIT_CLIENT;
  _bannerSentThisConn = false;
}


size_t WifiLink::sendFastTelemetry(uint16_t loop_us,
                                     uint16_t bat_adc,
                                     const uint8_t mot[4],
                                     float roll_deg, float pitch_deg,
                                     float gx_dps,  float gy_dps)
{
  if (_state != STREAMING || !_client.connected()) return 0;

  auto q = [](float v, float s)->int16_t {
    float f = v * s;
    if (f >  32767.f) f =  32767.f;
    if (f < -32768.f) f = -32768.f;
    return (int16_t)f;
  };

  AnglesPkt p{};
  p.type        = PKT_ANGLES;
  p.seq_be      = htobe16_u16(_txSeq++);
  p.loop_us_be  = htobe16_u16(loop_us);
  p.bat_adc_be  = htobe16_u16(bat_adc);
  p.mot[0]=mot[0]; p.mot[1]=mot[1]; p.mot[2]=mot[2]; p.mot[3]=mot[3];

  p.roll_c_be  = (int16_t)htobe16_u16((uint16_t)q(roll_deg,  100.f));
  p.pitch_c_be = (int16_t)htobe16_u16((uint16_t)q(pitch_deg, 100.f));
  p.gx_c_be    = (int16_t)htobe16_u16((uint16_t)q(gx_dps,    100.f));
  p.gy_c_be    = (int16_t)htobe16_u16((uint16_t)q(gy_dps,    100.f));

  p.csum = xor8_sum(reinterpret_cast<const uint8_t*>(&p), sizeof(p) - 1);
  return writeTelemetry(reinterpret_cast<const uint8_t*>(&p), sizeof(p));
}