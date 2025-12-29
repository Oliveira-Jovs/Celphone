import uvicorn
import webbrowser
import threading
import time
import os
import sys
import main  

def start_api():
    uvicorn.run(main.app, host="127.0.0.1", port=5000, reload=False)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else None

    thread = threading.Thread(target=start_api, daemon=True)
    thread.start()

    time.sleep(3)  
    webbrowser.open("http://127.0.0.1:5000")

    print(">> Servidor iniciado. Não feche esta janela!")
    print(">> Acesse: http://127.0.0.1:5000")

    while True:
        time.sleep(1)
