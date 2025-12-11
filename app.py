import streamlit as st
import asyncio
from telethon import TelegramClient
from telethon.sessions import MemorySession
import time

# ---------------- CONFIG ----------------
api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender", layout="centered")

# ---------------- EVENT LOOP STREAMLIT ----------------
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.loop)

loop = st.session_state.loop

# ---------------- TELETHON CLIENT ----------------
if "client" not in st.session_state:
    st.session_state.client = TelegramClient(
        MemorySession(),   # evita erros de banco sqlite
        api_id,
        api_hash,
        loop=loop
    )
    loop.run_until_complete(st.session_state.client.connect())

client = st.session_state.client


# ---------------- STATE MACHINE ----------------
if "stage" not in st.session_state:
    st.session_state.stage = "phone"

for x in ["phone", "phone_hash", "need_2fa", "groups"]:
    if x not in st.session_state:
        st.session_state[x] = None


# ---------------- UI ----------------
st.title("🚀 Telegram Sender — Competição")


# ---------- 1) TELEFONE ----------
if st.session_state.stage == "phone":
    st.subheader("1️⃣ Digite seu número Telegram")

    number = st.text_input("Número completo (55DDD...)")

    if st.button("Enviar código SMS"):
        if not number:
            st.error("Digite o número.")
        else:
            async def do():
                return await client.send_code_request(number)

            try:
                res = loop.run_until_complete(do())
                st.session_state.phone = number
                st.session_state.phone_hash = res.phone_code_hash
                st.session_state.stage = "code"
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao enviar SMS: {e}")


# ---------- 2) CÓDIGO SMS ----------
if st.session_state.stage == "code":
    st.subheader("2️⃣ Digite o código recebido")

    code = st.text_input("Código de 5 dígitos")

    if st.button("Validar código"):
        async def do():
            return await client.sign_in(
                st.session_state.phone,
                code,
                phone_code_hash=st.session_state.phone_hash
            )

        try:
            loop.run_until_complete(do())
            st.session_state.stage = "logged"
            st.rerun()

        except Exception as e:
            if "password" in str(e).lower():
                st.session_s_
