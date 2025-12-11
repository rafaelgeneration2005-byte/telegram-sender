# app.py
import streamlit as st
import asyncio
from telethon import TelegramClient
import time

# ---------- CONFIG ----------
api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

st.set_page_config(page_title="Telegram Sender", layout="centered")

# ---------- EVENT LOOP (Streamlit-friendly) ----------
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Create Telethon client bound to our custom loop
client = TelegramClient("sessao_streamlit", api_id, api_hash, loop=loop)

async def ensure_connected():
    if not client.is_connected():
        await client.connect()

# ---------- SESSION STATE defaults ----------
if "stage" not in st.session_state:
    st.session_state.stage = "phone"  # stages: phone, code, need_2fa, logged
if "phone" not in st.session_state:
    st.session_state.phone = None
if "phone_hash" not in st.session_state:
    st.session_state.phone_hash = None
if "need_2fa" not in st.session_state:
    st.session_state.need_2fa = False
if "groups" not in st.session_state:
    st.session_state.groups = None
if "selected_group_id" not in st.session_state:
    st.session_state.selected_group_id = None

# ---------- UI ----------
st.title("🚀 Telegram Sender — Competição")
st.caption("Login → listar grupos/canais → escolher → enviar em loop até abrir")

# ---------- STAGE: PHONE ----------
if st.session_state.stage == "phone":
    st.subheader("1) Digite seu número (ex: +55DDDNÚMERO)")
    phone_input = st.text_input("Número do Telegram", value=st.session_state.phone or "")
    if st.button("Enviar código SMS"):
        if not phone_input:
            st.error("Coloque um número válido.")
        else:
            try:
                # send code and keep phone_code_hash in session_state
                async def send_code():
                    await ensure_connected()
                    res = await client.send_code_request(phone_input)
                    return res.phone_code_hash

                phone_hash = loop.run_until_complete(send_code())
                st.session_state.phone = phone_input
                st.session_state.phone_hash = phone_hash
                st.session_state.stage = "code"
                st.success("Código enviado! Verifique seu Telegram (app ou SMS).")
            except Exception as e:
                st.error(f"Erro ao enviar código: {e}")

# ---------- STAGE: CODE ----------
elif st.session_state.stage == "code":
    st.subheader("2) Digite o código recebido")
    code_input = st.text_input("Código (ex: 12345)", max_chars=10)
    if st.button("Confirmar código"):
        if not code_input:
            st.error("Digite o código.")
        else:
            try:
                async def do_sign_in():
                    await ensure_connected()
                    # Use phone_hash stored earlier
                    return await client.sign_in(st.session_state.phone, code_input, phone_code_hash=st.session_state.phone_hash)

                loop.run_until_complete(do_sign_in())
                st.session_state.stage = "logged"
                st.session_state.need_2fa = False
                st.success("Login realizado com sucesso!")
            except Exception as e:
                msg = str(e)
                # Telethon may raise error requiring 2FA password
                if "password" in msg.lower() or "two-step" in msg.lower() or "2fa" in msg.lower():
                    st.session_state.need_2fa = True
                    st.warning("Conta com 2FA detectada. Informe a senha abaixo.")
                else:
                    st.error(f"Falha no login: {e}")

# ---------- STAGE: 2FA ----------
if st.session_state.need_2fa:
    st.subheader("🔐 Digite a senha 2FA")
    pass_input = st.text_input("Senha 2FA", type="password")
    if st.button("Confirmar senha 2FA"):
        if not pass_input:
            st.error("Digite a senha 2FA.")
        else:
            try:
                async def do_pass():
                    await ensure_connected()
                    return await client.sign_in(password=pass_input)
                loop.run_until_complete(do_pass())
                st.session_state.need_2fa = False
                st.session_state.stage = "logged"
                st.success("2FA confirmada. Login completo!")
            except Exception as e:
                st.error(f"Senha 2FA incorreta ou erro: {e}")

# ---------- STAGE: LOGGED (listar grupos e enviar) ----------
if st.session_state.stage == "logged":
    st.subheader("3) Escolha o grupo/canal (apenas grupos e canais)")

    # Load groups once
    if st.session_state.groups is None:
        try:
            async def get_groups():
                await ensure_connected()
                dialogs = await client.get_dialogs()
                result = []
                for d in dialogs:
                    # include groups and channels (supergroups, channels)
                    if getattr(d, "is_group", False) or getattr(d, "is_channel", False):
                        title = getattr(d.entity, "title", None) or getattr(d.entity, "first_name", str(d.id))
                        result.append((d.id, title))
                return result

            groups = loop.run_until_complete(get_groups())
            # dedupe and keep order
            seen = set()
            unique = []
            for gid, title in groups:
                if gid not in seen:
                    seen.add(gid)
                    unique.append((gid, title))
            st.session_state.groups = unique

            if not unique:
                st.warning("Nenhum grupo/canal encontrado na conta.")
        except Exception as e:
            st.error(f"Erro ao buscar grupos: {e}")
            st.session_state.groups = []

    # build selectbox
    options = [f"{title} — {gid}" for (gid, title) in st.session_state.groups]
    if options:
        sel = st.selectbox("Selecione o grupo/canal", options)
        # extract id
        sel_index = options.index(sel)
        selected_gid = st.session_state.groups[sel_index][0]
        st.session_state.selected_group_id = selected_gid

        st.markdown("---")
        message_text = st.text_area("Mensagem que será enviada (não inclua ping)", height=120)

        # Status area (to show messages while trying)
        status_placeholder = st.empty()
        status_placeholder.info("Pronto. Clique em ENVIAR para começar a tentativa.")

        if st.button("ENVIAR EM LOOP ATÉ ABRIR"):
            if not message_text:
                st.error("Digite a mensagem primeiro.")
            else:
                # Run the flood loop (blocking for the user action)
                async def flood_loop(gid, text, placeholder):
                    placeholder.info("⏳ Tentando enviar... (grupo pode estar fechado).")
                    while True:
                        try:
                            start = time.perf_counter()
                            await client.send_message(int(gid), text)
                            ping = (time.perf_counter() - start) * 1000
                            # print ping only to console/logs
                            print(f"[PING] Mensagem entregue em {ping:.2f} ms")
                            return ping
                        except Exception:
                            placeholder.warning("🔄 Grupo fechado. Tentando novamente...")
                            await asyncio.sleep(0.02)

                try:
                    ping_value = loop.run_until_complete(flood_loop(st.session_state.selected_group_id, message_text, status_placeholder))
                    status_placeholder.success("✅ Mensagem enviada com sucesso!")
                    st.info(f"Ping (apenas no console): veja os logs. (valor calculado: {ping_value:.2f} ms)")
                except Exception as e:
                    st.error(f"Erro durante envio: {e}")
    else:
        st.info("Ainda não há grupos carregados. Recarregue a página depois de logar.")
