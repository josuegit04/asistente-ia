import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import winsound
import os
import webbrowser
import time
import re
import subprocess
import psutil
from datetime import datetime
from PIL import ImageGrab
from google import genai
from google.genai import types

# ==========================================
# 1. CONFIGURACIÓN DE GEMINI API
# ==========================================
# Puedes poner tu API Key aquí o en la variable de entorno GEMINI_API_KEY
API_KEY = ""  # Reemplaza con tu API Key de Gemini
MODELO = "gemini-2.5-flash"

client = genai.Client(api_key=API_KEY)

# Inicializamos el mezclador de sonido una sola vez al arrancar
pygame.mixer.init()

# ==========================================
# 2. LA BOCA (Habla en voz alta con TTS)
# ==========================================
def hablar(texto: str):
    if not texto:
        return

    # Limpiamos caracteres de formato Markdown que Gemini pudiera incluir
    texto_limpio = re.sub(r'[*#_`~]', '', texto).strip()
    if not texto_limpio:
        return

    print(f"\nJarvis: {texto_limpio}")
    archivo_audio = f"voz_{int(time.time() * 1000)}.mp3"

    async def generar_audio():
        comunicacion = edge_tts.Communicate(texto_limpio, "es-MX-JorgeNeural", rate="+15%")
        await comunicacion.save(archivo_audio)

    try:
        asyncio.run(generar_audio())
        pygame.mixer.music.load(archivo_audio)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(15)

        pygame.mixer.music.unload()
    except Exception as e:
        print(f"[Error de audio: {e}]")
    finally:
        if os.path.exists(archivo_audio):
            try:
                os.remove(archivo_audio)
            except OSError:
                pass

# ==========================================
# 3. LAS MANOS (Herramientas nativas de Gemini)
# ==========================================
# Gemini leerá los docstrings y tipos de datos para ejecutar estas funciones automáticamente

MAPA_APPS = {
    "calculadora": "calc",
    "bloc de notas": "notepad",
    "notepad": "notepad",
    "chrome": "chrome",
    "navegador": "chrome",
    "explorador": "explorer",
    "cmd": "cmd",
    "terminal": "wt",
    "spotify": "spotify",
    "vscode": "code",
    "visual studio code": "code",
    "word": "winword",
    "excel": "excel",
    "configuracion": "ms-settings:",
    "administrador de tareas": "taskmgr"
}

def abrir_pagina_web(url: str) -> str:
    """Abre cualquier sitio web o realiza una búsqueda en el navegador predeterminado.
    
    Args:
        url: La dirección URL completa (ej. 'https://www.youtube.com' o 'https://www.google.com/search?q=clima').
    """
    if not url.startswith("http"):
        url = "https://" + url
    print(f">>> [SISTEMA: Abriendo web -> {url}] <<<")
    webbrowser.open(url)
    return f"Página {url} abierta correctamente."

def abrir_aplicacion(nombre_app: str) -> str:
    """Abre una aplicación o programa en el computador Windows.
    
    Args:
        nombre_app: Nombre común de la aplicación (ej. 'calculadora', 'chrome', 'vscode', 'spotify', 'notepad').
    """
    clave = nombre_app.lower().strip()
    ejecutable = MAPA_APPS.get(clave, clave)
    print(f">>> [SISTEMA: Abriendo aplicación -> {ejecutable}] <<<")
    try:
        os.system(f"start {ejecutable}")
        return f"Aplicación {nombre_app} iniciada."
    except Exception as e:
        return f"No se pudo abrir {nombre_app}: {str(e)}"

def cerrar_aplicacion(nombre_proceso: str) -> str:
    """Cierra una aplicación o proceso en ejecución en Windows.
    
    Args:
        nombre_proceso: Nombre del ejecutable o programa (ej. 'chrome.exe', 'calc.exe', 'notepad.exe', 'spotify.exe').
    """
    if not nombre_proceso.lower().endswith(".exe"):
        nombre_proceso += ".exe"
    
    # Protección básica de procesos críticos del sistema
    procesos_protegidos = {"explorer.exe", "svchost.exe", "lsass.exe", "csrss.exe", "wininit.exe", "system"}
    if nombre_proceso.lower() in procesos_protegidos:
        return "Operación denegada: No puedo cerrar procesos críticos del sistema operativo."

    print(f">>> [SISTEMA: Cerrando proceso -> {nombre_proceso}] <<<")
    resultado = subprocess.run(
        ["taskkill", "/F", "/IM", nombre_proceso, "/T"],
        capture_output=True,
        text=True
    )
    if resultado.returncode == 0:
        return f"El proceso {nombre_proceso} se cerró correctamente."
    return f"No se encontró o no se pudo cerrar {nombre_proceso}."

def obtener_estado_pc() -> str:
    """Obtiene la hora actual, fecha, uso de CPU, memoria RAM y porcentaje de batería del computador."""
    ahora = datetime.now().strftime("%H:%M del %d/%m/%Y")
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    bateria = psutil.sensors_battery()
    info_bateria = f"{bateria.percent}% ({'conectado' if bateria.power_plugged else 'Con batería'})" if bateria else "PC de escritorio (sin batería)"
    
    return f"Fecha y hora: {ahora}. Uso de CPU: {cpu}%. Uso de RAM: {ram}%. Batería: {info_bateria}."

