import streamlit as st
import asyncio
from telethon import TelegramClient
import time

api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender", layout="centered")

# ------------------------------------------
#  CONFIGURAÇÃO DO LOOP DO TELETHON
# ------------------------------------------
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = TelegramClient("sessao_streamlit", api_id, api_hash, loop=loop)

async def ensure_connected():
    if not client.is_connected():
        await client.connect()

# ------------------------------------------
#     INICIALIZAÇÃO DAS VARIÁVEIS
# ------------------------------------------
if "phone_hash" not in st.session_state:
    st.session_state.phone_hash = None
if "phone_number" not in st.session_state:
    st.session_state.phone_number = None

# ------------------------------------------
#     INTERFACE STREAMLIT
# ------------------------------------------
st.title("🔥 Telegram Auto Sender")

# 1 — Número
phone = st.text_input("📱 Digite seu número (+55...)", value=st.session_state.phone_number or "")

if st.button("Enviar código SMS"):
    async def send_code():
        await ensure_connected()
        result = await client.send_code_request(phone)
        return result.phone_code_hash

    try:
        phone_code_hash = loop.run_until_complete(send_code())
        st.session_state.phone_hash = phone_code_hash
        st.session_state.phone_number = phone
        st.success("Código enviado com sucesso!")
    except Exception as e:
        st.error(f"Erro: {e}")

# 2 — Código
code = st.text_input("🔐 Código recebido")

if st.button("Confirmar código"):
    async def verify():
        await ensure_connected()
        return await client.sign_in(
            st.session_state.phone_number,
            code,
            phone_code_hash=st.session_state.phone_hash
        )

    try:
        loop.run_until_complete(verify())
        st.success("Login efetuado!")
    except Exception as e:
        st.error(f"Erro: {e}")

# 3 — Enviar mensagem
chat_id = st.text_input("💬 ID do grupo (ex: -10012345678)")
msg = st.text_input("💬 Mensagem para enviar")

if st.button("🚀 Mandar mensagem no modo competição"):
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
