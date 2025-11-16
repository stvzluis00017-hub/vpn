import aiohttp
import asyncio
import re
import os
import time
import math

class ProgressBar:
    """
    Barra de progreso personalizada con velocidad en tiempo real
    """
    def __init__(self, total_chunks, total_bytes_estimate=0):
        self.total_chunks = total_chunks
        self.total_bytes = total_bytes_estimate
        self.completed_chunks = 0
        self.completed_bytes = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_bytes = 0
        
    def update(self, chunk_bytes=0, chunk_completed=True):
        """Actualiza el progreso"""
        self.completed_bytes += chunk_bytes
        if chunk_completed:
            self.completed_chunks += 1
        
    def get_speed(self):
        """Calcula la velocidad actual en bytes/segundo"""
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        if elapsed < 0.1:  # Evitar divisiones por cero
            return 0
            
        bytes_since_last = self.completed_bytes - self.last_bytes
        speed = bytes_since_last / elapsed
        
        self.last_update_time = current_time
        self.last_bytes = self.completed_bytes
        
        return speed
    
    def format_bytes(self, bytes_size):
        """Formatea bytes a formato legible"""
        if bytes_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = int(math.floor(math.log(bytes_size, 1024)))
        p = math.pow(1024, i)
        s = round(bytes_size / p, 2)
        return f"{s:.2f} {size_names[i]}"
    
    def format_speed(self, speed):
        """Formatea velocidad a formato legible"""
        return self.format_bytes(speed) + "/s"
    
    def get_elapsed_time(self):
        """Obtiene el tiempo transcurrido formateado"""
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_eta(self):
        """Calcula el tiempo estimado restante"""
        if self.completed_bytes == 0 or self.total_bytes == 0:
            return "--:--"
            
        elapsed = time.time() - self.start_time
        bytes_per_second = self.completed_bytes / elapsed
        remaining_bytes = self.total_bytes - self.completed_bytes
        
        if bytes_per_second > 0:
            remaining_seconds = remaining_bytes / bytes_per_second
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            seconds = int(remaining_seconds % 60)
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        else:
            return "--:--"
    
    def display(self, current_chunk=None, status="📥"):
        """Muestra la barra de progreso actualizada"""
        percentage = (self.completed_chunks / self.total_chunks) * 100 if self.total_chunks > 0 else 0
        
        # Barra de progreso visual (20 caracteres)
        bar_length = 20
        filled_length = int(bar_length * self.completed_chunks // self.total_chunks)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Información de chunks
        chunks_info = f"{self.completed_chunks}/{self.total_chunks}"
        
        # Información de bytes
        bytes_info = self.format_bytes(self.completed_bytes)
        if self.total_bytes > 0:
            bytes_info += f"/{self.format_bytes(self.total_bytes)}"
        
        # Velocidad actual
        current_speed = self.get_speed()
        speed_info = self.format_speed(current_speed)
        
        # Tiempo transcurrido y ETA
        time_info = f"{self.get_elapsed_time()} | ETA: {self.get_eta()}"
        
        # Estado actual
        if current_chunk:
            chunk_status = f"Chunk {current_chunk}/{self.total_chunks}"
        else:
            chunk_status = f"Chunk {self.completed_chunks}/{self.total_chunks}"
        
        # Construir línea de progreso
        progress_line = f"\r{status} {chunk_status} |{bar}| {percentage:5.1f}% "
        progress_line += f"| {bytes_info} | {speed_info:>12} | {time_info}"
        
        print(progress_line, end="", flush=True)
    
    def finish(self):
        """Finaliza la barra de progreso"""
        print()  # Nueva línea al final

async def iniciar_sesion():
    """
    Función para iniciar sesión y mantener la sesión activa
    """
    config = {
        'usuario': 'stvzcuba',
        'password': 'Stvz1234',
        'url_login': 'https://innovacion.ciget.lastunas.cu/index.php/innovatec/login/signIn'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    session = aiohttp.ClientSession(headers=headers)
    
    # Obtener token CSRF y hacer login
    async with session.get(config['url_login'], ssl=False) as response:
        html = await response.text()
        match = re.search(r'name="csrfToken"\s+value="([^"]+)"', html)
        csrf_token = match.group(1) if match else None
        
        if not csrf_token:
            print("❌ No se encontró token CSRF")
            return None
    
    login_data = {
        "username": config['usuario'],
        "password": config['password'], 
        "csrfToken": csrf_token,
        "remember": 1,
        "source": ""
    }
    
    async with session.post(config['url_login'], data=login_data, ssl=False) as response:
        if response.status != 200:
            print("❌ Error en login")
            return None
    
    print("✅ Sesión iniciada correctamente")
    return session

def extraer_chunk_original(contenido_png):
    """
    Extrae el chunk original del PNG fuso usando el mismo formato que se usó para crearlo
    """
    # Los bytes exactos que añadiste al crear el PNG falso
    png_header = b'\x89PNG\r\n\x1a\n'
    ihdr_chunk = b'\x00\x00\x00\x0dIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    iend_chunk = b'\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # Verificar que empiece con el header PNG
    if not contenido_png.startswith(png_header):
        print("❌ No es un PNG válido")
        return contenido_png
    
    # Buscar el inicio del IHDR chunk
    ihdr_start = len(png_header)
    
    # Verificar que sigue con el IHDR chunk
    if contenido_png[ihdr_start:ihdr_start + len(ihdr_chunk)] != ihdr_chunk:
        print("❌ Estructura IHDR no coincide")
        return contenido_png
    
    # El chunk original está entre el IHDR y el IEND
    inicio_chunk_original = ihdr_start + len(ihdr_chunk)
    
    # Buscar el IEND chunk al final
    iend_start = contenido_png.find(iend_chunk)
    if iend_start == -1:
        print("❌ No se encontró el chunk IEND")
        return contenido_png
    
    # Extraer el chunk original (todo entre IHDR e IEND)
    chunk_original = contenido_png[inicio_chunk_original:iend_start]
    
    return chunk_original

async def descargar_chunk_con_progreso(session, enlace, progress_bar, chunk_num):
    """
    Descarga un chunk mostrando progreso en tiempo real
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"
    }
    try:
        # Iniciar descarga
        async with session.get(enlace, ssl=False, headers=headers) as response:
            if response.status == 200:
                # Obtener tamaño del contenido si está disponible
                content_length = response.headers.get('Content-Length')
                total_size = int(content_length) if content_length else 0
                
                # Descargar en chunks pequeños para mostrar progreso
                chunk_data = b''
                downloaded = 0
                
                async for data_chunk in response.content.iter_chunked(8192):  # 8KB chunks
                    chunk_data += data_chunk
                    downloaded += len(data_chunk)
                    
                    # Actualizar progreso en tiempo real
                    progress_bar.update(len(data_chunk), chunk_completed=False)
                    progress_bar.display(current_chunk=chunk_num, status="📥")
                
                # Procesar el chunk completo
                chunk_original = extraer_chunk_original(chunk_data)
                
                # Actualizar progreso final del chunk
                progress_bar.update(len(chunk_original), chunk_completed=True)
                progress_bar.display(current_chunk=chunk_num, status="✅")
                
                return chunk_original, len(chunk_original), None
            else:
                error_msg = f"Error HTTP {response.status}"
                progress_bar.update(0, chunk_completed=True)
                progress_bar.display(current_chunk=chunk_num, status="❌")
                return None, 0, error_msg
                
    except Exception as e:
        progress_bar.update(0, chunk_completed=True)
        progress_bar.display(current_chunk=chunk_num, status="❌")
        return None, 0, str(e)

async def descargar_y_procesar_chunks():
    """
    Función principal para descargar y procesar chunks con progreso en tiempo real
    """
    session = await iniciar_sesion()
    if not session:
        print("❌ No se pudo iniciar sesión")
        return
    
    # Solicitar enlaces al usuario
    print("📥 Introduce los enlaces de los chunks (uno por línea, deja una línea vacía para terminar):")
    
    enlaces = []
    while True:
        enlace = input().strip()
        if not enlace:
            break
        enlaces.append(enlace)
    
    if not enlaces:
        print("❌ No se proporcionaron enlaces")
        return
    
    # Solicitar nombre del archivo de salida
    nombre_archivo = input("📝 Introduce el nombre del archivo final (con extensión): ").strip()
    if not nombre_archivo:
        nombre_archivo = "archivo_reconstruido"
    
    print(f"\n🚀 Iniciando descarga de {len(enlaces)} chunks...")
    print("=" * 90)
    
    # Crear barra de progreso
    progress_bar = ProgressBar(total_chunks=len(enlaces))
    
    # Mostrar barra inicial
    progress_bar.display(current_chunk=1, status="🔄")
    
    # Crear archivo final
    with open(nombre_archivo, 'wb') as archivo_final:
        chunks_procesados = 0
        total_bytes = 0
        errores = []
        
        # Descargar y procesar cada chunk
        for i, enlace in enumerate(enlaces, 1):
            chunk_original, bytes_chunk, error = await descargar_chunk_con_progreso(
                session, enlace, progress_bar, i
            )
            
            if chunk_original is not None:
                # Escribir al archivo final
                archivo_final.write(chunk_original)
                archivo_final.flush()
                
                chunks_procesados += 1
                total_bytes += bytes_chunk
                
            else:
                errores.append(f"Chunk {i}: {error}")
        
        # Finalizar barra de progreso
        progress_bar.finish()
    
    # Mostrar resumen final
    print("=" * 90)
    if chunks_procesados > 0:
        tamaño_final = os.path.getsize(nombre_archivo)
        tiempo_total = progress_bar.get_elapsed_time()
        
        print(f"\n✅ DESCARGAS COMPLETADAS")
        print(f"📁 Archivo: {nombre_archivo}")
        print(f"📊 Tamaño final: {progress_bar.format_bytes(tamaño_final)}")
        print(f"🔢 Chunks exitosos: {chunks_procesados}/{len(enlaces)}")
        print(f"⏱️  Tiempo total: {tiempo_total}")
        print(f"⚡ Velocidad promedio: {progress_bar.format_speed(total_bytes / (time.time() - progress_bar.start_time))}")
        
        if errores:
            print(f"❌ Chunks con error: {len(errores)}")
            for error in errores:
                print(f"   - {error}")
        
        if tamaño_final == 0:
            print("⚠️  ADVERTENCIA: El archivo final tiene 0 bytes")
    else:
        print("❌ No se pudieron procesar chunks")
        if os.path.exists(nombre_archivo):
            os.remove(nombre_archivo)
    
    await session.close()

async def main():
    """
    Función principal
    """
    print("=" * 60)
    print("📥 DESCARGADOR Y UNIDOR DE CHUNKS - PROGRESO EN TIEMPO REAL")
    print("=" * 60)
    print("Esta herramienta:")
    print("• Descarga chunks desde enlaces proporcionados")
    print("• Elimina encabezados PNG falsos")
    print("• Une los chunks automáticamente")
    print("• Muestra velocidad y progreso en TIEMPO REAL")
    print("=" * 60)
    
    await descargar_y_procesar_chunks()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa terminado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")