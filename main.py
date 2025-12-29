import ctypes
import time
import sys
import os
import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mutex_name = "ZapinhoLauncherMutex"
mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)  

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR, "usuarios.db")

# ---------- STATIC ----------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------- FRONT ----------
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/admin")
def admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

# ---------- BANCO ----------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telefone TEXT,
    nome TEXT,
    colegio TEXT
)
""")
conn.commit()

# ---------- API ADMIN ----------
@app.get("/api/usuarios")
def listar_usuarios():
    cursor.execute("SELECT id, telefone, nome, colegio FROM usuarios")
    rows = cursor.fetchall()
    return [
        {"id": r[0], "telefone": r[1], "nome": r[2], "colegio": r[3]}
        for r in rows
    ]

# ---------- CURSOS ----------
CURSOS = {
    1: {"nome": "ADMINISTRAÇÃO", "turnos": {"diurno": 694.62, "noturno": 689.69}},
    2: {"nome": "ARQUEOLOGIA", "turnos": {"diurno": 654.14}},
    3: {"nome": "ARQUITETURA E URBANISMO", "turnos": {"diurno": 709.08, "noturno": 689.69}},
    4: {"nome": "ARTES VISUAIS", "turnos": {"diurno": 752.63, "noturno": 708.94}},
    5: {"nome": "BIBLIOTECONOMIA", "turnos": {"diurno": 638.46}},
    6: {"nome": "BIOMEDICINA", "turnos": {"diurno": 732.65}},
    7: {"nome": "CIÊNCIA DA COMPUTAÇÃO", "turnos": {"diurno": 801.38}},
}

usuarios = {}

# ---------- MODELO ----------
class Mensagem(BaseModel):
    user_id: str
    message: str

# ---------- FUNÇÕES ----------
def is_number(valor):
    try:
        float(valor)
        return True
    except ValueError:
        return False

def salvar_usuario(telefone, nome, colegio):
    cursor.execute(
        "INSERT INTO usuarios (telefone, nome, colegio) VALUES (?, ?, ?)",
        (telefone, nome, colegio),
    )
    conn.commit()

def listar_cursos():
    return "\n".join(
        f"{i} - {c['nome']} ({' / '.join(c['turnos'].keys())})"
        for i, c in CURSOS.items()
    )

def calcular_ssa3(ssa1, ssa2, redacao, nota_corte):
    return round(
        (nota_corte - (ssa1 * 0.2) - (ssa2 * 0.3) - (redacao * 0.1)) / 0.4,
        2
    )

# ---------- CHAT ----------
@app.post("/chat")
def chat(msg: Mensagem):
    session_id = msg.user_id
    texto = msg.message.strip().lower()

    if session_id not in usuarios:
        usuarios[session_id] = {"etapa": 0}

    u = usuarios[session_id]

    if u["etapa"] == 0:
        if texto == "sim":
            u["etapa"] = 1
            return {"reply": "Consentimento registrado. Informe seu número de telefone."}
        return {"reply": "Você concorda com o uso dos seus dados? Responda SIM."}

    if u["etapa"] == 1:
        u["telefone"] = texto
        u["etapa"] = 2
        return {"reply": "Qual seu nome completo?"}

    if u["etapa"] == 2:
        u["nome"] = texto.title()
        u["etapa"] = 3
        return {"reply": "Qual seu colégio?"}

    if u["etapa"] == 3:
        u["colegio"] = texto.title()
        salvar_usuario(u["telefone"], u["nome"], u["colegio"])
        u["etapa"] = 4
        return {"reply": "Informe sua nota do SSA1"}

    if u["etapa"] == 4:
        if not is_number(texto):
            return {"reply": "Digite apenas números para a nota do SSA1."}
        u["ssa1"] = float(texto)
        u["etapa"] = 5
        return {"reply": "Informe sua nota do SSA2"}

    if u["etapa"] == 5:
        if not is_number(texto):
            return {"reply": "Digite apenas números para a nota do SSA2."}
        u["ssa2"] = float(texto)
        u["etapa"] = 6
        return {"reply": "Qual nota você acha que vai tirar na redação?"}

    if u["etapa"] == 6:
        if not is_number(texto):
            return {"reply": "Digite apenas números para a redação."}
        u["redacao"] = float(texto)
        u["etapa"] = 7
        return {"reply": f"Escolha o curso:\n\n{listar_cursos()}"}

    if u["etapa"] == 7:
        if not texto.isdigit() or int(texto) not in CURSOS:
            return {"reply": "Curso inválido. Escolha pelo número."}
        u["curso"] = CURSOS[int(texto)]
        u["etapa"] = 8
        return {"reply": f"Qual turno? ({' / '.join(u['curso']['turnos'].keys())})"}

    if u["etapa"] == 8:
        if texto not in u["curso"]["turnos"]:
            return {"reply": "Turno inválido."}
        nota_corte = u["curso"]["turnos"][texto]
        ssa3 = calcular_ssa3(u["ssa1"], u["ssa2"], u["redacao"], nota_corte)
        usuarios.pop(session_id)
        return {"reply": f"{u['nome']}, você precisa tirar {ssa3} no SSA3."}

    return {"reply": "Erro inesperado."}

LAST_ACCESS = time.time()

@app.middleware("http")
async def track_access(request, call_next):
    global LAST_ACCESS
    LAST_ACCESS = time.time()
    return await call_next(request)