def mirar_pantalla(pregunta: str) -> str:
    """Toma una captura de pantalla en tiempo real para ver qué está haciendo el usuario y responder preguntas visuales.
    Úsala siempre que el usuario diga 'mira mi pantalla', 'qué ves aquí', 'ayúdame con este error', etc.
    
    Args:
        pregunta: Qué es lo que el usuario quiere saber o analizar de su pantalla.
    """
    print(">>> [SISTEMA: Capturando y analizando tu pantalla...] <<<")
    try:
        captura = ImageGrab.grab()
        respuesta_visual = client.models.generate_content(
            model=MODELO,
            contents=[
                captura,
                f"Eres los ojos de Jarvis. Describe o responde de forma concisa a lo siguiente viendo la pantalla del usuario: {pregunta}"
            ]
        )
        return respuesta_visual.text
    except Exception as e:
        return f"Error al capturar la pantalla: {str(e)}"

# Lista de herramientas disponibles para Gemini
mis_herramientas = [
    abrir_pagina_web,
    abrir_aplicacion,
    cerrar_aplicacion,
    obtener_estado_pc,
    mirar_pantalla
]

# ==========================================
# 4. EL CEREBRO (Sesión de Chat con Memoria y Tools)
# ==========================================
instrucciones = """Eres Jarvis, el asistente personal de voz en el computador de Josué.
REGLA 1: Tus respuestas serán leídas en voz alta, así que sé MUY conciso, natural y directo (máximo 2 o 3 oraciones). No uses listas largas ni bloques de código.
REGLA 2: Tienes herramientas conectadas para abrir páginas web, abrir programas, cerrar programas, ver el estado/hora del PC y mirar la pantalla de Josué. Úsalas siempre que te lo pida.
REGLA 3: Nunca intentes borrar archivos del sistema operativo ni ejecutar acciones destructivas."""

chat = client.chats.create(
    model=MODELO,
    config=types.GenerateContentConfig(
        system_instruction=instrucciones,
        tools=mis_herramientas,
        temperature=0.7,
    )
)

def pensar(texto_usuario: str) -> str:
    print("[Pensando...]")
    try:
        respuesta = chat.send_message(texto_usuario)
        return respuesta.text
    except Exception as e:
        print(f"[Error en Gemini API: {e}]")
        return "Tuve un problema al conectarme con mis servidores, Josué."

# ==========================================
# 5. LOS OÍDOS Y FLUJO ESTILO SIRI / OK GOOGLE
# ==========================================
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8  # Detecta el final de tu frase más rápido

def escuchar_microfono(timeout=3, phrase_limit=8):
    with sr.Microphone() as source:
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            # es-CL o es-ES funcionan excelente con el motor de Google
            texto = recognizer.recognize_google(audio, language="es-CL").lower()
            return texto
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except Exception as e:
            print(f"[Error de micrófono: {e}]")
            return None

# Calibración inicial de ruido ambiente
print("[Calibrando ruido de fondo por 1 segundo...]")
with sr.Microphone() as source:
    recognizer.adjust_for_ambient_noise(source, duration=1)

hablar("Sistemas activados y conectados a Gemini. Estoy listo, Josué.")
print("\n[Modo Guardia: Di 'Jarvis' seguido de tu comando, o solo 'Jarvis']")

modo_conversacion = False

while True:
    if not modo_conversacion:
        # Escucha corta esperando la palabra clave "jarvis"
        texto_escuchado = escuchar_microfono(timeout=2, phrase_limit=6)
        if not texto_escuchado or "jarvis" not in texto_escuchado:
            continue

        winsound.Beep(1000, 180)
        # Extraemos lo que dijiste después de "jarvis" por si hablaste de corrido
        comando = texto_escuchado.split("jarvis", 1)[1].strip()

        if not comando:
            print("\n[¡Despierto! Te escucho...]")
            comando = escuchar_microfono(timeout=5, phrase_limit=12)
            if not comando:
                print("[No escuché ningún comando. Volviendo a modo guardia...]")
                continue
        
        modo_conversacion = True
    else:
        # En modo conversación continua, no hace falta decir "Jarvis" otra vez
        print("\n[Modo Conversación Activo (5s): Sigue hablando o guarda silencio para dormir...]")
        comando = escuchar_microfono(timeout=5, phrase_limit=12)
        if not comando:
            winsound.Beep(600, 150)  # Tono grave indicando que vuelve a dormir
            print("[Volviendo a Modo Guardia. Di 'Jarvis' cuando me necesites]")
            modo_conversacion = False
            continue

    print(f"Josué: {comando}")

    # Comandos para descansar o apagar
    if any(palabra in comando for palabra in ["apagar sistema", "cierra el asistente", "desconéctate"]):
        hablar("Apagando todos los sistemas. ¡Hasta luego, Josué!")
        break

    if any(palabra in comando for palabra in ["gracias", "eso es todo", "descansa", "duerme"]):
        hablar("Para servirte, Josué.")
        modo_conversacion = False
        continue

    # Procesamos con Gemini (él mismo ejecuta las funciones si hace falta)
    respuesta_ia = pensar(comando)
    hablar(respuesta_ia)

pygame.mixer.quit()