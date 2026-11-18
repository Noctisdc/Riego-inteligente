#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "DHT.h"

const char* WIFI_SSID = "Wokwi-GUEST";
const char* BROKER = "broker.hivemq.com";
const char* TOPIC_DATOS = "camilo/riego/datos";
const char* TOPIC_COMANDO = "camilo/riego/comando";

const int PIN_DHT = 15;
const int PIN_SUELO = 34;
const int PIN_TRIG = 5;
const int PIN_ECHO = 18;
const int PIN_BOTON = 13;
const int PIN_BUZZER = 27;
const int PIN_LED_BOMBA = 2;
const int PIN_LED_ALERTA = 4;
const int PIN_RELE = 26;

const int TANQUE_MINIMO = 10;
const unsigned long DURACION_RIEGO = 3000;

WiFiClient espClient;
PubSubClient mqtt(espClient);
DHT dht(PIN_DHT, DHT22);
Adafruit_SSD1306 pantalla(128, 64, &Wire, -1);

int umbral = 40;
bool automatico = false;
bool bomba = false;
bool bombaAnterior = false;
int suelo = 0;
int tanque = 0;
float temperatura = 0;
float humedadAire = 0;

unsigned long finRiego = 0;
unsigned long ultimaLectura = 0;
unsigned long ultimoEnvio = 0;
unsigned long ultimoBoton = 0;
unsigned long ultimaAlarma = 0;
unsigned long ultimoIntento = 0;

bool alertaTanque() {
  return tanque < TANQUE_MINIMO;
}

bool alertaSeca() {
  return suelo < umbral;
}

void pitar() {
  for (int i = 0; i < 100; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delayMicroseconds(500);
    digitalWrite(PIN_BUZZER, LOW);
    delayMicroseconds(500);
  }
}

float medirDistancia() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duracion = pulseIn(PIN_ECHO, HIGH, 30000);
  if (duracion == 0) return 400;
  return duracion * 0.0343 / 2;
}

void leerSensores() {
  suelo = map(analogRead(PIN_SUELO), 0, 4095, 0, 100);
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) temperatura = t;
  if (!isnan(h)) humedadAire = h;
  long mm = (long)(medirDistancia() * 10);
  tanque = constrain(map(mm, 300, 50, 0, 100), 0, 100);
}

void iniciarRiego() {
  finRiego = millis() + DURACION_RIEGO;
  ultimoEnvio = 0;
}

void controlarBomba() {
  bool puedeRegar = !alertaTanque();
  bool forzado = millis() < finRiego;
  bomba = puedeRegar && (forzado || (automatico && alertaSeca()));
  digitalWrite(PIN_RELE, bomba);
  digitalWrite(PIN_LED_BOMBA, bomba);
  if (bomba && !bombaAnterior) pitar();
  if (bomba != bombaAnterior) ultimoEnvio = 0;
  bombaAnterior = bomba;
}

void gestionarAlerta() {
  bool alerta = alertaTanque() || alertaSeca();
  digitalWrite(PIN_LED_ALERTA, alerta);
  if (alertaTanque() && millis() - ultimaAlarma > 5000) {
    ultimaAlarma = millis();
    pitar();
  }
}

void revisarBoton() {
  if (digitalRead(PIN_BOTON) == LOW && millis() - ultimoBoton > 400) {
    ultimoBoton = millis();
    iniciarRiego();
  }
}

void actualizarPantalla() {
  pantalla.clearDisplay();
  pantalla.setTextSize(1);
  pantalla.setTextColor(SSD1306_WHITE);
  pantalla.setCursor(0, 0);
  pantalla.print("RIEGO INTELIGENTE");
  pantalla.print(mqtt.connected() ? " OK" : " --");
  pantalla.drawLine(0, 10, 127, 10, SSD1306_WHITE);
  pantalla.setCursor(0, 14);
  pantalla.print("Suelo:");
  pantalla.print(suelo);
  pantalla.print("% Tanque:");
  pantalla.print(tanque);
  pantalla.print("%");
  pantalla.setCursor(0, 26);
  pantalla.print("Aire:");
  pantalla.print(temperatura, 1);
  pantalla.print("C Hum:");
  pantalla.print(humedadAire, 0);
  pantalla.print("%");
  pantalla.setCursor(0, 38);
  pantalla.print(automatico ? "AUTO" : "MANUAL");
  pantalla.print(" u:");
  pantalla.print(umbral);
  pantalla.print(" Bomba:");
  pantalla.print(bomba ? "ON" : "OFF");
  pantalla.setTextSize(2);
  pantalla.setCursor(0, 49);
  if (alertaSeca()) pantalla.print("SECA");
  else if (suelo > 80) pantalla.print("ENCHARCADA");
  else pantalla.print("BIEN");
  pantalla.display();
}

void publicarDatos() {
  String json = "{\"suelo\":" + String(suelo) +
                ",\"temp\":" + String(temperatura, 1) +
                ",\"hum\":" + String(humedadAire, 1) +
                ",\"tanque\":" + String(tanque) +
                ",\"bomba\":" + String(bomba ? "true" : "false") +
                ",\"auto\":" + String(automatico ? "true" : "false") +
                ",\"alerta\":" + String((alertaTanque() || alertaSeca()) ? "true" : "false") +
                ",\"umbral\":" + String(umbral) + "}";
  mqtt.publish(TOPIC_DATOS, json.c_str());
}

void recibirComando(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  if (msg == "regar") {
    iniciarRiego();
  } else if (msg == "auto") {
    automatico = true;
  } else if (msg == "manual") {
    automatico = false;
  } else if (msg.startsWith("umbral:")) {
    umbral = constrain(msg.substring(7).toInt(), 0, 100);
  }
  ultimoEnvio = 0;
}

void mantenerConexion() {
  if (millis() - ultimoIntento < 5000) return;
  if (WiFi.status() != WL_CONNECTED) {
    ultimoIntento = millis();
    Serial.println("Sin WiFi, esperando...");
    return;
  }
  if (!mqtt.connected()) {
    ultimoIntento = millis();
    Serial.println("Conectando MQTT...");
    String id = "esp32-riego-" + String(random(0xffff), HEX);
    if (mqtt.connect(id.c_str())) {
      mqtt.subscribe(TOPIC_COMANDO);
      Serial.println("MQTT conectado");
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_BOTON, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_BOMBA, OUTPUT);
  pinMode(PIN_LED_ALERTA, OUTPUT);
  pinMode(PIN_RELE, OUTPUT);

  dht.begin();
  Wire.begin(21, 22);
  pantalla.begin(SSD1306_SWITCHCAPVCC, 0x3C);

  WiFi.begin(WIFI_SSID, "", 6);
  mqtt.setServer(BROKER, 1883);
  mqtt.setCallback(recibirComando);
  mqtt.setSocketTimeout(2);

  leerSensores();
  actualizarPantalla();
}

void loop() {
  mantenerConexion();
  mqtt.loop();

  revisarBoton();

  if (millis() - ultimaLectura >= 1000) {
    ultimaLectura = millis();
    leerSensores();
    actualizarPantalla();
  }

  controlarBomba();
  gestionarAlerta();

  if (mqtt.connected() && millis() - ultimoEnvio >= 2000) {
    ultimoEnvio = millis();
    publicarDatos();
  }
}
