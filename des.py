import aiohttp
import asyncio
import re
import os
import time
import math

class ProgressBar:
    def __init__(self, total_chunks):
        self.total_chunks = total_chunks
        self.completed_chunks = 0
        self.completed_bytes = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_bytes = 0
        
    def update(self, chunk_bytes=0, chunks_completed=1):
        self.completed_bytes += chunk_bytes
        self.completed_chunks += chunks_completed
        
    def get_speed(self):
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        if elapsed < 0.1:
            return 0
            
        bytes_since_last = self.completed_bytes - self.last_bytes
        speed = bytes_since_last / elapsed
        
        self.last_update_time = current_time
        self.last_bytes = self.completed_bytes
        
        return speed
    
    def format_bytes(self, bytes_size):
        if bytes_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = int(math.floor(math.log(bytes_size, 1024)))
        p = math.pow(1024, i)
        s = round(bytes_size / p, 2)
        return f"{s:.2f} {size_names[i]}"
    
    def format_speed(self, speed):
        return self.format_bytes(speed) + "/s"
    
    def get_elapsed_time(self):
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_eta(self):
        if self.completed_chunks == 0 or self.total_chunks == 0:
            return "--:--"
            
        elapsed = time.time() - self.start_time
        chunks_per_second = self.completed_chunks / elapsed
        remaining_chunks = self.total_chunks - self.completed_chunks
        
        if chunks_per_second > 0:
            remaining_seconds = remaining_chunks / chunks_per_second
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            seconds = int(remaining_seconds % 60)
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        else:
            return "--:--"
    
    def display(self, status="📥"):
        percentage = (self.completed_chunks / self.total_chunks) * 100 if self.total_chunks > 0 else 0
        
        bar_length = 20
        filled_length = int(bar_length * self.completed_chunks // self.total_chunks)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        bytes_info = self.format_bytes(self.completed_bytes)
        
        current_speed = self.get_speed()
        speed_info = self.format_speed(current_speed)
        
        time_info = f"{self.get_elapsed_time()} | ETA: {self.get_eta()}"
        
        progress_line = f"\r{status} {self.completed_chunks}/{self.total_chunks} |{bar}| {percentage:5.1f}% "
        progress_line += f"| {bytes_info} | {speed_info:>12} | {time_info}"
        
        print(progress_line, end="", flush=True)
    
    def finish(self):
        print()

async def iniciar_sesion():
    config = {
        'usuario': 'stvzcuba',
        'password': 'Stvz1234',
        'url_login': 'https://innovacion.ciget.lastunas.cu/index.php/innovatec/login/signIn'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    session = aiohttp.ClientSession(headers=headers)
    
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

async def descargar_chunk(session, enlace, progress_bar):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"
    }
    try:
        async with session.get(enlace, ssl=False) as response:
            if response.status == 200:
                # Descargar todo el chunk de una vez
                chunk_data = await response.read()
                
                # Actualizar progreso una sola vez por chunk
                progress_bar.update(len(chunk_data), 1)
                progress_bar.display(status="✅")
                
                return chunk_data, len(chunk_data), None
            else:
                error_msg = f"Error HTTP {response.status}"
                progress_bar.update(0, 1)
                progress_bar.display(status="❌")
                return None, 0, error_msg
                
    except Exception as e:
        progress_bar.update(0, 1)
        progress_bar.display(status="❌")
        return None, 0, str(e)

async def descargar_y_procesar_chunks():
    session = await iniciar_sesion()
    if not session:
        print("❌ No se pudo iniciar sesión")
        return
    
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
    
    nombre_archivo = input("📝 Introduce el nombre del archivo final (con extensión): ").strip()
    if not nombre_archivo:
        nombre_archivo = "archivo_reconstruido"
    
    ruta_descargas = "/storage/emulated/0/Download"
    ruta_completa = os.path.join(ruta_descargas, nombre_archivo)
    
    print(f"\n🚀 Iniciando descarga de {len(enlaces)} chunks...")
    print(f"📁 Guardando en: {ruta_completa}")
    print("=" * 80)
    
    progress_bar = ProgressBar(total_chunks=len(enlaces))
    
    with open(ruta_completa, 'wb') as archivo_final:
        chunks_procesados = 0
        total_bytes = 0
        errores = []
        
        for i, enlace in enumerate(enlaces, 1):
            # Mostrar progreso antes de empezar cada chunk
            progress_bar.display(status="📥")
            
            chunk_data, bytes_chunk, error = await descargar_chunk(
                session, enlace, progress_bar
            )
            
            if chunk_data is not None:
                archivo_final.write(chunk_data)
                archivo_final.flush()
                
                chunks_procesados += 1
                total_bytes += bytes_chunk
            else:
                errores.append(f"Chunk {i}: {error}")
        
        progress_bar.finish()
    
    print("=" * 80)
    if chunks_procesados > 0:
        tamaño_final = os.path.getsize(ruta_completa)
        tiempo_total = progress_bar.get_elapsed_time()
        
        print(f"\n✅ DESCARGAS COMPLETADAS")
        print(f"📁 Archivo: {ruta_completa}")
        print(f"📊 Tamaño final: {progress_bar.format_bytes(tamaño_final)}")
        print(f"🔢 Chunks exitosos: {chunks_procesados}/{len(enlaces)}")
        print(f"⏱️  Tiempo total: {tiempo_total}")
        print(f"⚡ Velocidad promedio: {progress_bar.format_speed(total_bytes / (time.time() - progress_bar.start_time))}")
        
        if errores:
            print(f"❌ Chunks con error: {len(errores)}")
            for error in errores:
                print(f"   - {error}")
    else:
        print("❌ No se pudieron procesar chunks")
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
    
    await session.close()

async def main():
    print("=" * 60)
    print("📥 DESCARGADOR Y UNIDOR DE CHUNKS")
    print("=" * 60)
    print("• Introduce enlaces manualmente")
    print("• Guarda en carpeta de descargas del teléfono")
    print("• Muestra progreso en tiempo real")
    print("=" * 60)
    
    await descargar_y_procesar_chunks()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa terminado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
