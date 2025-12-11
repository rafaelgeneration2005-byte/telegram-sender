import streamlit as st
import asyncio
from telethon import TelegramClient
import time

api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender", layout="centered")

# ------------------------------------------
# EVENT LOOP
# ------------------------------------------
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = TelegramClient("sessao_streamlit", api_id, api_hash, loop=loop)

async def ensure_connected():
    if not client.is_connected():
        await client.connect()

# ------------------------------------------
# SESSION STATE
# ------------------------------------------
for key in ["phone", "phone_hash", "need_2fa"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ------------------------------------------
# UI
# ------------------------------------------
st.title("🔥 Telegram Auto Sender - Competição")

# 1 — NÚMERO
phone = st.text_input("📱 Digite seu número (+55...)", value=st.session_state.phone or "")

if st.button("Enviar código SMS"):
    async def send_code():
        await ensure_connected()
        result = await client.send_code_request(phone)
        return result.phone_code_hash

    try:
        h = loop.run_until_complete(send_code())
        st.session_state.phone = phone
        st.session_state.phone_hash = h
        st.success("SMS enviado! Digite o código abaixo.")
    except Exception as e:
        st.error(f"Erro: {e}")

# 2 — CÓDIGO
code = st.text_input("🔐 Código do Telegram (ex: 12345)")

if st.button("Confirmar código"):
    async def verify():
        await ensure_connected()
        return await client.sign_in(
            st.session_state.phone,
            code,
            phone_code_hash=st.session_state.phone_hash
        )

    try:
        loop.run_until_complete(verify())
        st.success("Login feito com sucesso!")
        st.session_state.need_2fa = False

    except Exception as e:
        if "password" in str(e).lower():
            st.session_state.need_2fa = True
            st.warning("Sua conta tem senha 2FA. Digite abaixo.")
        else:
            st.error(f"Erro: {e}")

# 3 — SENHA 2FA (se necessário)
if st.session_state.need_2fa:
    password = st.text_input("🔑 Senha 2FA", type="password")

    if st.button("Confirmar senha 2FA"):
        async def verify_2fa():
            await ensure_connected()
            return await client.sign_in(password=password)

        try:
            loop.run_until_complete(verify_2fa())
            st.success("Login realizado com sucesso!")
            st.session_state.need_2fa = False
        except Exception as e:
            st.error(f"Senha incorreta: {e}")


# 4 — CAMPOS DA COMPETIÇÃO
chat_id = st.text_input("💬 ID do grupo (ex: -100xxxx)")
msg = st.text_input("📨 Mensagem da competição")

if st.button("🚀 ENVIAR EM LOOP ATÉ ABRIR"):
    async def flood():
        await ensure_connected()

        while True:
            try:
                start = time.perf_counter()
                await client.send_message(int(chat_id), msg)
                ping = (time.perf_counter() - start) * 1000
                return ping
            except:
                await asyncio.sleep(0.03)

    try:
        ping = loop.run_until_complete(flood())
        st.success(f"Mensagem enviada! Ping: {ping:.2f} ms")
    except Exception as e:
        st.error(f"Erro: {e}")
