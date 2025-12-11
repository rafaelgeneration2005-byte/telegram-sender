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
    st.session_state.client = TelegramClient(MemorySession(), api_id, api_hash, loop=loop)
    loop.run_until_complete(st.session_state.client.connect())
client = st.session_state.client

# ---------------- SESSION defaults ----------------
defaults = {
    "stage": "login",
    "user_id": None,
    "attempts": 0,
    "attempts_display": "",
}
for k, v in defaults.items():
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
            st.session_state.user_id = uid
            user = users_db.get(uid)
            st.session_state.authorized_phone = user.get("phone")
            st.session_state.stage = "phone"
            st.rerun()

# ---------------- UI: Phone stage ----------------
if st.session_state.stage == "phone":
    st.subheader("1️⃣ Confirme seu telefone cadastrado")
    authorized = st.session_state.authorized_phone
    st.text(f"Número autorizado: {authorized}")

    if st.button("Enviar código SMS para o número cadastrado"):
        async def do_send():
            return await client.send_code_request(authorized)
        try:
            res = loop.run_until_complete(do_send())
            st.session_state.phone_hash = res.phone_code_hash
            st.session_state.stage = "code"
            st.success("Código enviado! Verifique o Telegram.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao enviar código: {e}")

# ---------------- UI: Code stage ----------------
if st.session_state.stage == "code":
    st.subheader("2️⃣ Digite o código recebido")

    code = st.text_input("Código (ex: 12345)")
    if st.button("Confirmar código"):
        async def do_sign():
            return await client.sign_in(
                st.session_state.authorized_phone, 
                code, 
                phone_code_hash=st.session_state.phone_hash
            )
        try:
            loop.run_until_complete(do_sign())
            st.session_state.stage = "logged"
            st.rerun()
        except Exception as e:
            if "password" in str(e).lower():
                st.session_state.stage = "need_2fa"
                st.rerun()
            else:
                st.error(f"Erro: {e}")

# ---------------- UI: 2FA ----------------
if st.session_state.stage == "need_2fa":
    st.subheader("🔐 Informe sua senha 2FA")
    pwd2 = st.text_input("Senha 2FA", type="password")
    if st.button("Confirmar 2FA"):
        async def do_pass():
            return await client.sign_in(password=pwd2)
        try:
            loop.run_until_complete(do_pass())
            st.session_state.stage = "logged"
            st.rerun()
        except Exception as e:
            st.error(f"Erro 2FA: {e}")

# ---------------- UI: LOGGED ----------------
if st.session_state.stage == "logged":
    st.success("✅ Acesso autorizado.")

    st.subheader("Selecione o grupo/canal")

    if st.session_state.get("groups") is None:
        async def load_groups():
            dialogs = await client.get_dialogs()
            arr = []
            for d in dialogs:
                if getattr(d, "is_group", False) or getattr(d, "is_channel", False):
                    title = getattr(d.entity, "title", "") or str(d.id)
                    arr.append((d.entity.id, title, d))
            return arr
        try:
            arr = loop.run_until_complete(load_groups())
            st.session_state.groups = arr
        except Exception as e:
            st.error(f"Erro ao carregar grupos: {e}")
            st.session_state.groups = []

    options = [f"{title} (ID: {gid})" for gid, title, _ in st.session_state.groups]

    if options:
        sel = st.selectbox("Escolha:", options)
        idx = options.index(sel)
        gid, title, dialog_obj = st.session_state.groups[idx]

        preview_col, info_col = st.columns([1, 3])
        with preview_col:
            try:
                bio = io.BytesIO()
                loop.run_until_complete(client.download_profile_photo(dialog_obj.entity, file=bio))
                bio.seek(0)
                st.image(bio.read(), caption=title, use_column_width=True)
            except:
                st.write("🖼️ (sem foto)")

        with info_col:
            st.markdown(f"**{title}**")
            st.markdown(f"ID: `{gid}`")

        msg = st.text_area("Mensagem:", height=120)

        attempts_pl = st.empty()
        ping_pl = st.empty()
        status_pl = st.empty()

        attempts_pl.info(f"Tentativas: {st.session_state.attempts}")

        if st.button("🚀 ENVIAR EM LOOP ATÉ ABRIR"):
            if not msg:
                st.error("Digite a mensagem.")
            else:
                async def flood_run():
                    st.session_state.attempts = 0
                    attempts_pl.info(f"Tentativas: {st.session_state.attempts}")
                    while True:
                        try:
                            st.session_state.attempts += 1
                            attempts_pl.info(f"Tentativas: {st.session_state.attempts}")
                            t0 = time.perf_counter()
                            await client.send_message(int(gid), msg)
                            return (time.perf_counter() - t0) * 1000
                        except:
                            status_pl.warning("Grupo fechado. Tentando...")
                            await asyncio.sleep(0.03)

                try:
                    ping = loop.run_until_complete(flood_run())
                    status_pl.success("Mensagem enviada!")
                    ping_pl.info(f"⏱️ Ping: {ping:.2f} ms")
                except Exception as e:
                    status_pl.error(f"Erro: {e}")
    else:
        st.info("Nenhum grupo encontrado.")
