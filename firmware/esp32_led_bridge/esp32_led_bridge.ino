#include <WiFi.h>
#include <WebServer.h>

#include "secrets.h"

// Most ESP32 DevKit boards use GPIO 2 for the onboard LED.
const int LED_PIN = 2;

// Set to false if your board's LED turns on when the pin is LOW.
const bool LED_ACTIVE_HIGH = true;

WebServer server(80);
bool ledOn = false;

void writeLed(bool on) {
  ledOn = on;
  int activeValue = LED_ACTIVE_HIGH ? HIGH : LOW;
  int inactiveValue = LED_ACTIVE_HIGH ? LOW : HIGH;
  digitalWrite(LED_PIN, on ? activeValue : inactiveValue);
}

String jsonStatus() {
  String json = "{";
  json += "\"state\":\"";
  json += ledOn ? "on" : "off";
  json += "\",\"led\":";
  json += ledOn ? "true" : "false";
  json += ",\"pin\":";
  json += LED_PIN;
  json += ",\"activeLevel\":\"";
  json += LED_ACTIVE_HIGH ? "HIGH" : "LOW";
  json += "\",\"ip\":\"";
  json += WiFi.localIP().toString();
  json += "\"}";
  return json;
}

void sendStatus() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", jsonStatus());
}

void handleLedOn() {
  writeLed(true);
  sendStatus();
}

void handleLedOff() {
  writeLed(false);
  sendStatus();
}

void handleLedToggle() {
  writeLed(!ledOn);
  sendStatus();
}

void handleRoot() {
  server.send(
    200,
    "text/plain",
    "ESP32 LED MCP bridge\n\nEndpoints:\n/led/on\n/led/off\n/led/toggle\n/led/status\n"
  );
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_PIN, OUTPUT);
  writeLed(false);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connected. ESP32 IP address: ");
  Serial.println(WiFi.localIP());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/led/on", HTTP_GET, handleLedOn);
  server.on("/led/off", HTTP_GET, handleLedOff);
  server.on("/led/toggle", HTTP_GET, handleLedToggle);
  server.on("/led/status", HTTP_GET, sendStatus);
  server.onNotFound([]() {
    server.send(404, "application/json", "{\"error\":\"not found\"}");
  });

  server.begin();
  Serial.println("HTTP LED server started.");
}

void loop() {
  server.handleClient();
}
