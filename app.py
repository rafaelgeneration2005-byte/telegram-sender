import streamlit as st
import asyncio
from telethon import TelegramClient
from telethon.sessions import MemorySession
import time

api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender", layout="centered")

# -------------------- EVENT LOOP STREAMLIT --------------------
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.loop)

loop = st.session_state.loop


# -------------------- CLIENT --------------------
if "client" not in st.session_state:
    st.session_state.client = TelegramClient(
        MemorySession(),
        api_id,
        api_hash,
        loop=loop
    )
    loop.run_until_complete(st.session_state.client.connect())

client = st.session_state.client


# -------------------- STATES --------------------
defaults = {
    "stage": "phone",
    "phone": None,
    "phone_hash": None,
    "groups": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# -------------------- UI --------------------
st.title("🚀 Telegram Sender — Competição")

log_box = st.empty()   # ← onde o log aparece


def log(msg):
    """Imprime no Streamlit ao invés do console."""
    log_box.write(f"📡 {msg}")


# -------------------- PHONE --------------------
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


# -------------------- CODE --------------------
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
                st.session_state.stage = "need_2fa"
                st.rerun()

            st.error(f"Erro: {e}")


# -------------------- 2FA --------------------
if st.session_state.stage == "need_2fa":
    st.subheader("🔐 Senha 2FA necessária")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):

        async def do():
            return await client.sign_in(password=pwd)

        try:
            loop.run_until_complete(do())
            st.session_state.stage = "logged"
            st.rerun()

        except Exception as e:
            st.error(f"Erro 2FA: {e}")


# -------------------- LOGGED --------------------
if st.session_state.stage == "logged":
    st.success("Login realizado!")

    st.subheader("📂 Selecione o grupo")

    # carregando grupos uma única vez
    if st.session_state.groups is None:

        async def load():
            dialogs = await client.get_dialogs()
            arr = []
            for d in dialogs:
                if d.is_group or d.is_channel:
                    name = getattr(d.entity, "title", "Sem nome")
                    arr.append((d.entity.id, name))
            return arr

        st.session_state.groups = loop.run_until_complete(load())

    names = [f"{title}   (ID: {gid})" for gid, title in st.session_state.groups]

    sel = st.selectbox("Escolha o grupo", names)

    idx = names.index(sel)
    gid = st.session_state.groups[idx][0]

    msg = st.text_area("Mensagem")

    status = st.empty()
    ping_box = st.empty()

    if st.button("🚀 ENVIAR EM LOOP ATÉ ABRIR"):

        async def flood():
            tentativas = 0

            while True:
                try:
                    tentativas += 1
                    status.warning(f"Tentativa #{tentativas} — grupo fechado...")

                    t0 = time.perf_counter()
                    await client.send_message(gid, msg)
                    ping = (time.perf_counter() - t0) * 1000

                    return ping

                except:
                    await asyncio.sleep(0.05)

        try:
            ping = loop.run_until_complete(flood())
            status.success("Mensagem enviada! 🎉")

            ping_box.info(f"⏱️ Ping da última tentativa: **{ping:.2f} ms**")

        except Exception as e:
            status.error(f"Erro: {e}")
