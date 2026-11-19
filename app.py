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

st.set_page_config(
    page_title="Riego Inteligente",
    page_icon="🌿",
    layout="wide",
)


def aplicar_estilos():
    st.markdown(
        """
        <style>
            /* Fondo principal blanco hueso */
            .stApp {
                background-color: #F6F4EE;
                color: #1F2E22;
            }

            /* Barra lateral en blanco hueso cálido */
            section[data-testid="stSidebar"] {
                background-color: #EAE6DC;
                border-right: 1px solid #D8D2C5;
            }

            /* Títulos en verde oscuro */
            h1, h2, h3 {
                color: #1E4226 !important;
                font-weight: 700 !important;
            }

            /* Tarjetas de métricas */
            div[data-testid="stMetric"] {
                background-color: #FCFBF7;
                border: 1px solid #DCD6C8;
                border-left: 5px solid #2D5A36;
                border-radius: 12px;
                padding: 16px 18px;
                box-shadow: 0 2px 6px rgba(30, 66, 38, 0.06);
            }
            div[data-testid="stMetricLabel"] {
                color: #4A5D4E !important;
                font-size: 0.9rem !important;
                font-weight: 600 !important;
            }
            div[data-testid="stMetricValue"] {
                color: #1E4226 !important;
                font-size: 1.7rem !important;
            }

            /* Contenedores con borde */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #FCFBF7;
                border: 1px solid #DCD6C8 !important;
                border-radius: 14px !important;
                padding: 18px !important;
            }

            /* Botones principales en verde */
            div.stButton > button {
                background-color: #2D5A36;
                color: #F6F4EE;
                border: none;
                border-radius: 10px;
                padding: 0.6rem 1.2rem;
                font-weight: 600;
                transition: background-color 0.2s ease, transform 0.1s ease;
            }
            div.stButton > button:hover {
                background-color: #214528;
                color: #FFFFFF;
            }
            div.stButton > button:disabled {
                background-color: #B8C2B9;
                color: #F6F4EE;
            }

            /* Barras de progreso en verde */
            div[data-testid="stProgress"] > div > div > div > div {
                background-color: #2D5A36;
            }

            /* Badge de estado */
            .estado-badge {
                display: inline-block;
                padding: 6px 14px;
                border-radius: 999px;
                font-weight: 700;
                font-size: 0.95rem;
                margin-bottom: 12px;
            }
            .estado-bien {
                background-color: #DCECE0;
                color: #1E4226;
                border: 1px solid #9EC4A6;
            }
            .estado-seca {
                background-color: #F8E5D8;
                color: #8C3B14;
                border: 1px solid #E5B495;
            }
            .estado-encharcada {
                background-color: #DCE8F2;
                color: #1B4B72;
                border: 1px solid #A4C4DE;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


aplicar_estilos()
cliente, estado = iniciar()


def clasificar(d):
    if d["suelo"] < d["umbral"]:
        return "Seca", "estado-seca"
    if d["suelo"] > 80:
        return "Encharcada", "estado-encharcada"
    return "En buen estado", "estado-bien"


def monitoreo():
    st_autorefresh(interval=2000, key="refresco")
    st.title("Monitoreo de la planta")

    d = estado["ultimo"]
    if d is None:
        st.info("Esperando datos del ESP32. Inicia la simulación en Wokwi.")
        return

    texto_estado, clase_estado = clasificar(d)
    tanque = d.get("tanque", 0)

    st.markdown(
        f'<div class="estado-badge {clase_estado}">Estado de la planta: {texto_estado}</div>',
        unsafe_allow_html=True,
    )

    if tanque < 10:
        st.error("Tanque casi vacío (< 10 %): la bomba está bloqueada por seguridad hasta que se rellene.")
    elif d["suelo"] < d["umbral"]:
        st.warning(f"La planta necesita agua (humedad por debajo del umbral de {d['umbral']} %).")

    # Métricas principales
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Humedad del suelo", f"{d['suelo']} %")
    c2.metric("Temperatura", f"{d['temp']} °C")
    c3.metric("Humedad del aire", f"{d['hum']} %")
    c4.metric("Nivel del tanque", f"{tanque} %")
    c5.metric("Bomba", "Encendida" if d["bomba"] else "Apagada")

    st.write("")

    # Barras de progreso en dos columnas
    with st.container(border=True):
        b1, b2 = st.columns(2)
        with b1:
            st.progress(
                min(max(d["suelo"], 0), 100) / 100,
                text=f"Humedad del suelo: {d['suelo']} % (Umbral: {d['umbral']} %)",
            )
        with b2:
            st.progress(
                min(max(tanque, 0), 100) / 100,
                text=f"Nivel del tanque: {tanque} % (Mínimo seguro: 10 %)",
            )
        st.caption(
            f"Modo actual: {'Automático' if d['auto'] else 'Manual'}  •  "
            f"Última lectura recibida: {d['hora']}"
        )

    # Gráfica histórica con nombres claros
    st.subheader("Historial en tiempo real")
    df = pd.DataFrame(estado["historial"])
    renombrar = {"suelo": "Suelo (%)", "hum": "Aire (%)", "tanque": "Tanque (%)"}
    columnas = [c for c in ["suelo", "hum", "tanque"] if c in df]
    if not df.empty and columnas:
        df_plot = df.set_index("hora")[columnas].rename(columns=renombrar)
        st.line_chart(df_plot, color=["#2D5A36", "#7FA688", "#4A7C9B"])


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
        texto_estado, _ = clasificar(d)
        return (
            f"La planta está {texto_estado.lower()}, con {d['suelo']} % de humedad "
            f"en el suelo y el tanque al {d.get('tanque', 0)} %"
        )
    if "rieg" in f or "regar" in f or "agua" in f:
        cliente.publish(T_COM, "regar")
        return "Orden de riego enviada"
    return "No entendí la orden. Prueba con: riega la planta, modo automático, umbral 50, nivel del tanque o cómo está mi planta."


def control():
    st.title("Control del riego")
    d = estado["ultimo"]

    # Resumen rápido arriba
    if d:
        texto_estado, clase_estado = clasificar(d)
        tanque = d.get("tanque", 0)
        st.markdown(
            f'<div class="estado-badge {clase_estado}">{texto_estado} • Suelo: {d["suelo"]} % • Tanque: {tanque} %</div>',
            unsafe_allow_html=True,
        )
        tanque_vacio = tanque < 10
    else:
        st.info("Esperando conexión con el ESP32 para mostrar el estado en vivo.")
        tanque_vacio = False

    col_ctrl, col_voz = st.columns([1, 1], gap="large")

    # Columna izquierda: Controles directos
    with col_ctrl:
        with st.container(border=True):
            st.subheader("Control manual y automático")

            if st.button(
                "Regar ahora (3 segundos)",
                use_container_width=True,
                disabled=tanque_vacio,
            ):
                cliente.publish(T_COM, "regar")
                st.success("Orden de riego enviada al ESP32.")

            if tanque_vacio:
                st.caption("Botón deshabilitado: el tanque tiene menos del 10 % de agua.")

            st.divider()

            st.radio(
                "Modo de operación",
                ["manual", "auto"],
                format_func=lambda x: "Manual" if x == "manual" else "Automático",
                horizontal=True,
                key="modo",
                on_change=lambda: cliente.publish(T_COM, st.session_state.modo),
            )

            st.slider(
                "Umbral mínimo de humedad (%)",
                0,
                100,
                40,
                key="umbral",
                on_change=lambda: cliente.publish(T_COM, f"umbral:{st.session_state.umbral}"),
            )

    # Columna derecha: Asistente por texto o voz
    with col_voz:
        with st.container(border=True):
            st.subheader("Asistente por texto o voz")
            st.caption("Ejemplos: *riega la planta*, *modo automático*, *umbral 50*, *nivel del tanque*, *¿cómo está mi planta?*")

            texto = st.text_input("Escribe una orden", placeholder="Ej: riega la planta")
            enviar = st.button("Enviar orden", use_container_width=True)

            st.write("O dicta tu comando por micrófono:")
            voz = speech_to_text(
                language="es",
                start_prompt="Hablar",
                stop_prompt="Detener",
                just_once=True,
                key="voz",
            )

            if voz:
                st.write(f"**Escuché:** {voz}")
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
