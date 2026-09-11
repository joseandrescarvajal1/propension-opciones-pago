"""Front del sandbox (Streamlit) para probar el sistema agéntico de extremo a extremo.

Habla con la API del agente (AGENTE_API_URL, por defecto http://127.0.0.1:8001) con la clave AGENTE_API_KEY.
Pestañas: WhatsApp (reactivo y proactivo por cliente), Campaña proactiva (lote), Ficha del cliente, Trazas y gestor.

Uso en local:
    uvicorn agente.api.main:app --port 8001          (en otra terminal)
    streamlit run agente/front/app.py

En Cloud Run se despliega con deploy/Dockerfile.front y deploy/service_front.yaml: obtiene el token de
identidad de su cuenta de servicio y protege el acceso con FRONT_PASSWORD (Secret Manager).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
API = os.environ.get("AGENTE_API_URL", "http://127.0.0.1:8001").rstrip("/")
CAB = {"X-API-Key": os.environ.get("AGENTE_API_KEY", "")}

st.set_page_config(page_title="Sandbox agente de cobranza", page_icon="💬", layout="wide")


@st.cache_data(ttl=3000)
def _token_identidad() -> str | None:
    """La API del agente exige token de identidad IAM. En Cloud Run lo da la cuenta de servicio
    (servidor de metadata); en local, gcloud."""
    if ".run.app" not in API:
        return None
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token
        return google.oauth2.id_token.fetch_id_token(google.auth.transport.requests.Request(), API)
    except Exception:  # noqa: BLE001 - fuera de GCP: gcloud
        import subprocess
        for cmd in (os.environ.get("GCLOUD", "gcloud"), r"C:\Users\USUARIO\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"):
            try:
                tok = subprocess.run([cmd, "auth", "print-identity-token"], capture_output=True, text=True, timeout=60).stdout.strip()
                if tok:
                    return tok
            except Exception:  # noqa: BLE001
                continue
    return None


def puerta() -> bool:
    """Contraseña de acceso cuando el front se publica en internet (FRONT_PASSWORD).
    Sin ella el front queda abierto, que es aceptable solo en local."""
    clave = os.environ.get("FRONT_PASSWORD")
    if not clave:
        return True
    if st.session_state.get("acceso_ok"):
        return True
    st.title("Sandbox · Agente de cobranza")
    st.caption("Prototipo con clientes simulados. Ingresa la contraseña de la demostración.")
    with st.form("acceso"):
        entrada = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            import hmac
            if hmac.compare_digest(entrada, clave):
                st.session_state["acceso_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    return False


def api(metodo: str, ruta: str, **kw):
    try:
        cab = dict(CAB)
        tok = _token_identidad()
        if tok:
            cab["Authorization"] = f"Bearer {tok}"
        r = httpx.request(metodo, f"{API}{ruta}", headers=cab, timeout=180.0, **kw)
        if r.status_code >= 400:
            st.error(f"{metodo} {ruta}: {r.status_code} {r.text[:300]}")
            return None
        return r.json()
    except httpx.HTTPError as e:
        st.error(f"No se pudo conectar con la API del agente en {API}: {e}")
        return None


@st.cache_data(ttl=30)
def clientes():
    d = api("GET", "/sandbox/clientes")
    return pd.DataFrame(d["clientes"]) if d else pd.DataFrame()


def burbuja(m: dict):
    entrante = m["direccion"] == "entrante"
    color = "#DCF8C6" if not entrante else "#FFFFFF"
    align = "flex-end" if not entrante else "flex-start"
    etiqueta = "📱 SMS" if m["canal"] == "sms" else ("📄 plantilla" if m["tipo"] == "plantilla" else "")
    st.markdown(f"""<div style="display:flex;justify-content:{align};margin:4px 0"><div style="background:{color};border-radius:10px;padding:8px 12px;max-width:75%;
                box-shadow:0 1px 1px rgba(0,0,0,.15);font-size:14px;color:#111"><div style="font-size:10px;color:#666">{'Cliente' if entrante else 'Bancolombia'} {etiqueta} · {m['creado'][11:19]}</div>{m['texto']}</div></div>""",
                unsafe_allow_html=True)


if not puerta():
    st.stop()

st.title("Sandbox · Agente de cobranza (Parte 2)")
st.caption(f"API del agente: {API}")
df = clientes()
if df.empty:
    st.stop()

tab_chat, tab_lote, tab_ficha, tab_trazas = st.tabs(["💬 WhatsApp (reactivo y proactivo)", "📣 Campaña proactiva", "🗂️ Ficha del cliente", "🔍 Trazas y gestor humano"])

