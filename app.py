import streamlit as st
import asyncio
from telethon import TelegramClient
import time

api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender", layout="centered")

# ------------------- FOR STREAMLIT -------------------
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.loop)

loop = st.session_state.loop

if "client" not in st.session_state:
    st.session_state.client = TelegramClient(
        "sessao_streamlit",
        api_id,
        api_hash,
        loop=loop
    )
    loop.run_until_complete(st.session_state.client.connect())

client = st.session_state.client


# ------------------- STATE MACHINE -------------------
if "stage" not in st.session_state:
    st.session_state.stage = "phone"

for x in ["phone", "phone_hash", "need_2fa", "groups", "selected_group_id"]:
    if x not in st.session_state:
        st.session_state[x] = None


# ------------------- UI -------------------
st.title("🚀 Telegram Sender — Competição")


# ------------------- STAGE 1: PHONE -------------------
if st.session_state.stage == "phone":
    st.subheader("1️⃣ Digite seu número Telegram")

    inp = st.text_input("Número (ex: +55DDDNUMERO)")

    if st.button("Enviar código SMS"):
        if not inp:
            st.error("Digite um número válido.")
        else:

            async def do():
                return await client.send_code_request(inp)

            try:
                res = loop.run_until_complete(do())
                st.session_state.phone = inp
                st.session_state.phone_hash = res.phone_code_hash
                st.session_state.stage = "code"
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao enviar SMS: {e}")


# ------------------- STAGE 2: CODE -------------------
if st.session_state.stage == "code":
    st.subheader("2️⃣ Digite o código recebido")

    code = st.text_input("Código (5 dígitos)")

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
            msg = str(e).lower()
            if "password" in msg or "2fa" in msg or "two-step" in msg:
                st.session_state.need_2fa = True
                st.session_state.stage = "need_2fa"
                st.rerun()
            else:
                st.error(f"Erro: {e}")


# ------------------- STAGE 3: NEED 2FA -------------------
if st.session_state.stage == "need_2fa":
    st.subheader("🔐 Sua conta possui 2FA")
    senha = st.text_input("Senha 2FA", type="password")

    if st.button("Confirmar senha"):
        async def do():
            return await client.sign_in(password=senha)

        try:
            loop.run_until_complete(do())
            st.session_state.stage = "logged"
            st.rerun()
        except Exception as e:
            st.error(f"Erro na senha 2FA: {e}")


# ------------------- STAGE 4: LOGGED -------------------
if st.session_state.stage == "logged":
    st.success("Login OK!")

    st.subheader("📂 Selecione o grupo/canal")

    # CARREGAR GRUPOS APENAS UMA VEZ
    if st.session_state.groups is None:

        async def load():
            dialogs = await client.get_dialogs()

            res = []
            for d in dialogs:
                if d.is_group or d.is_channel:
                    title = getattr(d.entity, "title", None) or str(d.id)
                    res.append((d.id, title))
            return res

        try:
            st.session_state.groups = loop.run_until_complete(load())
        except Exception as e:
            st.error(f"Erro ao carregar grupos: {e}")

    # DROPDOWN
    nomes = [f"{name} — {gid}" for gid, name in st.session_state.groups]

    sel = st.selectbox("Selecione", nomes)

    pos = nomes.index(sel)
    gid = st.session_state.groups[pos][0]

    st.session_state.selected_group_id = gid

    st.markdown("---")
    msg = st.text_area("Mensagem a enviar:")

    status = st.empty()

    if st.button("ENVIAR EM LOOP ATÉ ABRIR"):
        if not msg:
            st.error("Digite uma mensagem")
        else:

            async def flood():
                while True:
                    try:
                        start = time.perf_counter()
                        await client.send_message(gid, msg)
                        ping = (time.perf_counter() - start) * 1000
                        print(f"[PING] {ping:.2f} ms")
                        return ping
                    except:
                        status.warning("Grupo fechado... tentando novamente...")
                        await asyncio.sleep(0.05)

            try:
                p = loop.run_until_complete(flood())
                status.success("Mensagem enviada!")
                st.info("Ping exibido apenas no console.")
            except Exception as e:
                st.error(f"Erro: {e}")
