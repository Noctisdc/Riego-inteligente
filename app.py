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


def aplicar_estilos():
    st.markdown(
        """
        <style>
            /* Fondo principal blanco hueso */
            .stApp {
                background-color: #F5F3EC;
                color: #1D3525;
            }

            /* Barra lateral verde bosque con degradado */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #1B4332 0%, #2D6A4F 100%);
                border-right: 1px solid #163628;
            }
            section[data-testid="stSidebar"] * {
                color: #F5F3EC !important;
            }
            section[data-testid="stSidebar"] a[aria-current="page"] {
                background-color: rgba(245, 243, 236, 0.16) !important;
                border-radius: 10px;
                font-weight: 700;
            }

            /* Encabezado principal */
            .hero-banner {
                background: linear-gradient(135deg, #1B4332 0%, #2D6A4F 60%, #40916C 100%);
                color: #F5F3EC;
                padding: 24px 28px;
                border-radius: 16px;
                box-shadow: 0 8px 20px rgba(27, 67, 50, 0.15);
                margin-bottom: 22px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
            }
            .hero-titulo {
                font-size: 1.9rem;
                font-weight: 800;
                margin: 0;
                letter-spacing: -0.4px;
            }
            .hero-subtitulo {
                font-size: 0.98rem;
                opacity: 0.9;
                margin: 4px 0 0 0;
            }
            .estado-pill {
                background: rgba(245, 243, 236, 0.16);
                border: 1px solid rgba(245, 243, 236, 0.32);
                padding: 8px 16px;
                border-radius: 999px;
                font-size: 0.88rem;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }
            .punto-vivo {
                width: 9px;
                height: 9px;
                background-color: #95D5B2;
                border-radius: 50%;
                display: inline-block;
                animation: pulso 1.8s infinite;
            }
            @keyframes pulso {
                0% { box-shadow: 0 0 0 0 rgba(149, 213, 178, 0.8); }
                70% { box-shadow: 0 0 0 9px rgba(149, 213, 178, 0); }
                100% { box-shadow: 0 0 0 0 rgba(149, 213, 178, 0); }
            }

            /* Títulos */
            h1, h2, h3 {
                color: #1B4332 !important;
                font-weight: 700 !important;
            }

            /* Tarjetas de métricas */
            div[data-testid="stMetric"] {
                background-color: #FCFBF7;
                border: 1px solid #DCD9CE;
                border-top: 4px solid #2D6A4F;
                border-radius: 14px;
                padding: 16px 18px;
                box-shadow: 0 4px 12px rgba(27, 67, 50, 0.06);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            div[data-testid="stMetric"]:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(27, 67, 50, 0.1);
            }
            div[data-testid="stMetricLabel"] {
                color: #4A6353 !important;
                font-weight: 600 !important;
            }
            div[data-testid="stMetricValue"] {
                color: #1B4332 !important;
                font-size: 1.75rem !important;
                font-weight: 800 !important;
            }

            /* Contenedores con borde */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #FCFBF7;
                border: 1px solid #DCD9CE !important;
                border-radius: 16px !important;
                padding: 20px !important;
                box-shadow: 0 4px 12px rgba(27, 67, 50, 0.04);
            }

            /* Botones en verde */
            div.stButton > button {
                background: linear-gradient(135deg, #2D6A4F 0%, #40916C 100%);
                color: #F5F3EC;
                border: none;
                border-radius: 10px;
                padding: 0.6rem 1.2rem;
                font-weight: 600;
                box-shadow: 0 4px 10px rgba(45, 106, 79, 0.2);
                transition: all 0.2s ease;
            }
            div.stButton > button:hover {
                background: linear-gradient(135deg, #1B4332 0%, #2D6A4F 100%);
                color: #FFFFFF;
                transform: translateY(-1px);
            }

            /* Barras de progreso */
            div[data-testid="stProgress"] > div > div > div > div {
                background: linear-gradient(90deg, #2D6A4F 0%, #52B788 100%);
                border-radius: 8px;
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
        return "Seca"
    if d["suelo"] > 80:
        return "Encharcada"
    return "En buen estado"


def monitoreo():
    st_autorefresh(interval=2000, key="refresco")
    d = estado["ultimo"]
    if d is None:
        st.markdown(
            """
            <div class="hero-banner">
                <div>
                    <p class="hero-titulo">Monitoreo de la planta</p>
                    <p class="hero-subtitulo">Esperando datos del ESP32. Inicia la simulación en Wokwi.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    tanque = d.get("tanque", 0)
    st.markdown(
        f"""
        <div class="hero-banner">
            <div>
                <p class="hero-titulo">Monitoreo de la planta</p>
                <p class="hero-subtitulo">La planta está: {clasificar(d)}</p>
            </div>
            <div class="estado-pill">
                <span class="punto-vivo"></span>
                Modo: {'automático' if d['auto'] else 'manual'} | Umbral: {d['umbral']} % | {d['hora']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.write("")

    with st.container(border=True):
        b1, b2 = st.columns(2, gap="large")
        with b1:
            st.progress(min(max(d["suelo"], 0), 100) / 100, text="Humedad del suelo")
        with b2:
            st.progress(min(max(tanque, 0), 100) / 100, text="Nivel del tanque")

    st.write("")

    with st.container(border=True):
        df = pd.DataFrame(estado["historial"])
        columnas = [c for c in ["suelo", "hum", "tanque"] if c in df]
        st.line_chart(df.set_index("hora")[columnas], color=["#2D6A4F", "#74C69D", "#40916C"])


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
    d = estado["ultimo"]
    subtitulo = (
        f"Estado actual: {clasificar(d)} ({d['suelo']} % de humedad, tanque al {d.get('tanque', 0)} %)"
        if d
        else "Esperando datos del ESP32"
    )

    st.markdown(
        f"""
        <div class="hero-banner">
            <div>
                <p class="hero-titulo">Control del riego</p>
                <p class="hero-subtitulo">{subtitulo}</p>
            </div>
            <div class="estado-pill">
                <span class="punto-vivo"></span>
                Conexión MQTT
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            if st.button("Regar ahora", use_container_width=True):
                cliente.publish(T_COM, "regar")
                st.success("Orden de riego enviada")

            st.divider()

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

    with col2:
        with st.container(border=True):
            st.subheader("Orden por texto o voz")
            texto = st.text_input("Escribe una orden", placeholder="riega la planta")
            enviar = st.button("Enviar orden", use_container_width=True)
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
