import aiohttp
import asyncio
import re
from aiohttp import web
import aiofiles

async def iniciar_sesion():
    """
    Función para iniciar sesión y mantener la sesión activa
    """
    config = {
        'usuario': 'fds',
        'password': 'Stvz1234',
        'url_login': 'https://medisan.sld.cu/index.php/san/login/signIn'
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

async def descargar_archivo(request):
    """
    Maneja las solicitudes para descargar archivos
    """
    session = request.app['session']
    path = request.path
    
    # Construir la URL completa con query parameters
    url_archivo = f"https://medisan.sld.cu{path}"
    
    # Agregar query parameters si existen
    if request.query_string:
        url_archivo += f"?{request.query_string}"
    
    print(f"📥 Solicitando descarga: {url_archivo}")
    
    try:
        # Hacer la solicitud al servidor remoto con la sesión activa
        async with session.get(url_archivo, ssl=False) as response:
            if response.status == 200:
                # Obtener el nombre del archivo desde los headers o la URL
                content_disposition = response.headers.get('Content-Disposition', '')
                if 'filename=' in content_disposition:
                    nombre_archivo = content_disposition.split('filename=')[1].strip('"')
                else:
                    # Extraer nombre del archivo de los parámetros o la URL
                    submission_file_id = request.query.get('submissionFileId', 'archivo')
                    nombre_archivo = f"file_{submission_file_id}"
                
                # Obtener el tipo de contenido
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                
                # Crear respuesta para forzar descarga
                resp = web.StreamResponse()
                resp.headers['Content-Type'] = content_type
                resp.headers['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
                resp.headers['Cache-Control'] = 'no-cache'
                
                await resp.prepare(request)
                
                # Stream del archivo
                async for chunk in response.content.iter_chunked(8192):
                    await resp.write(chunk)
                
                await resp.write_eof()
                return resp
            else:
                return web.Response(text=f"Error al obtener el archivo: {response.status}", status=response.status)
                
    except Exception as e:
        return web.Response(text=f"Error: {str(e)}", status=500)

async def manejar_subida(request):
    """
    Maneja la subida de archivos
    """
    session = request.app['session']
    
    if request.method == 'POST':
        data = await request.post()
        
        # Obtener el archivo del formulario
        archivo = data['file']
        nombre_archivo = archivo.filename
        
        # Leer el contenido del archivo
        file_content = archivo.file.read()
        
        # Obtener token CSRF para la subida
        async with session.get('https://medisan.sld.cu/index.php/san/login/signIn', ssl=False) as response:
            html = await response.text()
            match = re.search(r'name="csrfToken"\s+value="([^"]+)"', html)
            csrf_token = match.group(1) if match else ""
        
        # Preparar FormData para la subida
        payload = aiohttp.FormData()
        payload.add_field('fileStage', '2')
        payload.add_field('name[es_ES]', nombre_archivo)
        payload.add_field('file', file_content, filename=nombre_archivo, content_type='text/x-python')
        
        headers_subida = {
            "X-CSRF-Token": csrf_token
        }
        
        # Subir el archivo
        url_subida = 'https://medisan.sld.cu/index.php/san/api/v1/submissions/5474/files'
        async with session.post(url_subida, data=payload, headers=headers_subida, ssl=False) as response:
            if response.status == 200:
                return web.Response(text="✅ Archivo subido exitosamente")
            else:
                error_text = await response.text()
                return web.Response(text=f"❌ Error en la subida: {error_text}", status=400)
    
    # Mostrar formulario de subida para GET
    html_form = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subir Archivo</title>
    </head>
    <body>
        <h2>Subir Archivo a Medisan</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Subir Archivo</button>
        </form>
    </body>
    </html>
    """
    return web.Response(text=html_form, content_type='text/html')

async def pagina_principal(request):
    """
    Página principal del servidor
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Servidor Medisan</title>
    </head>
    <body>
        <h1>Servidor Local Medisan</h1>
        <p>Servidor funcionando correctamente</p>
        <ul>
            <li><a href="/upload">Subir archivo</a></li>
            <li><a href="/index.php/san/$$$call$$$/api/file/file-api/download-file?submissionFileId=30998&submissionId=5474&stageId=1">Descargar archivo ejemplo</a></li>
        </ul>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def iniciar_servidor():
    """
    Inicia el servidor local
    """
    # Iniciar sesión primero
    session = await iniciar_sesion()
    if not session:
        print("❌ No se pudo iniciar sesión, cerrando...")
        return
    
    # Crear aplicación web
    app = web.Application()
    app['session'] = session
    
    # Configurar rutas
    app.router.add_get('/', pagina_principal)
    app.router.add_get('/upload', manejar_subida)
    app.router.add_post('/upload', manejar_subida)
    app.router.add_get('/{path:.*}', descargar_archivo)
    
    # Configurar el runner
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Configurar el sitio
    site = web.TCPSite(runner, '127.0.0.7', 8080)
    
    print("🚀 Servidor iniciado en http://127.0.0.7:8080")
    print("📥 Los archivos se descargarán automáticamente")
    print("💡 Ejemplo: http://127.0.0.7:8080/index.php/san/$$$call$$$/api/file/file-api/download-file?submissionFileId=30998&submissionId=5474&stageId=1")
    
    await site.start()
    
    # Mantener el servidor corriendo
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor...")
    finally:
        await session.close()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(iniciar_servidor())
    except KeyboardInterrupt:
        print("\n👋 Servidor cerrado")