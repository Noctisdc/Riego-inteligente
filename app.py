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
            /* Fondo blanco hueso con toque botánico */
            .stApp {
                background-color: #F3F6F1;
                color: #1B3B2B;
            }

            /* Barra lateral verde bosque con degradado */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #1B4332 0%, #2D6A4F 100%);
            }
            section[data-testid="stSidebar"] * {
                color: #F4F6F0 !important;
            }
            section[data-testid="stSidebar"] a[aria-current="page"] {
                background-color: rgba(255, 255, 255, 0.16) !important;
                border-radius: 10px;
                font-weight: 700;
            }

            /* Banner principal (Hero) */
            .hero-card {
                background: linear-gradient(135deg, #1B4332 0%, #2D6A4F 55%, #40916C 100%);
                color: #F7F9F5;
                padding: 26px 30px;
                border-radius: 18px;
                box-shadow: 0 10px 24px rgba(27, 67, 50, 0.18);
                margin-bottom: 22px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 16px;
            }
            .hero-title {
                font-size: 2rem;
                font-weight: 800;
                margin: 0;
                letter-spacing: -0.5px;
            }
            .hero-sub {
                font-size: 1rem;
                opacity: 0.92;
                margin: 6px 0 0 0;
            }

            /* Indicador pulsante "En vivo" */
            .live-pill {
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                padding: 8px 16px;
                border-radius: 999px;
                font-size: 0.9rem;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                backdrop-filter: blur(4px);
            }
            .live-dot {
                width: 10px;
                height: 10px;
                background-color: #95D5B2;
                border-radius: 50%;
                display: inline-block;
                box-shadow: 0 0 0 0 rgba(149, 213, 178, 0.8);
                animation: pulso 1.8s infinite;
            }
            @keyframes pulso {
                0% { box-shadow: 0 0 0 0 rgba(149, 213, 178, 0.8); }
                70% { box-shadow: 0 0 0 10px rgba(149, 213, 178, 0); }
                100% { box-shadow: 0 0 0 0 rgba(149, 213, 178, 0); }
            }

            /* Títulos de secciones */
            h1, h2, h3 {
                color: #1B4332 !important;
                font-weight: 700 !important;
            }

            /* Tarjetas de métricas con efecto hover */
            div[data-testid="stMetric"] {
                background-color: #FAFBF8;
                border: 1px solid #D8E2DC;
                border-top: 4px solid #2D6A4F;
                border-radius: 14px;
                padding: 16px 18px;
                box-shadow: 0 4px 12px rgba(27, 67, 50, 0.06);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            div[data-testid="stMetric"]:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 18px rgba(27, 67, 50, 0.12);
            }
            div[data-testid="stMetricLabel"] {
                color: #4A6B5D !important;
                font-weight: 600 !important;
            }
            div[data-testid="stMetricValue"] {
                color: #1B4332 !important;
                font-size: 1.8rem !important;
                font-weight: 800 !important;
            }

            /* Contenedores con borde */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #FAFBF8;
                border: 1px solid #D8E2DC !important;
                border-radius: 16px !important;
                padding: 20px !important;
                box-shadow: 0 4px 12px rgba(27, 67, 50, 0.04);
            }

            /* Botones verdes */
            div.stButton > button {
                background: linear-gradient(135deg, #2D6A4F 0%, #40916C 100%);
                color: #FAFBF8;
                border: none;
                border-radius: 12px;
                padding: 0.65rem 1.2rem;
                font-weight: 700;
                box-shadow: 0 4px 10px rgba(45, 106, 79, 0.22);
                transition: all 0.2s ease;
            }
            div.stButton > button:hover {
                background: linear-gradient(135deg, #1B4332 0%, #2D6A4F 100%);
                transform: translateY(-1px);
                color: #FFFFFF;
            }
            div.stButton > button:disabled {
                background: #B7C9BE;
                box-shadow: none;
                color: #F3F6F1;
            }

            /* Barras de progreso personalizadas */
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
        return "Seca", "🥀", "La tierra está por debajo del