with st.sidebar:
    st.header("Cliente simulado")
    esc = st.selectbox("Escenario", ["todos"] + sorted(df.escenario.unique()))
    sub = df if esc == "todos" else df[df.escenario == esc]
    etiqueta = sub.apply(lambda r: f"{r.nombre} · {r.cedula} · {r.escenario[:2]}", axis=1)
    sel = st.selectbox("Cliente", list(etiqueta))
    fila = sub.iloc[list(etiqueta).index(sel)]
    cedula = fila.cedula
    st.caption(fila.descripcion_escenario)
    st.write(f"**Producto:** {fila.producto}  \n**Días de mora:** {fila.dias_mora} ({fila.etapa_mora})  \n**Vencido:** ${fila.valor_vencido:,.0f}  \n**Cuota:** ${fila.valor_cuota:,.0f}")
    st.divider()
    if st.button("🔄 Reiniciar sandbox (borra hilos)"):
        r = api("POST", "/sandbox/reiniciar"); st.cache_data.clear(); st.success("Sandbox reiniciado" if r and r.get("reiniciado") else "No se pudo reiniciar")

# ---------------------------------------------------------------- WhatsApp
with tab_chat:
    col_chat, col_tel = st.columns([2, 1])
    with col_tel:
        st.subheader("📱 Teléfono del cliente")
        st.caption(f"{fila.nombre} · {fila.telefono or 'sin teléfono'}")
        sms = api("GET", f"/sandbox/otp/{cedula}")
        if sms and sms.get("sms"):
            cod = re.search(r"\b(\d{6})\b", sms["sms"]["texto"])
            st.info(f"SMS · {sms['sms']['creado'][11:19]}\n\n{sms['sms']['texto']}")
            if cod:
                st.code(cod.group(1), language=None)
        else:
            st.caption("Sin SMS de verificación todavía.")
        st.divider()
        st.subheader("📣 Gestión proactiva")
        st.caption("Busca en la base, llama al modelo, decide la siguiente mejor acción y envía la plantilla de WhatsApp.")
        if st.button("Lanzar gestión proactiva para este cliente"):
            r = api("POST", "/proactivo", json={"cedula": cedula})
            if r:
                st.session_state["ultimo_proactivo"] = r
        if "ultimo_proactivo" in st.session_state and st.session_state["ultimo_proactivo"].get("cedula") == cedula:
            r = st.session_state["ultimo_proactivo"]
            st.write(f"**Acción:** {r['accion']}  \n**Motivo:** {r['motivo']}  \n**Propensión:** {r['propension']} ({r['fuente_modelo']})  \n**Opción recomendada:** {r.get('opcion_recomendada') or '-'}  \n**Plantilla:** {r.get('plantilla') or '-'}")
            if not r.get("enviado"):
                st.warning(f"No se envió: {r.get('motivo_no_envio')}")
    with col_chat:
        st.subheader("💬 WhatsApp simulado")
        conv = api("GET", f"/conversaciones/{cedula}") or {"mensajes": []}
        estado = f"hilo `{cedula}` · turno {conv.get('turno', 0)} · {'✅ verificado' if conv.get('verificado') else '🔒 sin verificar'} · acción {conv.get('accion') or '-'} · origen {conv.get('origen') or '-'}"
        if conv.get("bloqueado"):
            estado += " · ⛔ bloqueado"
        if conv.get("escalado"):
            estado += f" · 🙋 escalado ({conv['escalado'].get('motivo', '')[:60]})"
        st.caption(estado)
        caja = st.container(height=420)
        with caja:
            for m in conv["mensajes"]:
                if m["canal"] == "whatsapp":
                    burbuja(m)
        msg = st.chat_input("Escribe como el cliente…")
        if msg:
            with st.spinner("El agente está respondiendo…"):
                r = api("POST", "/chat", json={"thread_id": cedula, "mensaje": msg})
            if r:
                st.session_state["ultimo_turno"] = r
            st.rerun()
        if "ultimo_turno" in st.session_state and st.session_state["ultimo_turno"].get("thread_id") == cedula:
            r = st.session_state["ultimo_turno"]
            u = r.get("uso") or {}
            st.caption(f"Último turno: ruta {' → '.join(r['ruta'])} · guardrail entrada **{r['guardrail_entrada']}** · salida **{r['guardrail_salida']}** · "
                       f"{r['latencia_ms']:.0f} ms · LLM {u.get('llamadas_llm', 0)} llamadas, {u.get('tokens_entrada', 0)}+{u.get('tokens_salida', 0)} tokens · herramientas {u.get('herramientas', [])}")

