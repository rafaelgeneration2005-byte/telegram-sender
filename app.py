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
                st.session_state.stage = "need_2fa"
                st.rerun()

            st.error(f"Erro: {e}")


# ---------- 3) 2FA ----------
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


# ---------- 4) LOGADO ----------
if st.session_state.stage == "logged":
    st.success("Login realizado com sucesso! ✅")

    st.subheader("📂 Escolha o grupo ou canal")

    # Carregar grupos uma única vez
    if st.session_state.groups is None:

        async def load():
            dialogs = await client.get_dialogs()
            arr = []
            for d in dialogs:
                if d.is_group or d.is_channel:
                    title = getattr(d.entity, "title", "Sem nome")
                    arr.append((d.entity.id, title))
            return arr

        st.session_state.groups = loop.run_until_complete(load())

    names = [f"{title} (ID: {gid})" for gid, title in st.session_state.groups]
    sel = st.selectbox("Selecione o grupo", names)

    idx = names.index(sel)
    gid = st.session_state.groups[idx][0]

    msg = st.text_area("✉ Mensagem para enviar:")

    # LOGS PERSISTENTES
    if "attempts_log" not in st.session_state:
        st.session_state.attempts_log = ""

    attempts_box = st.container()
    ping_box = st.empty()
    status = st.empty()

    attempts_box.write(st.session_state.attempts_log)

    if st.button("🚀 ENVIAR EM LOOP ATÉ ABRIR"):

        async def flood():
            tentativas = 0

            while True:
                try:
                    tentativas += 1

                    st.session_state.attempts_log = (
                        f"🔄 Tentativas: {tentativas}"
                    )
                    attempts_box.write(st.session_state.attempts_log)

                    t0 = time.perf_counter()
                    await client.send_message(gid, msg)
                    ping = (time.perf_counter() - t0) * 1000

                    return tentativas, ping

                except:
                    await asyncio.sleep(0.05)

        try:
            tentativas, ping = loop.run_until_complete(flood())

            status.success("🎉 Mensagem enviada com sucesso!")

            ping_box.info(
                f"📊 **Estatísticas da entrega:**\n"
                f"- Tentativas: **{tentativas}**\n"
                f"- Ping: **{ping:.2f} ms**"
            )

        except Exception as e:
            status.error(f"Erro: {e}")
