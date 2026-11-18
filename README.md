# Sistema de riego inteligente de plantas

Proyecto final de Interfaces Multimodales (Diseño Interactivo, Universidad EAFIT).

Aplicación web en Streamlit que permite monitorear y controlar el riego de una planta mediante un circuito simulado en Wokwi. Los dos lados se comunican en ambos sentidos por MQTT.

- Aplicación publicada: ENLACE_DE_LA_APP
- Simulación en Wokwi: ENLACE_DE_WOKWI

## Problema

Las plantas se secan por olvido, se pudren por exceso de agua y quedan desatendidas cuando la persona viaja. Hoy se resuelve con intuición, tocando la tierra y adivinando. Este sistema mide el estado real de la planta, avisa y permite regar a distancia.

## Cómo funciona

1. El ESP32 mide la humedad del suelo, la temperatura, la humedad del aire y el nivel del tanque de agua.
2. Publica los datos por MQTT cada 2 segundos.
3. La app de Streamlit los recibe y los muestra en la página de Monitoreo.
4. Desde la página de Control el usuario envía órdenes: regar, cambiar el modo o ajustar el umbral.
5. El ESP32 recibe la orden, activa el relé (la bomba) y confirma el nuevo estado.

```
Wokwi (ESP32) <---- MQTT (broker.hivemq.com) ----> Streamlit
 sensores y bomba                                  Monitoreo / Control
```

## Modalidades de interacción

| Modalidad | Tipo | Uso |
|---|---|---|
| Voz | Entrada | Órdenes como "riega la planta" o "cómo está mi planta" |
| Texto | Entrada | Las mismas órdenes escritas |
| Botones | Entrada | Regar ahora y cambio de modo en la web; botón físico en el circuito |
| Control deslizante | Entrada | Umbral de humedad para el riego automático |
| Sensores | Entrada | Humedad del suelo, temperatura, humedad del aire y nivel del tanque |
| Indicadores visuales | Salida | Estado, alertas, barras y gráfica en tiempo real |
| Pantalla OLED, LED y buzzer | Salida | Estado y alertas en el propio circuito |
| Relé | Salida | Bomba de agua simulada |

## Páginas de la app

- **Monitoreo:** estado de la planta, valores de los sensores, nivel del tanque, alertas y gráfica.
- **Control:** botón de riego, modo manual o automático, umbral y órdenes por texto o voz.

## Lógica del circuito

- En modo automático la bomba se activa cuando la humedad del suelo baja del umbral.
- Si el tanque tiene menos de 10 %, la bomba se bloquea y suena una alarma.
- El LED rojo indica alerta (planta seca o tanque bajo) y el LED azul indica bomba encendida.
- Si no hay red, el circuito sigue funcionando de forma local y se reconecta solo.

## Comunicación MQTT

Broker público: `broker.hivemq.com`, puerto 1883.

| Tópico | Dirección | Contenido |
|---|---|---|
| `camilo/riego/datos` | ESP32 a app | JSON con suelo, temp, hum, tanque, bomba, auto, alerta y umbral |
| `camilo/riego/comando` | App a ESP32 | `regar`, `auto`, `manual` o `umbral:NN` |

## Conexiones del circuito

| Componente | Pin del ESP32 |
|---|---|
| DHT22 (datos) | D15 |
| Potenciómetro, humedad del suelo (señal) | D34 |
| Sensor ultrasónico HC-SR04 (TRIG / ECHO) | D5 / D18 |
| Pantalla OLED SSD1306 (SDA / SCL) | D21 / D22 |
| Botón de riego | D13 |
| Buzzer | D27 |
| LED azul, bomba (con resistencia) | D2 |
| LED rojo, alerta (con resistencia) | D4 |
| Módulo relé (IN) | D26 |

## Cómo ejecutarlo

### 1. Simulación en Wokwi

1. Crea un proyecto ESP32 en wokwi.com.
2. Copia en él los tres archivos de la carpeta `firmware`: `sketch.ino`, `diagram.json` y `libraries.txt`.
3. Pulsa play. La pantalla OLED muestra "OK" junto al título cuando conecta al broker.

### 2. Aplicación

```
pip install -r requirements.txt
python -m streamlit run app.py
```

La app abre en `http://localhost:8501`. Para usar la voz se necesita Chrome o Edge y permitir el micrófono.

## Tecnologías

ESP32, Wokwi, MQTT (paho-mqtt), Python, Streamlit y reconocimiento de voz del navegador (streamlit-mic-recorder).

## Autor

Camilo, estudiante de Diseño Interactivo, Universidad EAFIT.
