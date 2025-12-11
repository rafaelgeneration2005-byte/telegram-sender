import streamlit as st
import asyncio
from telethon import TelegramClient
import time

api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

# Criar loop próprio (obrigatório no Streamlit)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = TelegramClient("sessao_streamlit", api_id, api_hash, loop=loop)

async def connect_client():
    if not client.is_connected():
        await client.connect()


# ------------------
#   INTERFACE
# ------------------
st.title("🔥 Telegram Auto Sender (Flood)")

phone = st.text_input("📱 Digite seu número (+55...)")

if st.button("Enviar código SMS"):
    async def send_code():
        await connect_client()
        await client.send_code_request(phone)

    try:
        loop.run_until_complete(send_code())
        st.success("Código enviado!")
    except Exception as e:
        st.error(f"Erro: {e}")


code = st.text_input("🔐 Código recebido (5 dígitos)")

if st.button("Confirmar código"):
    async def verify():
        await connect_client()
        await client.sign_in(phone, code)

    try:
        loop.run_until_complete(verify())
        st.success("Login feito com sucesso!")
    except Exception as e:
        st.error(f"Erro: {e}")


chat_id = st.text_input("💬 ID do grupo (números negativos)")
message = st.text_input("✏️ Mensagem para enviar")

if st.button("🚀 Enviar mensagem (modo competição)"):

    async def flood():
        await connect_client()

        retries = 0
        while True:
            try:
                start = time.perf_counter()
                await client.send_message(int(chat_id), message)
                ping = (time.perf_counter() - start) * 1000
                return ("OK", ping)
            except Exception:
                retries += 1
                await asyncio.sleep(0.02)

    try:
        status, ping = loop.run_until_complete(flood())
        st.success(f"Mensagem enviada! Ping: {ping:.2f}ms")
    except Exception as e:
        st.error(f"Erro: {e}")
