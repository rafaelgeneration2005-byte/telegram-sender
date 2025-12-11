# app.py
import streamlit as st
import asyncio
from telethon import TelegramClient
from telethon.sessions import MemorySession
import time
import json
import io
from datetime import datetime

# ---------------- CONFIG ----------------
api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender — Private", layout="centered")

# ---------------- LOOP STREAMLIT ----------------
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.loop)
loop = st.session_state.loop

# ---------------- USERS (read from users.json) ----------------
USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

users_db = load_users()

# ---------------- CLIENT (MemorySession) ----------------
if "client" not in st.session_state:
    st.session_state.client = TelegramClient(
        MemorySession(), api_id, api_hash, loop=loop
    )
    loop.run_until_complete(st.session_state.client.connect())
client = st.session_state.client

# ---------------- SESSION defaults ----------------
defaults = {
    "stage": "login",
    "user_id": None,
    "attempts": 0,
    "authorized_phone": None,
    "stop_flood": False
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- UI: Login ----------------
st.title("🔒 Login — Telegram Sender (Privado)")

def verify_credentials(uid, pwd):
    user = users_db.get(uid)
    if not user:
        return False, "Usuário não encontrado."
    if not user.get("active", True):
        return False, "Conta inativa."
    exp = user.get("expires")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp)
            if datetime.utcnow() > exp_dt:
                return False, "Acesso expirado."
        except:
            pass
    if user.get("password") != pwd:
        return False, "Senha incorreta."
    return True, None

if st.session_state.stage == "login":
    st.subheader("Acesse com seu ID e senha")
    uid = st.text_input("ID do cliente")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        ok, msg = verify_credentials(uid, pwd)
        if not ok:
            st.error(msg)
        else:
            st.success("Login OK.")
            st.session_state.user_id = uid
            st.session_state.authorized_phone = users_db[uid]["phone"]
            st.session_state.stage = "phone"
            st.rerun()

# ---------------- PHONE ----------------
if st.session_state.stage == "phone":
    st.subheader("1️⃣ Confirme seu telefone cadastrado")
    number = st.session_state.authorized_phone

    st.text(f"Número autorizado: {number}")

    if st.button("Enviar código SMS"):
        async def do_send():
            return await client.send_code_request(number)

        try:
            res = loop.run_until_complete(do_send())
            st.session_state.phone_hash = res.phone_code_hash
            st.session_state.stage = "code"
            st.success("Código enviado!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao enviar: {e}")

# ---------------- CODE ----------------
if st.session_state.stage == "code":
    st.subheader("2️⃣ Digite o código")
    code = st.text_input("Código")

    if st.button("Validar código"):
        async def do_login():
            return await client.sign_in(
                st.session_state.authorized_phone,
                code,
                phone_code_hash=st.session_state.phone_hash
            )
        try:
            loop.run_until_complete(do_login())
            st.session_state.stage = "logged"
            st.rerun()
        except Exception as e:
            if "password" in str(e).lower():
                st.session_state.stage = "2fa"
                st.rerun()
            st.error(f"Erro: {e}")

# ---------------- 2FA ----------------
if st.session_state.stage == "2fa":
    st.subheader("🔐 Senha 2FA")
    pwd = st.text_input("Senha 2FA", type="password")

    if st.button("Entrar"):
        async def do_pass():
            return await client.sign_in(password=pwd)
        try:
            loop.run_until_complete(do_pass())
            st.session_state.stage = "logged"
            st.rerun()
        except Exception as e:
            st.error(f"Erro 2FA: {e}")

# ---------------- LOGGED ----------------
if st.session_state.stage == "logged":

    # --- botão sair
    if st.button("🔒 Sair"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.stage = "login"
        st.rerun()

    st.success("Logado!")
    st.subheader("Escolha o grupo/canal")

    if st.session_state.get("groups") is None:
        async def load_groups():
            dialogs = await client.get_dialogs()
            arr = []
            for d in dialogs:
                if d.is_group or d.is_channel:
                    title = getattr(d.entity, "title", "")
                    arr.append((d.entity.id, title, d))
            return arr
        try:
            st.session_state.groups = loop.run_until_complete(load_groups())
        except Exception as e:
            st.error(f"Erro carregando grupos: {e}")
            st.session_state.groups = []

    options = [
        f"{title} — ID {gid}"
        for gid, title, _ in st.session_state.groups
    ]

    if options:
        sel = st.selectbox("Selecione o grupo", options)
        idx = options.index(sel)
        gid, title, dialog_data = st.session_state.groups[idx]

        # preview foto
        col1, col2 = st.columns([1,3])
        with col1:
            try:
                bio = io.BytesIO()
                loop.run_until_complete(
                    client.download_profile_photo(dialog_data.entity, file=bio)
                )
                bio.seek(0)
                st.image(bio.read(), caption=title)
            except:
                st.write("(sem foto)")

        with col2:
            st.write(f"**{title}**")
            st.write(f"ID: `{gid}`")

        msg = st.text_area("Mensagem a enviar", height=120)

        attempts_pl = st.empty()
        ping_pl = st.empty()
        status_pl = st.empty()
        attempts_pl.info(f"Tentativas: {st.session_state.attempts}")

        # botão cancelar
        if st.button("❌ Cancelar envio"):
            st.session_state.stop_flood = True
            status_pl.warning("Envio cancelado pelo usuário.")

        # botão enviar
        if st.button("🚀 ENVIAR EM LOOP"):
            st.session_state.stop_flood = False

            async def flood():
                st.session_state.attempts = 0
                attempts_pl.info(f"Tentativas: {st.session_state.attempts}")

                while True:
                    if st.session_state.stop_flood:
                        return None

                    try:
                        st.session_state.attempts += 1
                        attempts_pl.info(f"Tentativas: {st.session_state.attempts}")

                        t0 = time.perf_counter()
                        await client.send_message(int(gid), msg)
                        ping = (time.perf_counter() - t0) * 1000
                        return ping

                    except:
                        status_pl.warning("Grupo fechado. Tentando...")
                        await asyncio.sleep(0.03)

            ping = loop.run_until_complete(flood())

            if ping is None:
                status_pl.info("❌ Envio cancelado.")
            else:
                status_pl.success("Mensagem enviada!")
                ping_pl.info(f"⏱️ Ping: {ping:.2f} ms")

    else:
        st.warning("Nenhum grupo encontrado.")
