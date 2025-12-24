#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <esp_wifi.h>
#include "secrets.h"

// ==========================================
// Configuration
// ==========================================
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;
uint8_t newMACAddress[] = {0x7C, 0xE1, 0x52, 0x07, 0x0D, 0x66}; // Custom MAC Address (Locally Administered)

// Static IP Configuration
IPAddress local_IP(192, 168, 1, 54);  // Desired Fixed IP
IPAddress gateway(192, 168, 1, 1);    // Router IP
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);

// UART Configuration
// On ESP32-CAM, Serial (UART0) is on GPIO 1 (TX) and GPIO 3 (RX).
// This is shared with the USB-TTL adapter during programming.
HardwareSerial& BridgeSerial = Serial; 
bool isSerialStarted = false;

WebServer server(80);

// ==========================================
// Helper Functions
// ==========================================

void clearSerialBuffers() {
    if (!isSerialStarted) return;
    // Clear RX buffer
    while (BridgeSerial.available()) {
        BridgeSerial.read();
    }
    // Flush TX buffer (waits for transmission to complete)
    BridgeSerial.flush();
}

void sendCorsHeaders() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
    server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

// ==========================================
// API Handlers
// ==========================================

// Endpoint: /start
// Method: POST
// Params: baud (optional, default 9600)
// Description: Starts the UART connection and clears buffers.
void handleStart() {
    sendCorsHeaders();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    String baudStr = server.arg("baud");
    unsigned long baud = baudStr.toInt();
    if (baud == 0) baud = 9600;

    if (isSerialStarted) {
        BridgeSerial.end();
    }

    BridgeSerial.begin(baud);
    isSerialStarted = true;
    
    // Give it a moment to settle
    delay(100);
    clearSerialBuffers();

    server.send(200, "text/plain", "UART Started at " + String(baud));
}

// Endpoint: /end
// Method: POST
// Description: Ends the UART connection and clears buffers.
void handleEnd() {
    sendCorsHeaders();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    if (isSerialStarted) {
        clearSerialBuffers();
        BridgeSerial.end();
        isSerialStarted = false;
        server.send(200, "text/plain", "UART Ended");
    } else {
        server.send(200, "text/plain", "UART was not running");
    }
}

// Endpoint: /send_sync
// Method: POST
// Body: Data to send
// Params: timeout (optional, default 1000ms)
// Description: Sends data over serial and waits for a response.
void handleSendSync() {
    sendCorsHeaders();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    if (!isSerialStarted) {
        server.send(400, "text/plain", "Error: UART not started");
        return;
    }

    if (!server.hasArg("plain")) {
        server.send(400, "text/plain", "Error: No body received");
        return;
    }

    String dataToSend = server.arg("plain");
    String timeoutStr = server.arg("timeout");
    unsigned long timeout = timeoutStr.toInt();
    if (timeout == 0) timeout = 1000;

    // Clear any previous garbage before sending
    while (BridgeSerial.available()) BridgeSerial.read();

    BridgeSerial.print(dataToSend);

    // Wait for response
    String response = "";
    unsigned long startTime = millis();
    bool receivedData = false;

    while (millis() - startTime < timeout) {
        if (BridgeSerial.available()) {
            char c = BridgeSerial.read();
            response += c;
            receivedData = true;
            // Reset timeout on new data? 
            // For now, strict total timeout to avoid hanging forever if stream is continuous
        } else if (receivedData) {
            // If we have received data but buffer is now empty, wait a tiny bit to see if more comes
            // This is a simple heuristic for "end of message"
            delay(10);
            if (!BridgeSerial.available()) break;
        } else {
            delay(1);
        }
    }

    server.send(200, "text/plain", response);
}

// Endpoint: /send_async
// Method: POST
// Body: Data to send
// Description: Sends data over serial and returns immediately.
void handleSendAsync() {
    sendCorsHeaders();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    if (!isSerialStarted) {
        server.send(400, "text/plain", "Error: UART not started");
        return;
    }

    if (!server.hasArg("plain")) {
        server.send(400, "text/plain", "Error: No body received");
        return;
    }

    String dataToSend = server.arg("plain");
    BridgeSerial.print(dataToSend);

    server.send(200, "text/plain", "Data sent");
}

// Endpoint: /gpio
// Method: POST
// Params: pin, state (0 or 1)
// Description: Sets a GPIO pin to a specific state.
void handleGpio() {
    sendCorsHeaders();
    if (server.method() == HTTP_OPTIONS) { server.send(200); return; }

    if (!server.hasArg("pin") || !server.hasArg("state")) {
        server.send(400, "text/plain", "Error: Missing 'pin' or 'state' parameter");
        return;
    }

    int pin = server.arg("pin").toInt();
    int state = server.arg("state").toInt();

    // Basic safety check for ESP32-CAM (avoid resetting if possible, but user asked for arbitrary)
    // GPIO 1 & 3 are Serial. GPIO 0 is boot. GPIO 16 is PSRAM CS (careful!).
    
    pinMode(pin, OUTPUT);
    digitalWrite(pin, state ? HIGH : LOW);

    server.send(200, "text/plain", "GPIO " + String(pin) + " set to " + String(state));
}

void handleNotFound() {
    if (server.method() == HTTP_OPTIONS) {
        sendCorsHeaders();
        server.send(200);
    } else {
        server.send(404, "text/plain", "Not found");
    }
}

// ==========================================
// Main Setup & Loop
// ==========================================

void setup() {
    // Initialize Serial for debugging initially? 
    // Since we use Serial for the bridge, we might want to avoid noise.
    // But usually setup logs are helpful. We'll start it, print info, then end it if not requested.
    // However, the user wants explicit control via /start.
    // We will NOT start Serial here to keep the line quiet until requested.
    
    // Config WiFi
    if (!WiFi.config(local_IP, gateway, subnet, primaryDNS)) {
        // Serial.println("STA Failed to configure");
    }

    WiFi.mode(WIFI_STA);
    esp_wifi_set_mac(WIFI_IF_STA, &newMACAddress[0]);

    WiFi.begin(ssid, password);

    // Wait for connection (without Serial debug, we just wait)
    // Blink the flashlight LED (GPIO 4) until connected
    pinMode(4, OUTPUT); 
    digitalWrite(4, LOW); // Off

    while (WiFi.status() != WL_CONNECTED) {
        delay(50);
        digitalWrite(4, false); // Blink
        delay(500);
        digitalWrite(4, true); // Blink
    }
    digitalWrite(4, LOW); // Off

    // Setup Routes
    server.on("/start", HTTP_POST, handleStart);
    server.on("/end", HTTP_POST, handleEnd);
    server.on("/send_sync", HTTP_POST, handleSendSync);
    server.on("/send_async", HTTP_POST, handleSendAsync);
    server.on("/gpio", HTTP_POST, handleGpio);
    server.onNotFound(handleNotFound);

    server.begin();
}

void loop() {
    server.handleClient();
}
