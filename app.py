import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Escáner de Almacén", layout="centered", initial_sidebar_state="collapsed")

# ==========================================
# 2. CARGA Y LIMPIEZA DE DATOS (NUBE)
# ==========================================
@st.cache_data(ttl=60) # Actualiza el catálogo automáticamente cada 60 segundos
def cargar_base_maestra():
    url_catalogo = "https://docs.google.com/spreadsheets/d/1sFb0ZuO22B0p52GqAPoodUQm1mgcEVb7AffY3jsKHXA/export?format=csv&gid=892257044"
    df = pd.read_csv(url_catalogo, dtype=str)
    for col in ['SKU', 'Codigo MELI', 'FNSKU']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

def cargar_guias():
    url_guias = "https://docs.google.com/spreadsheets/d/1sFb0ZuO22B0p52GqAPoodUQm1mgcEVb7AffY3jsKHXA/export?format=csv&gid=0"
    try:
        df = pd.read_csv(url_guias)
        df.columns = df.columns.str.strip().str.upper()
        
        # LIMPIEZA PROFUNDA
        df = df.replace(r'^\s*$', np.nan, regex=True)
        
        columnas_guia = [c for c in df.columns if c != 'SKU']
        df[columnas_guia] = df[columnas_guia].ffill()
        df = df.dropna(subset=['SKU'])
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            
        return df
    except Exception:
        return pd.DataFrame()

try:
    df_maestro = cargar_base_maestra()
except Exception as e:
    st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
    st.stop()

# Llama a la función de la nube sin pedir archivo local
df_guias = cargar_guias()

# ==========================================
# 3. VARIABLES DE ESTADO
# ==========================================
if 'codigo_final' not in st.session_state:
    st.session_state.codigo_final = ''
if 'temp_pistola' not in st.session_state:
    st.session_state.temp_pistola = ''
if 'temp_camara' not in st.session_state:
    st.session_state.temp_camara = ''

def procesar_pistola():
    st.session_state.codigo_final = st.session_state.temp_pistola
    st.session_state.temp_pistola = ''

def procesar_camara():
    st.session_state.codigo_final = st.session_state.temp_camara
    st.session_state.temp_camara = ''

# ==========================================
# 4. INTERFAZ DE ENTRADA (PESTAÑAS)
# ==========================================
tab_pistola, tab_camara = st.tabs(["🔫 Escáner de Pistola (PC)", "📸 Cámara de Celular (Móvil)"])

with tab_pistola:
    st.text_input("ESCANEE LA ETIQUETA AQUÍ:", key="temp_pistola", on_change=procesar_pistola, placeholder="Dispare el láser sobre el código...")
    
    # Autofocus fantasma para la pistola
    components.html(
        """
        <script>
        setTimeout(function() {
            const doc = window.parent.document;
            const inputs = doc.querySelectorAll('input');
            if (inputs.length > 0) { inputs[0].focus(); }
        }, 150); 
        </script>
        """, height=0, width=0
    )

