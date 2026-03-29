import os
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("PDFLIB_HOST", "0.0.0.0")
    port_raw = os.environ.get("PDFLIB_PORT", os.environ.get("PORT", "8000"))
    try:
        port = int(port_raw)
    except Exception:
        port = 8000
    
    # Запускаем приложение из модуля server.main
    uvicorn.run("server.main:app", host=host, port=port, reload=True)