from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI()

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- PATHS ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ---------- STATIC ----------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------- FRONT ----------
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# ---------- BANCO ----------
conn = sqlite3.connect("usuarios.db", check_same_thread=False)
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

# ---------- CURSOS ----------
CURSOS = {
    1: {"nome": "ADMINISTRAÇÃO", "turnos": {"diurno": 694.62, "noturno": 689.69}},
    2: {"nome": "ARQUEOLOGIA", "turnos": {"diurno": 654.14}},
    3: {"nome": "ARQUITETURA E URBANISMO", "turnos": {"diurno": 709.08, "noturno": 689.69}},
    4: {"nome": "ARTES VISUAIS", "turnos": {"diurno": 752.63, "noturno": 708.94}},
    5: {"nome": "BIBLIOTECONOMIA", "turnos": {"diurno": 638.46}},
    6: {"nome": "BIOMEDICINA", "turnos": {"diurno": 732.65}},
    7: {"nome": "CIÊNCIA DA COMPUTAÇÃO", "turnos": {"diurno": 801.38}},
    8: {"nome": "CIÊNCIA POLÍTICA", "turnos": {"diurno": 670.18}},
    9: {"nome": "CIÊNCIAS ATUARIAIS", "turnos": {"diurno": 651.39}},
    10: {"nome": "CIÊNCIAS BIOLÓGICAS", "turnos": {"diurno": 669.43, "noturno": 660.48}},
    11: {"nome": "CIÊNCIAS BIOLÓGICAS - ÊNFASE CIÊNCIAS AMBIENTAIS", "turnos": {"diurno": 640.25}},
}

# ---------- ESTADO ----------
usuarios = {}

# ---------- MODELO ----------
class Mensagem(BaseModel):
    user_id: str
    message: str

# ---------- FUNÇÕES ----------
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
    telefone = msg.user_id
    texto = msg.message.strip().lower()

    if telefone not in usuarios:
        usuarios[telefone] = {"etapa": 0}

    u = usuarios[telefone]

    if u["etapa"] == 0:
        u["etapa"] = 1
        return {"reply": "Você concorda com o uso dos seus dados? Responda SIM."}

    if u["etapa"] == 1:
        if texto != "sim":
            return {"reply": "Sem consentimento não é possível continuar."}
        u["etapa"] = 2
        return {"reply": "Qual seu nome completo?"}

    if u["etapa"] == 2:
        u["nome"] = texto.title()
        u["etapa"] = 3
        return {"reply": "Qual seu colégio?"}

    if u["etapa"] == 3:
        u["colegio"] = texto.title()
        salvar_usuario(telefone, u["nome"], u["colegio"])
        u["etapa"] = 4
        return {"reply": "Informe sua nota do SSA1"}

    if u["etapa"] == 4:
        u["ssa1"] = float(texto)
        u["etapa"] = 5
        return {"reply": "Informe sua nota do SSA2"}

    if u["etapa"] == 5:
        u["ssa2"] = float(texto)
        u["etapa"] = 6
        return {"reply": "Qual nota você acha que vai tirar na redação?"}

    if u["etapa"] == 6:
        u["redacao"] = float(texto)
        u["etapa"] = 7
        return {"reply": f"Escolha o curso:\n\n{listar_cursos()}"}

    if u["etapa"] == 7:
        curso = CURSOS[int(texto)]
        u["curso"] = curso
        u["etapa"] = 8
        return {"reply": "Qual turno? (diurno / noturno)"}

    if u["etapa"] == 8:
        curso = u["curso"]
        nota_corte = curso["turnos"][texto]
        ssa3 = calcular_ssa3(u["ssa1"], u["ssa2"], u["redacao"], nota_corte)
        usuarios.pop(telefone)
        return {
            "reply": f"{u['nome']}, você precisa tirar {ssa3} no SSA3."
        }

    return {"reply": "Erro."}