with tab_camara:
    st.info("💡 Apunte la cámara trasera del celular hacia el código de barras.")
    
    # Módulo de cámara HTML5
    components.html(
        """
        <div id="reader" style="width:100%; max-width:450px; margin:0 auto; border-radius:10px; overflow:hidden;"></div>
        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
        function onScanSuccess(decodedText, decodedResult) {
            const doc = window.parent.document;
            const inputs = doc.querySelectorAll('input');
            // Buscamos el segundo input (el de la cámara)
            if(inputs.length > 1) {
                inputs[1].value = decodedText;
                inputs[1].dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
        let config = { fps: 10, qrbox: {width: 250, height: 150} };
        let html5QrcodeScanner = new Html5QrcodeScanner("reader", config, false);
        html5QrcodeScanner.render(onScanSuccess);
        </script>
        """, height=350
    )
    
    # Input invisible que recibe el texto de la cámara
    st.text_input("Código capturado por cámara:", key="temp_camara", on_change=procesar_camara, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. LÓGICA DE BÚSQUEDA Y PROCESAMIENTO
# ==========================================
codigo = st.session_state.codigo_final.strip().upper()

if codigo:
    skus_encontrados = []
    tienda_origen = "Desconocida"
    
    # A) Búsqueda en Guías Diarias
    if not df_guias.empty:
        columnas_guia = [c for c in df_guias.columns if c != 'SKU']
        for col in columnas_guia:
            coincidencia = df_guias[df_guias[col].str.contains(codigo, na=False, regex=False)]
            if not coincidencia.empty:
                if 'SKU' in df_guias.columns:
                    # Trae TODOS los SKUs permitiendo piezas múltiples idénticas (Para Shein/Temu)
                    skus_brutos = coincidencia['SKU'].astype(str).str.strip().str.upper().tolist()
                    skus_encontrados = [s for s in skus_brutos if s not in ["NAN", "NONE", ""]]
                    tienda_origen = "Guía Logística Diaria"
                    break

    # B) Búsqueda en Catálogo Maestro
    if not skus_encontrados:
        match_meli = df_maestro[df_maestro['Codigo MELI'] == codigo]
        if not match_meli.empty:
            skus_encontrados.append(match_meli.iloc[0]['SKU'])
            tienda_origen = "Mercado Libre (Catálogo Directo)"
        else:
            if 'FNSKU' in df_maestro.columns:
                match_fnsku = df_maestro[df_maestro['FNSKU'] == codigo]
                if not match_fnsku.empty:
                    skus_encontrados.append(match_fnsku.iloc[0]['SKU'])
                    tienda_origen = "Amazon (FNSKU)"
            
            if not skus_encontrados:
                match_sku = df_maestro[df_maestro['SKU'] == codigo]
                if not match_sku.empty:
                    skus_encontrados.append(codigo)
                    tienda_origen = "Búsqueda Directa por SKU"

    # ==========================================
    # 6. RENDERIZADO VISUAL DE PRODUCTOS
    # ==========================================
    if skus_encontrados:
        total_productos = len(skus_encontrados)
        
        if total_productos > 1:
            st.error(f"### 🚨 ¡ATENCIÓN! PEDIDO MÚLTIPLE: {total_productos} PRODUCTOS 🚨", icon="⚠️")
            st.markdown("<br>", unsafe_allow_html=True)
            
        for indice, sku_encontrado in enumerate(skus_encontrados):
            fila_producto = df_maestro[df_maestro['SKU'] == sku_encontrado]
            
            if not fila_producto.empty:
                titulo = fila_producto.iloc[0]['Titulo']
                variante = fila_producto.iloc[0]['Variante'] if 'Variante' in fila_producto.columns else "-"
                nombre_chino = fila_producto.iloc[0]['Nombre Chino'] if 'Nombre Chino' in fila_producto.columns else "-"
                
                caja = fila_producto.iloc[0]['Caja'] if 'Caja' in fila_producto.columns else "0"
                cinta = fila_producto.iloc[0]['Cinta Nano'] if 'Cinta Nano' in fila_producto.columns else "0"
                imagen_nombre = fila_producto.iloc[0]['Imagen'] if 'Imagen' in fila_producto.columns else None
                
                msg_caja = f"📦 {caja}" if str(caja).upper() not in ["0", "NAN", "SIN CAJA"] else "⚠️ SIN CAJA (Mandar en Bolsa/Playo)"
                msg_cinta = f"🔒 Lleva Cinta: {cinta}" if str(cinta).upper() not in ["0", "NAN", "SIN CINTA"] else "🚫 No requiere Cinta Nano"

                if pd.notna(imagen_nombre) and str(imagen_nombre).strip() != "":
                    ruta_img = os.path.join("IMAGENES_VMINGO_PDF", str(imagen_nombre))
                    if os.path.exists(ruta_img):
                        col_espacio1, col_img, col_espacio2 = st.columns([1, 4, 1])
                        with col_img:
                            st.image(ruta_img, use_container_width=True)
                    else:
                        st.warning(f"📸 Foto no encontrada: {ruta_img}")
                
                st.markdown(f"<h1 style='text-align: center; margin-bottom: 0px; font-size: 2.5rem;'>{titulo}</h1>", unsafe_allow_html=True)
                
                if pd.notna(variante) and str(variante).strip().upper() not in ["-", "NAN", ""]:
                    st.markdown(f"<h3 style='text-align: center; color: #555; font-weight: 400;'>Variante: <b>{variante}</b></h3>", unsafe_allow_html=True)
                    
                if pd.notna(nombre_chino) and str(nombre_chino).strip().upper() not in ["-", "NAN", "SIN NOMBRE CHINO", ""]:
                    st.markdown(f"<p style='text-align: center; font-family: monospace; color: #999;'>🇨🇳 {nombre_chino}</p>", unsafe_allow_html=True)
                
                st.markdown(f"<p style='text-align: center; font-family: monospace; font-size: 1.1em; color: #666666; margin-bottom: 25px;'>🏷️ SKU: {sku_encontrado}</p>", unsafe_allow_html=True)
                
                col_izq, col_der = st.columns(2)
                with col_izq:
                    st.info(f"**Caja:**\n### {msg_caja}")
                with col_der:
                    st.success(f"**Sellado:**\n### {msg_cinta}")
                
                st.markdown(f"<p style='text-align: center; font-size: 0.85rem; color: #ccc; margin-top: 25px;'>Origen: {tienda_origen} | Ref: {codigo}</p>", unsafe_allow_html=True)
                
                if indice < total_productos - 1:
                    st.markdown("<hr style='border: 2px dashed #ff4b4b; margin: 50px 0;'>", unsafe_allow_html=True)
                
            else:
                st.error(f"❌ La guía mapeó al SKU `{sku_encontrado}`, pero ese SKU no existe en tu Excel maestro.")
    else:
        st.warning(f"No se reconoció el código `{codigo}`. Revise el lector.")

# ==========================================
# 7. CENTRO DE AYUDA
# ==========================================
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("❓ ¿El sistema no reconoce una guía? Centro de Ayuda"):
    st.markdown("""
    ### 🛠️ Guía rápida para resolver problemas en piso:
    
    1. **La pantalla de la PC no enfoca sola:** Haz un clic en la barra que dice 'ESCANEE LA ETIQUETA AQUÍ' para reactivar el láser.
    2. **El sistema marca que no encontró nada:** Revisa si guardaste el archivo `Guias_del_dia.xlsx` tras pegar los datos nuevos. Recuerda recargar la página presionando `R`.
    3. **Aparece un SKU inexistente en rojo:** Significa que la guía se leyó bien, pero ese código de producto es nuevo y falta darlo de alta en tu base maestra (`Catalogo para escaner.xlsx`).
    4. **El celular no abre la cámara:** Revisa los permisos de tu navegador web móvil y asegúrate de haberle dado en "Permitir" al uso de video.
    """)
