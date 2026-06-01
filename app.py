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
@st.cache_data(ttl=60)
def cargar_base_maestra():
    url_catalogo = "https://docs.google.com/spreadsheets/d/1sFb0ZuO22B0p52GqAPoodUQm1mgcEVb7AffY3jsKHXA/export?format=csv&gid=892257044"
    # Forzamos a que lea el catálogo estrictamente como texto
    df = pd.read_csv(url_catalogo, dtype=str)
    
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
        # Barredora: Destruye los decimales (.0) en los números largos de MELI
        df[col] = df[col].apply(lambda x: x[:-2] if str(x).endswith('.0') else x)
        
    return df

def cargar_guias():
    url_guias = "https://docs.google.com/spreadsheets/d/1sFb0ZuO22B0p52GqAPoodUQm1mgcEVb7AffY3jsKHXA/export?format=csv&gid=0"
    try:
        # FIX CLAVE: dtype=str para que las guías no se deformen
        df = pd.read_csv(url_guias, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        
        # Limpieza ultra agresiva para recuperar los pedidos combinados
        df = df.replace(r'^\s*$', np.nan, regex=True)
        df = df.replace(['NAN', 'NONE', 'NULL', ''], np.nan)
        
        columnas_guia = [c for c in df.columns if c != 'SKU']
        df[columnas_guia] = df[columnas_guia].ffill()
        df = df.dropna(subset=['SKU'])
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            # Barredora para las guías logísticas
            df[col] = df[col].apply(lambda x: x[:-2] if str(x).endswith('.0') else x)
            
        return df
    except Exception:
        return pd.DataFrame()

try:
    df_maestro = cargar_base_maestra()
except Exception as e:
    st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
    st.stop()

df_guias = cargar_guias()

# ==========================================
# MOTOR DE BÚSQUEDA DE IMÁGENES (ANTI-LINUX Y RAÍZ)
# ==========================================
def obtener_ruta_imagen(nombre_imagen):
    if not pd.notna(nombre_imagen) or str(nombre_imagen).strip() == "":
        return None
    
    nombre_limpio = str(nombre_imagen).strip().lower()
    
    # 1. Buscar directamente en la raíz (ya que se subieron sueltas en GitHub)
    if os.path.exists('.'):
        for archivo in os.listdir('.'):
            if archivo.lower() == nombre_limpio:
                return archivo
                
    # 2. Buscar en la carpeta por si alguna sí entró ahí
    carpeta = "IMAGENES_VMINGO_PDF"
    if os.path.exists(carpeta):
        for archivo in os.listdir(carpeta):
            if archivo.lower() == nombre_limpio:
                return os.path.join(carpeta, archivo)
    return None

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
tab_pistola, tab_camara = st.tabs(["🔫 Escáner de Pistola (PC)", "📸 Cámara Automática (Móvil)"])

with tab_pistola:
    st.text_input("ESCANEE LA ETIQUETA AQUÍ:", key="temp_pistola", on_change=procesar_pistola, placeholder="Dispare el láser sobre el código...")
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
    st.info("💡 La cámara trasera se activará automáticamente.")
    
    # Módulo de cámara HTML5 FORZADO (Con Hack para React/Streamlit)
    components.html(
        """
        <div id="reader" style="width:100%; max-width:450px; margin:0 auto; border-radius:10px; overflow:hidden;"></div>
        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
        function onScanSuccess(decodedText, decodedResult) {
            const doc = window.parent.document;
            const inputs = doc.querySelectorAll('input');
            let targetInput = null;
            
            // Buscamos la caja de texto exacta por su fondo
            for (let i = 0; i < inputs.length; i++) {
                if (inputs[i].placeholder === "Escriba y presione Enter...") {
                    targetInput = inputs[i];
                    break;
                }
            }
            
            if(targetInput) {
                // Truco maestro para obligar a React a leer el código
                let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(targetInput, decodedText);
                
                // Detonamos el Enter automático
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                targetInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Pausar el escáner 3 segundos para no escanear lo mismo 20 veces
                if (html5QrCode.getState() === 2) {
                    html5QrCode.pause(true);
                    setTimeout(() => html5QrCode.resume(), 3000);
                }
            }
        }
        
        const html5QrCode = new Html5Qrcode("reader");
        const config = { fps: 10, qrbox: {width: 250, height: 150} };
        
        html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess)
        .catch(err => {
            console.log("Error al iniciar cámara: ", err);
        });
        </script>
        """, height=350
    )
    
    st.text_input("✏️ O escriba el código manualmente aquí:", key="temp_camara", on_change=procesar_camara, placeholder="Escriba y presione Enter...")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. LÓGICA DE BÚSQUEDA Y PROCESAMIENTO
# ==========================================
codigo = st.session_state.codigo_final.strip().upper()

if codigo:
    skus_encontrados = []
    tienda_origen = "Desconocida"
    
    if not df_guias.empty:
        columnas_guia = [c for c in df_guias.columns if c != 'SKU']
        for col in columnas_guia:
            coincidencia = df_guias[df_guias[col].str.contains(codigo, na=False, regex=False)]
            if not coincidencia.empty:
                if 'SKU' in df_guias.columns:
                    skus_brutos = coincidencia['SKU'].astype(str).str.strip().str.upper().tolist()
                    skus_encontrados = [s for s in skus_brutos if s not in ["NAN", "NONE", ""]]
                    tienda_origen = "Guía Logística Diaria"
                    break

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

                ruta_img = obtener_ruta_imagen(imagen_nombre)

                if ruta_img:
                    col_espacio1, col_img, col_espacio2 = st.columns([1, 4, 1])
                    with col_img:
                        st.image(ruta_img, use_container_width=True)
                else:
                    if pd.notna(imagen_nombre) and str(imagen_nombre).strip() != "":
                        st.warning(f"📸 Foto no encontrada en la nube: {imagen_nombre}")
                
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
with st.expander("❓ ¿El sistema no reconoce una guía o marca error?"):
    st.markdown("""
    ### 🛠️ Guía rápida:
    1. **No encuentra el producto:** Revisa que hayas pegado las guías de hoy en el Google Sheets.
    2. **Aparece un SKU inexistente:** El código de barras se leyó, pero falta dar de alta el producto en la pestaña 'Catalogo' de Google Sheets.
    3. **El celular no abre la cámara:** Revisa los permisos de Chrome/Safari y asegúrate de darle a "Permitir" uso de cámara.
    """)