# ---------------------------------------------------------------- Campaña
with tab_lote:
    st.subheader("Campaña proactiva del día")
    st.caption("Recorre los clientes seleccionados, llama al modelo y decide la siguiente mejor acción; envía la plantilla solo cuando corresponde.")
    escs = st.multiselect("Escenarios", sorted(df.escenario.unique()), default=sorted(df.escenario.unique()))
    objetivo = df[df.escenario.isin(escs)]
    st.write(f"{len(objetivo)} clientes")
    if st.button("Ejecutar campaña"):
        with st.spinner("Decidiendo acciones…"):
            r = api("POST", "/proactivo/lote", json={"cedulas": list(objetivo.cedula)})
        if r:
            st.session_state["campana"] = r
    if "campana" in st.session_state:
        r = st.session_state["campana"]
        c1, c2 = st.columns(2)
        c1.metric("Clientes", r["n"]); c2.metric("Plantillas enviadas", r["enviados"])
        st.bar_chart(pd.Series(r["por_accion"]))
        res = pd.DataFrame(r["resultados"])[["cedula", "nombre", "accion", "propension", "fuente_modelo", "opcion_recomendada", "plantilla", "enviado", "motivo"]]
        st.dataframe(res, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- Ficha
with tab_ficha:
    st.subheader(f"Ficha de {fila.nombre} (lo que ve el gestor)")
    f = api("GET", f"/sandbox/cliente/{cedula}")
    if f:
        nba = f["siguiente_mejor_accion"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Siguiente mejor acción", nba["accion"]); c2.metric("Propensión (modelo)", f"{nba['propension']['prob']:.2f}" if nba["propension"]["prob"] is not None else "n/d", nba["propension"]["fuente"])
        c3.metric("Etapa de mora", f"{nba['etapa_mora']} ({nba['dias_mora']} d)")
        st.write(f"**Motivo:** {nba['motivo']}")
        st.write("**Reglas aplicadas:** " + " · ".join(nba["reglas_aplicadas"]))
        if nba["propension"]["factores"]:
            st.write("**Factores del modelo (SHAP, lenguaje de negocio):**")
            st.dataframe(pd.DataFrame(nba["propension"]["factores"])[["descripcion", "contribucion"]], hide_index=True, use_container_width=True)
        for o in f["deuda"]["obligaciones"]:
            with st.expander(f"{o['producto']} · vencido ${o['valor_vencido']:,.0f} · {o['dias_mora']} días", expanded=True):
                e = o["elegibilidad"]
                st.write(f"Saldo ${o['saldo_capital']:,.0f} · cuota ${o['valor_cuota']:,.0f} · inconsistencias: {o['inconsistencias'] or 'ninguna'}")
                st.write("**Opciones elegibles:** " + (", ".join(f"{x['nombre']} (cuota ${x['cuota_nueva']:,.0f})" for x in e["opciones_elegibles"]) or "ninguna"))
                st.write("**No elegibles:** " + (", ".join(f"{x['nombre']}: {x['motivo']}" for x in e["opciones_no_elegibles"]) or "ninguna"))
                st.write(f"**Acuerdo de pago:** {'elegible' if e['acuerdo']['elegible'] else 'no elegible'} · {e['acuerdo']['motivo']}")
                if o["acuerdos"]:
                    st.dataframe(pd.DataFrame(o["acuerdos"]), hide_index=True)
                if o["opciones_aplicadas"]:
                    st.dataframe(pd.DataFrame(o["opciones_aplicadas"]), hide_index=True)
        if f["deuda"]["restricciones"]:
            st.error("Restricciones: " + "; ".join(f"{r['tipo']}: {r['detalle']}" for r in f["deuda"]["restricciones"]))

# ---------------------------------------------------------------- Trazas
with tab_trazas:
    st.subheader(f"Trazas del hilo {cedula}")
    t = api("GET", f"/trazas/{cedula}")
    if t and t["n"]:
        st.caption(f"{t['n']} eventos · tokens {t['tokens_entrada']} entrada / {t['tokens_salida']} salida")
        tr = pd.DataFrame(t["trazas"])
        tr["detalle"] = tr.detalle.str.slice(0, 220)
        st.dataframe(tr[["turno", "nodo", "evento", "latencia_ms", "tokens_entrada", "tokens_salida", "detalle"]], use_container_width=True, hide_index=True, height=420)
        with st.expander("Detalle completo del evento"):
            i = st.number_input("Fila", 0, t["n"] - 1, 0)
            st.json(json.loads(t["trazas"][int(i)]["detalle"]) if (t["trazas"][int(i)]["detalle"] or "").startswith("{") else t["trazas"][int(i)]["detalle"])
    else:
        st.caption("Sin trazas todavía.")
    st.divider()
    st.subheader("🙋 Casos para gestor humano")
    e = api("GET", "/escalamientos")
    if e and e["n"]:
        st.dataframe(pd.DataFrame(e["casos"])[["creado", "thread_id", "prioridad", "motivo", "resumen"]], use_container_width=True, hide_index=True)
    else:
        st.caption("Sin escalamientos.")
