import json
import re
import time
import pandas as pd
import streamlit as st
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh
from streamlit_mic_recorder import speech_to_text

BROKER = "broker.hivemq.com"
T_DATOS = "camilo/riego/datos"
T_COM = "camilo/riego/comando"

st.set_page_config(page_title="Riego inteligente", layout="wide")


@st.cache_resource
def iniciar():
    estado = {"ultimo": None, "historial": []}

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(T_DATOS)

    def on_message(client, userdata, msg):
        try:
            d = json.loads(msg.payload.decode())
        except Exception:
            return
        d["hora"] = time.strftime("%H:%M:%S")
        estado["ultimo"] = d
        estado["historial"].append(d)
        estado["historial"] = estado["historial"][-100:]

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.on_connect = on_connect
    c.on_message = on_message
    c.connect(BROKER, 1883, 60)
    c.loop_start()
    return c, estado


cliente, estado = iniciar()


def clasificar(d):
    if d["suelo"] < d["umbral"]:
        return "Seca"
    if d["suelo"] > 80:
        return "Encharcada"
    return "En buen estado"


def monitoreo():
    st_autorefresh(interval=2000, key="refresco")
    st.title("Monitoreo de la planta")
    d = estado["ultimo"]
    if d is None:
        st.info("Esperando datos del ESP32. Inicia la simulación en Wokwi.")
        return
    st.subheader(f"La planta está: {clasificar(d)}")
    tanque = d.get("tanque", 0)
    if tanque < 10:
        st.error("Tanque casi vacío: la bomba está bloqueada hasta que se rellene")
    elif d["suelo"] < d["umbral"]:
        st.warning("La planta necesita agua")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Humedad del suelo", f"{d['suelo']} %")
    c2.metric("Temperatura", f"{d['temp']} °C")
    c3.metric("Humedad del aire", f"{d['hum']} %")
    c4.metric("Nivel del tanque", f"{tanque} %")
    c5.metric("Bomba", "Encendida" if d["bomba"] else "Apagada")
    st.progress(min(max(d["suelo"], 0), 100) / 100, text="Humedad del suelo")
    st.progress(min(max(tanque, 0), 100) / 100, text="Nivel del tanque")
    st.caption(
        f"Modo: {'automático' if d['auto'] else 'manual'} | "
        f"Umbral: {d['umbral']} % | Última lectura: {d['hora']}"
    )
    df = pd.DataFrame(estado["historial"])
    columnas = [c for c in ["suelo", "hum", "tanque"] if c in df]
    st.line_chart(df.set_index("hora")[columnas])


def interpretar(frase):
    f = frase.lower()
    d = estado["ultimo"]
    if "umbral" in f:
        n = re.search(r"\d+", f)
        if n:
            cliente.publish(T_COM, f"umbral:{n.group()}")
            return f"Umbral cambiado a {n.group()} %"
    if "autom" in f:
        cliente.publish(T_COM, "auto")
        return "Modo automático activado"
    if "manual" in f:
        cliente.publish(T_COM, "manual")
        return "Modo manual activado"
    if "tanque" in f:
        if d is None:
            return "Todavía no hay datos del tanque"
        return f"El tanque está al {d.get('tanque', 0)} %"
    if "estado" in f or "cómo está" in f or "como esta" in f:
        if d is None:
            return "Todavía no hay datos de la planta"
        return (
            f"La planta está {clasificar(d).lower()}, con {d['suelo']} % de humedad "
            f"en el suelo y el tanque al {d.get('tanque', 0)} %"
        )
    if "rieg" in f or "regar" in f or "agua" in f:
        cliente.publish(T_COM, "regar")
        return "Orden de riego enviada"
    return "No entendí la orden. Prueba con: riega la planta, modo automático, umbral 50, nivel del tanque o cómo está mi planta"


def control():
    st.title("Control del riego")
    d = estado["ultimo"]
    if d:
        st.write(
            f"Estado actual: {clasificar(d)} ({d['suelo']} % de humedad, "
            f"tanque al {d.get('tanque', 0)} %)"
        )

    if st.button("Regar ahora", use_container_width=True):
        cliente.publish(T_COM, "regar")
        st.success("Orden de riego enviada")

    st.radio(
        "Modo de riego",
        ["manual", "auto"],
        horizontal=True,
        key="modo",
        on_change=lambda: cliente.publish(T_COM, st.session_state.modo),
    )
    st.slider(
        "Umbral de humedad (%)",
        0,
        100,
        40,
        key="umbral",
        on_change=lambda: cliente.publish(T_COM, f"umbral:{st.session_state.umbral}"),
    )

    st.subheader("Orden por texto o voz")
    texto = st.text_input("Escribe una orden", placeholder="riega la planta")
    enviar = st.button("Enviar orden")
    st.write("O habla:")
    voz = speech_to_text(language="es", just_once=True, key="voz")

    if voz:
        st.write(f"Escuché: {voz}")
        st.info(interpretar(voz))
    elif enviar and texto:
        st.info(interpretar(texto))


pagina = st.navigation(
    [
        st.Page(monitoreo, title="Monitoreo"),
        st.Page(control, title="Control"),
    ]
)
pagina.run()
