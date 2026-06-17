import streamlit as st
import pandas as pd
import re
from difflib import get_close_matches
import io
import zipfile

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(page_title="🧹 Limpieza de Emails", layout="wide")

st.title("🧹 Limpieza de Correos Electrónicos")
st.write("Subí tu archivo CSV o Excel, limpiamos los correos inválidos y te devolvemos uno corregido. Ahora también podés dividirlo en partes y personalizar el nombre final.")

# ==============================
# PARÁMETROS
# ==============================
valid_domains = [
    'gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com', 'live.com', 'icloud.com'
]

generic_roles = ['info', 'ventas', 'administracion', 'contacto', 'support', 'no-reply']

# ==============================
# FUNCIÓN DE LIMPIEZA
# ==============================
def smart_normalize_and_validate(email):
    if not isinstance(email, str) or '@' not in email:
        return None, False, True

    user, domain = email.lower().strip().split('@', 1)

    # Roles genéricos
    if any(user.startswith(role) for role in generic_roles):
        return None, False, True

    # Formato mínimo
    if len(user) <= 4 or user.isdigit():
        return None, False, True

    # Corrección automática de dominios
    matches = get_close_matches(domain, valid_domains, n=1, cutoff=0.6)
    corrected_domain = matches[0] if matches else domain

    if corrected_domain not in valid_domains:
        return None, False, True

    normalized_email = f"{user}@{corrected_domain}"
    is_domain_valid = True

    # Detección de mails sospechosos
    num_digits = sum(c.isdigit() for c in user)
    num_letters = sum(c.isalpha() for c in user)
    if num_letters > 0 and num_digits / num_letters > 1.5:
        return None, False, True
    elif len(user) < 3 and user.isalnum():
        return None, False, True
    elif re.search(r'\d{5,}', user) or re.search(r'^[a-z]\d{6,}', user):
        return None, False, True

    return normalized_email, is_domain_valid, False


# ==============================
# CARGA DE ARCHIVO
# ==============================
uploaded_file = st.file_uploader("📂 Subí un archivo CSV o Excel", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, encoding="utf-8", sep=None, engine="python")
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"✅ Archivo cargado con éxito ({len(df)} filas).")

        st.write("### Columnas detectadas:")
        st.dataframe(df.head())

        # Normalizamos nombres de columnas
        df.columns = df.columns.str.strip().str.lower().str.replace('�', '', regex=False)

        # Seleccionar columna de email
        email_col = st.selectbox("📧 Seleccioná la columna de emails", df.columns)

        # ==============================
        # PROCESO DE LIMPIEZA
        # ==============================
        if st.button("🚀 Limpiar Emails"):
            with st.spinner("Procesando y limpiando correos..."):
                df['analisis'] = df[email_col].apply(smart_normalize_and_validate)
                df[['email_normalizado', 'dominio_valido', 'sospechoso']] = pd.DataFrame(df['analisis'].tolist(), index=df.index)

                df_clean = df[(df['dominio_valido'] == True) & (df['sospechoso'] == False)].copy()
                df_clean[email_col] = df_clean['email_normalizado']
                df_clean = df_clean.drop(columns=['analisis', 'email_normalizado', 'dominio_valido', 'sospechoso'])

                # ✅ Guardamos en sesión para no perderlo si cambia otro input
                st.session_state["df_clean"] = df_clean

                st.success(f"✅ Limpieza completada. {len(df_clean)} correos válidos encontrados.")
                st.dataframe(df_clean.head())

        # ==============================
        # SI YA TENEMOS DF LIMPIO, MOSTRAMOS OPCIONES
        # ==============================
        if "df_clean" in st.session_state:
            df_clean = st.session_state["df_clean"]

            st.markdown("### ✂️ Opciones de división del archivo limpio")

            nombre_base = st.text_input("📁 Nombre base para los archivos (sin extensión)", value="emails_limpios")
            n_partes = st.number_input("🔢 ¿En cuántas partes querés dividir el archivo?", min_value=1, max_value=100, value=1)

            if st.button("⬇️ Generar archivos para descargar"):
                total_filas = len(df_clean)
                filas_por_parte = total_filas // n_partes

                archivos_zip = io.BytesIO()
                with zipfile.ZipFile(archivos_zip, "w") as zf:
                    for i in range(n_partes):
                        inicio = i * filas_por_parte
                        fin = (i + 1) * filas_por_parte if i < n_partes - 1 else total_filas
                        parte = df_clean.iloc[inicio:fin]

                        nombre_archivo = f"{nombre_base}_parte_{i+1}.csv"
                        csv_bytes = parte.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                        zf.writestr(nombre_archivo, csv_bytes)

                archivos_zip.seek(0)

                st.download_button(
                    label=f"⬇️ Descargar {n_partes} archivos en ZIP",
                    data=archivos_zip,
                    file_name=f"{nombre_base}_dividido.zip",
                    mime="application/zip"
                )

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {str(e)}")

else:
    st.info("👆 Esperando que subas un archivo para comenzar.")

st.markdown("---")
st.caption("Limpieza de Emails con Streamlit + División de Archivos")
