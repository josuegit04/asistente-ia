import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import winsound
import os
import webbrowser
import time
import re
from groq import Groq

# 1. API https://console.groq.com/keys
API_KEY = "api key"
client = Groq(api_key=API_KEY)

# 2. La Boca
def hablar(texto):
    # Limpiamos las etiquetas de acción
    texto_para_leer = re.sub(r'\[.*?\]', '', texto)
    texto_limpio = texto_para_leer.replace('*', '').replace('"', '').replace('#', '').strip()
    
    if not texto_limpio:
        return

    print(f"Jarvis: {texto_limpio}")
    
    # Cortamos el texto por puntos para procesarlo rapidísimo (al cambiar la voz se demora en descargarla y enviarla)
    oraciones = texto_limpio.split('.')
    
    # Prendemos la tarjeta de sonido SOLO cuando va a hablar
    pygame.mixer.init()
    
    for i, oracion in enumerate(oraciones):
        oracion = oracion.strip()
        if len(oracion) > 2: # Si la oración tiene más de 2 letras
            archivo_audio = f"voz_{i}_{int(time.time())}.mp3"
            
            # Generamos el audio de este pequeño fragmento
            async def crear_audio():
                comunicacion = edge_tts.Communicate(oracion, "es-MX-JorgeNeural", rate="+15%")
                await comunicacion.save(archivo_audio)
            
            asyncio.run(crear_audio())
            
            # Lo reproducimos al instante
            pygame.mixer.music.load(archivo_audio)
            pygame.mixer.music.play()
            
            # Esperamos a que termine esta oración
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # Liberamos el archivo
            pygame.mixer.music.unload()
            try:
                os.remove(archivo_audio)
            except:
                pass
                
    # Apagamos la tarjeta de sonido para liberar recursos y el micrófono
    pygame.mixer.quit()

# 3. Los Oídos
recognizer = sr.Recognizer()
recognizer.energy_threshold = 400
recognizer.dynamic_energy_threshold = False

# 4. El Cerebro (ajustar reglas segun necesidades)
instrucciones = """Eres Jarvis, el asistente de Josué.
REGLA 1: Tus respuestas deben ser MUY cortas y conversacionales. Máximo 2 o 3 oraciones.
REGLA 2: Para controlar la PC, deduce lo que Josué quiere y usa UNA de estas etiquetas al final de tu respuesta:
- Para abrir páginas web: [WEB: url_completa] (ej: [WEB: https://www.netflix.com])
- Para abrir aplicaciones: [APP: nombre_ejecutable] (ej: [APP: calc], [APP: notepad], [APP: chrome])
- Para cerrar aplicaciones: [CERRAR: nombre_proceso.exe] (ej: [CERRAR: chrome.exe], [CERRAR: calc.exe])
REGLA 3: Si te pide borrar archivos del sistema operativo, niégate."""

historial = [{"role": "system", "content": instrucciones}]

def pensar(texto_usuario):
    print("[Pensando...]")
    historial.append({"role": "user", "content": texto_usuario})
    
    respuesta = client.chat.completions.create(
        messages=historial,
        model="llama-3.3-70b-versatile",
    )
    
    texto_respuesta = respuesta.choices[0].message.content
    historial.append({"role": "assistant", "content": texto_respuesta})
    return texto_respuesta

# 5. Las Manos 
def ejecutar_accion(texto_ia):
    if "[WEB:" in texto_ia:
        url = texto_ia.split("[WEB:")[1].split("]")[0].strip()
        print(f">>> [SISTEMA: Abriendo página -> {url}] <<<")
        webbrowser.open(url)
        
    if "[APP:" in texto_ia:
        app = texto_ia.split("[APP:")[1].split("]")[0].strip()
        print(f">>> [SISTEMA: Abriendo aplicación -> {app}] <<<")
        os.system(f"start {app}")
        
    if "[CERRAR:" in texto_ia:
        proceso = texto_ia.split("[CERRAR:")[1].split("]")[0].strip()
        print(f">>> [SISTEMA: Cerrando proceso -> {proceso}] <<<")
        os.system(f"taskkill /F /IM {proceso} /T")

# 6. Codigo Principal
hablar("Sistemas Activados.")
print("\n[Modo Guardia: Activo. Di 'Jarvis' para despertarme]")

while True:
    try:
        with sr.Microphone() as source:
            audio_guardia = recognizer.listen(source, timeout=2, phrase_time_limit=3)
        texto_guardia = recognizer.recognize_google(audio_guardia, language="es-ES").lower()
        
        if "jarvis" in texto_guardia:
            winsound.Beep(1000, 200)
            print("\n[¡Despierto! Te escucho...]")
            
            with sr.Microphone() as source:
                audio_comando = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            comando = recognizer.recognize_google(audio_comando, language="es-ES").lower()
            print(f"Josué: {comando}")
            
            if "apagar" in comando or "salir" in comando:
                hablar("Apagando el sistema. ¡Nos vemos!")
                break
            
            respuesta_ia = pensar(comando)
            hablar(respuesta_ia)
            ejecutar_accion(respuesta_ia)
            
            print("\n[Volviendo a dormir... Di 'Jarvis' para despertarme]")
            
    except sr.WaitTimeoutError:
        pass
    except sr.UnknownValueError:
        pass
    except Exception as e:
        pass