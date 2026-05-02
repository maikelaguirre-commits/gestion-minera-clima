import os
import time

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from clima import generar_dashboard  
app = Flask(__name__)

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

cache = {}

def calcular_protocolo(temp_c: float) -> dict:
    if temp_c >= 30:
        return {
            "riesgo": "CRÍTICO",
            "clase": "bg-critico",
            "nutricion": "MENU HIDRATANTE: Priorizar ensaladas de hoja verde, frutas (sandía/melón) y legumbres frías. ALERTA: Suplementar con bebidas isotónicas cada 2 horas.",
            "medidas": "Protocolo de Calor Extremo activo. Pausas de 15 min por cada 45 min de trabajo. Prohibido trabajos en altura no ventilada.",
        }
    if temp_c >= 24:
        return {
            "riesgo": "MODERADO",
            "clase": "bg-alerta",
            "nutricion": "MENU BALANCEADO: Aumentar consumo de agua mineral. Proteínas magras a la plancha. Evitar frituras que dificulten la digestión térmica.",
            "medidas": "Suministro de agua en punto de trabajo. Uso obligatorio de protector solar cada 3 horas. Ventilación forzada en cabinas.",
        }
    if temp_c <= 10:
        return {
            "riesgo": "CRÍTICO",
            "clase": "bg-critico",
            "nutricion": "MENU TÉRMICO: Sopas calóricas (cazuelas), guisos con legumbres y carbohidratos complejos. Bebidas calientes constantes (té/café/chocolate).",
            "medidas": "Protocolo de Frío Activo. Ropa térmica obligatoria. Rotación de personal cada 30 min en áreas expuestas a viento.",
        }
    if temp_c <= 16:
        return {
            "riesgo": "MODERADO",
            "clase": "bg-alerta",
            "nutricion": "MENU REFORZADO: Priorizar pastas y cereales. Infusiones calientes disponibles en faena. Frutos secos como snack para aporte graso saludable.",
            "medidas": "Verificación de calefacción en equipos. Minimizar tiempos de espera en exteriores.",
        }
    return {
        "riesgo": "NORMAL",
        "clase": "bg-normal",
        "nutricion": "MENU ESTÁNDAR: Alimentación balanceada según minuta mensual. Mantener hidratación base de 2 litros diarios.",
        "medidas": "Operación bajo parámetros normales. Seguir medidas de seguridad estándar.",
    }

def obtener_clima(lat, lon):
    if not OPENWEATHER_API_KEY:
        raise RuntimeError("Falta OPENWEATHER_API_KEY en variables de entorno.")

    url = "https://api.openweathermap.org/data/2.5/weather"
    res = requests.get(
        url,
        params={
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "es",
        },
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
   
    data["main"] = data.get("main") or data.get("principal")

    if "main" in data:
        data["main"]["humidity"] = data["main"].get("humidity") or data["main"].get("humedad")

    return data


@app.route("/")
def inicio():
    return render_template("dashboard.html")

@app.route("/api/clima")
def clima():
    lat_raw = request.args.get("lat", type=str)
    lon_raw = request.args.get("lon", type=str)
    if not lat_raw or not lon_raw:
        return jsonify({"error": "Faltan parámetros 'lat' y 'lon'."}), 400

    try:
        lat = float(lat_raw)
        lon = float(lon_raw)
    except ValueError:
        return jsonify({"error": "Parámetros 'lat' y 'lon' inválidos."}), 400

    key = f"{lat},{lon}"
    ahora = time.time()

    # cache 60 segundos
    if key in cache and ahora - cache[key]["time"] < 60:
        return jsonify(cache[key]["data"])

    try:
        data = obtener_clima(lat, lon)
    except requests.RequestException:
        return jsonify({"error": "Error al consultar servicio de clima."}), 502
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    try:
        temp_c = float(data.get("main", {}).get("temp"))
    except (TypeError, ValueError):
        temp_c = None

    data["protocolo"] = calcular_protocolo(temp_c) if temp_c is not None else {
        "riesgo": "N/D",
        "clase": "bg-normal",
        "nutricion": "--",
        "medidas": "--",
    }

    cache[key] = {
        "data": data,
        "time": ahora
    }

    return jsonify(data)

