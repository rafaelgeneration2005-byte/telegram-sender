import streamlit as st
from telethon import TelegramClient
import asyncio
import time

# ===========================
# CONFIGURAÇÕES DO APP
# ===========================
st.set_page_config(
    page_title="Telegram Sender Pro",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilo escuro + estilização premium
st.markdown("""
<style>

html, body, [class*="css"]  {
    font-family: 'Segoe UI', sans-serif;
}

/* cartões */
.block {
    background-color: #1f1f1f;
    padding: 25px;
    border-radius: 14px;
    border: 1px solid #333;
    margin-top: 20px;
}

/* botões */
.stButton>button {
    width: 100%;
    background: linear-gradient(90deg, #4e8dff, #335fff);
    color: white;
    border-radius: 10px;
    padding: 10px;
    font-size: 17px;
    border: none;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #6ea0ff, #4c73ff);
}

/* títulos */
h1 {
    text-align: center;
}

</style>
""", unsafe_allow_html=True)


# ===========================
# TELEGRAM
# ===========================
api_id = 32994616
api_hash = "cf912432fa5bc84e7360944567697b08"

client = TelegramClient("sessao_streamlit", api_id, api_hash)
loop = asyncio.get_event_loop()

# ===========================
# STATE MACHINE
# ===========================
if "stage" not in st.session_state:
    st.session_state.stage = "phone"

st.title("🚀 Telegram Sender PRO")


# ===========================
# ETAPA 1 — TELEFONE
# ===========================
if st.session_state.stage == "phone":
    with st.container():
        st.markdown("<div class='block'>", unsafe_allow_html=True)
        st.subheader("1️⃣ Digite o número do Telegram")

        phone = st.text_input("Número (ex: +55DDDNUMERO)")

        if st.button("Enviar código"):
            try:
                loop.run_until_complete(client.connect())
                loop.run_until_complete(client.send_code_request(phone))
                st.session_state.phone = phone
                st.session_state.stage = "code"
                st.success("Código enviado com sucesso!")
            except Exception as e:
                st.error(f"Erro: {e}")

        st.markdown("</div>", unsafe_allow_html=True)


# ===========================
# ETAPA 2 — CÓDIGO SMS
# ===========================
elif st.session_state.stage == "code":
    st.markdown("<div class='block'>", unsafe_allow_html=True)

    st.subheader("2️⃣ Digite o código recebido no Telegram")
    code = st.text_input("Código SMS", max_chars=6)

    if st.button("Confirmar código"):
        try:
            loop.run_until_complete(client.sign_in(st.session_state.phone, code))
            st.session_state.stage = "logged"
            st.success("Login efetuado!")
        except Exception as e:
            if "PASSWORD" in str(e):
                st.session_state.stage = "2fa"
            else:
                st.error(str(e))

    st.markdown("</div>", unsafe_allow_html=True)


# ===========================
# ETAPA 3 — SENHA 2FA
# ===========================
elif st.session_state.stage == "2fa":
    st.markdown("<div class='block'>", unsafe_allow_html=True)

    st.subheader("🔐 Digite sua senha 2FA")
    pw = st.text_input("Senha", type="password")

    if st.button("Confirmar 2FA"):
        try:
            loop.run_until_complete(client.sign_in(password=pw))
            st.session_state.stage = "logged"
            st.success("Login completo!")
        except Exception as e:
            st.error(str(e))

    st.markdown("</div>", unsafe_allow_html=True)


# ===========================
# ETAPA 4 — ESCOLHER GRUPO E ENVIAR
# ===========================
elif st.session_state.stage == "logged":
    st.markdown("<div class='block'>", unsafe_allow_html=True)
    st.subheader("📤 Envio automático")

    # Carrega grupos
    if "groups" not in st.session_state:
        async def get_groups():
            dlg = await client.get_dialogs()
            return [(d.id, d.title) for d in dlg if d.is_group]

        st.session_state.groups = loop.run_until_complete(get_groups())

    groups = {name: gid for gid, name in st.session_state.groups}

    group_name = st.selectbox("Selecione o grupo:", list(groups.keys()))
    message = st.text_area("Mensagem")

    if st.button("ENVIAR MENSAGEM"):
        gid = groups[group_name]

        placeholder = st.empty()
        placeholder.info("⏳ Tentando enviar... Grupo pode estar fechado.")

        async def tentar():
            while True:
                try:
                    start = time.perf_counter()
                    await client.send_message(gid, message)

                    ping = (time.perf_counter() - start) * 1000
                    print(f"[PING] {ping:.2f} ms")

                    return True
                except Exception:
                    placeholder.warning("🔄 Grupo fechado... tentando novamente...")
                    await asyncio.sleep(0.02)

        ok = loop.run_until_complete(tentar())

        if ok:
            placeholder.success("✅ Mensagem enviada com sucesso!")

    st.markdown("</div>", unsafe_allow_html=True)
