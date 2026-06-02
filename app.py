import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
import base64

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y MARCA DE AGUA
# ==========================================
st.set_page_config(page_title="Escáner de Almacén", layout="centered", initial_sidebar_state="collapsed")

# MÓDULO DEL LOGO: Marca de Agua directa al fondo
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    # Inyecta la imagen directamente centrada, al fondo y transparente
    st.markdown(
        f"""
        <img src="data:image/png;base64,{encoded_string}" 
             style="position: fixed; 
                    top: 50%; 
                    left: 50%; 
                    transform: translate(-50%, -50%); 
                    width: 60%; 
                    max-width: 600px; 
                    opacity: 0.04; 
                    z-index: -100; 
                    pointer-events: none;">
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 2. CARGA Y LIMPIEZA DE DATOS (NUBE BLINDADA)
# ==========================================
@st.cache_data(ttl=30)
def cargar_base_maestra():
    url_catalogo = "https://docs.google.com/spreadsheets/d/1sFb0ZuO22B0p52GqAPoodUQm1mgcEVb7AffY3jsKHXA/export?format=csv&gid=892257044"
    df = pd.read_csv(url_catalogo, dtype=str)
    df.columns = df.columns.str.replace('\ufeff', '').str.strip().str.upper()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
        df[col] = df[col].apply(lambda x: str(x)[:-2] if str(x).endswith('.0') else str(x))
    return df

def cargar_guias():
    url_guias = "https://docs.google.com/spreadsheets/d/1sFb0ZuO22B0p52GqAPoodUQm1mgcEVb7AffY3jsKHXA/export?format=csv&gid=0"
    try:
        df = pd.read_csv(url_guias, dtype=str)
        df.columns = df.columns.str.replace('\ufeff', '').str.strip().str.upper()
        
        df = df.replace(r'^\s*$', np.nan, regex=True)
        df = df.replace(['NAN', 'NONE', 'NULL', 'nan', 'NaN', ''], np.nan)
        
        columnas_guia = [c for c in df.columns if c != 'SKU']
        if columnas_guia:
            df[columnas_guia] = df[columnas_guia].ffill()
            
        df = df.dropna(subset=['SKU'])
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df[col] = df[col].apply(lambda x: str(x)[:-2] if str(x).endswith('.0') else str(x))
            
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
# MOTOR DE INVENTARIO DE IMÁGENES (RAÍZ DE GITHUB)
# ==========================================
@st.cache_data
def cargar_inventario_imagenes():
    inventario = {}
    rutas_a_escanear = ['.', 'IMAGENES_VMINGO_PDF']
    for raiz in rutas_a_escanear:
        if os.path.exists(raiz):
            for arch in os.listdir(raiz):
                if arch.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    ruta_completa = arch if raiz == '.' else os.path.join(raiz, arch)
                    inventario[arch.lower()] = ruta_completa
    return inventario

inventario_imagenes = cargar_inventario_imagenes()

# ==========================================
# 3. VARIABLES DE ESTADO Y PROCESAMIENTO
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
tab_pistola, tab_camara = st.tabs(["🔫 Escáner de Pistola / SKU Manual", "📸 Cámara de Celular"])

with tab_pistola:
    st.text_input("ESCANEE CÓDIGO O ESCRIBA EL SKU AQUÍ:", key="temp_pistola", on_change=procesar_pistola, placeholder="Dispare el láser o teclee el SKU manualmente...")
    
    # IMÁN DE FOCO INFINITO PARA LA COMPUTADORA
    components.html(
        """
        <script>
        const doc = window.parent.document;
        function forceFocus() {
            const inputs = doc.querySelectorAll('input');
            if (inputs.length > 0) { 
                inputs[0].focus(); 
            }
        }
        setTimeout(forceFocus, 200);
        
        doc.addEventListener('click', function() {
            forceFocus();
        });
        </script>
        """, height=0, width=0
    )

with tab_camara:
    st.info("💡 Presione el botón azul para activar el lente e iniciar el escaneo.")
    
    # Módulo HTML5 con botón manual y Auto-Enter total
    components.html(
        """
        <div style="text-align: center; margin-bottom: 15px;">
            <button id="btn-iniciar" style="background-color: #24a0ed; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; max-width: 450px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                📸 CLIC AQUÍ PARA ESCANEAR
            </button>
        </div>
        <div id="reader" style="width:100%; max-width:450px; margin:0 auto; border-radius:10px; overflow:hidden;"></div>
        
        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
        let html5QrCode = null;
        
        function onScanSuccess(decodedText, decodedResult) {
            const doc = window.parent.document;
            const inputs = doc.querySelectorAll('input');
            let targetInput = null;
            
            for (let i = 0; i < inputs.length; i++) {
                if (inputs[i].placeholder === "Escriba o edite el código...") {
                    targetInput = inputs[i];
                    break;
                }
            }
            
            if(targetInput) {
                // Despierta la caja
                targetInput.focus();
                
                let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(targetInput, decodedText);
                
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                targetInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Micro-retraso para simular el auto-enter
                setTimeout(() => {
                    targetInput.blur();
                }, 100);
                
                if (html5QrCode && html5QrCode.getState() === 2) {
                    html5QrCode.pause(true);
                    setTimeout(() => html5QrCode.resume(), 3000);
                }
            }
        }
        
        document.getElementById('btn-iniciar').addEventListener('click', function() {
            if (typeof Html5Qrcode !== "undefined") {
                if (!html5QrCode) {
                    html5QrCode = new Html5Qrcode("reader");
                }
                
                const config = { fps: 15, qrbox: {width: 250, height: 150} };
                const button = document.getElementById('btn-iniciar');
                
                if (html5QrCode.getState() !== 2) {
                    button.innerText = "🔄 Conectando lente...";
                    button.style.backgroundColor = "#eab308";
                    
                    html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess)
                    .then(() => {
                        button.innerText = "🟢 Cámara Activa y Lista";
                        button.style.backgroundColor = "#22c55e";
                        button.disabled = true;
                    })
                    .catch(err => {
                        button.innerText = "❌ Reintentar Conexión";
                        button.style.backgroundColor = "#ef4444";
                    });
                }
            }
        });
        </script>
        """, height=420
    )
    
    st.text_input("✏️ Código capturado por la cámara:", key="temp_camara", on_change=procesar_camara, placeholder="Escriba o edite el código...")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. LÓGICA DE BÚSQUEDA ROBUSTA
# ==========================================
codigo = st.session_state.codigo_final.strip().upper()

if codigo:
    skus_encontrados = []
    tienda_origen = "Desconocida"
    
    # A) Búsqueda en Listas Diarias de Guías
    if not df_guias.empty:
        columnas_guia = [c for c in df_guias.columns if c != 'SKU']
        for col in columnas_guia:
            coincidencia = df_guias[df_guias[col] == codigo]
            if coincidencia.empty:
                coincidencia = df_guias[df_guias[col].str.contains(codigo, na=False, regex=False)]
                
            if not coincidencia.empty:
                if 'SKU' in df_guias.columns:
                    skus_brutos = coincidencia['SKU'].astype(str).str.strip().str.upper().tolist()
                    skus_encontrados = [s for s in skus_brutos if s not in ["NAN", "NONE", ""]]
                    tienda_origen = f"Guía Logística ({col})"
                    break

    # B) Búsqueda en Catálogo Maestro (MELI, Amazon o entrada Manual de SKU)
    if not skus_encontrados:
        if 'CODIGO MELI' in df_maestro.columns:
            match_meli = df_maestro[df_maestro['CODIGO MELI'] == codigo]
            if match_meli.empty:
                match_meli = df_maestro[df_maestro['CODIGO MELI'].str.contains(codigo, na=False, regex=False)]
            if not match_meli.empty:
                skus_encontrados.append(match_meli.iloc[0]['SKU'])
                tienda_origen = "Mercado Libre (Catálogo Directo)"
        
        if not skus_encontrados and 'FNSKU' in df_maestro.columns:
            match_fnsku = df_maestro[df_maestro['FNSKU'] == codigo]
            if match_fnsku.empty:
                match_fnsku = df_maestro[df_maestro['FNSKU'].str.contains(codigo, na=False, regex=False)]
            if not match_fnsku.empty:
                skus_encontrados.append(match_fnsku.iloc[0]['SKU'])
                tienda_origen = "Amazon (FNSKU)"
        
        if not skus_encontrados and 'SKU' in df_maestro.columns:
            match_sku = df_maestro[df_maestro['SKU'] == codigo]
            if not match_sku.empty:
                skus_encontrados.append(codigo)
                tienda_origen = "Búsqueda Manual por SKU"

    # ==========================================
    # 6. RENDERIZADO VISUAL ESTÁNDAR
    # ==========================================
    if skus_encontrados:
        total_productos = len(skus_encontrados)
        
        if total_productos > 1:
            st.error(f"### 🚨 ¡ATENCIÓN! PEDIDO MÚLTIPLE: {total_productos} PRODUCTOS 🚨", icon="⚠️")
            st.markdown("<br>", unsafe_allow_html=True)
            
        for indice, sku_encontrado in enumerate(skus_encontrados):
            fila_producto = df_maestro[df_maestro['SKU'] == sku_encontrado]
            
            if not fila_producto.empty:
                titulo = fila_producto.iloc[0]['TITULO'] if 'TITULO' in fila_producto.columns else "Producto"
                variante = fila_producto.iloc[0]['VARIANTE'] if 'VARIANTE' in fila_producto.columns else "-"
                nombre_chino = fila_producto.iloc[0]['NOMBRE CHINO'] if 'NOMBRE CHINO' in fila_producto.columns else "-"
                
                caja = fila_producto.iloc[0]['CAJA'] if 'CAJA' in fila_producto.columns else "0"
                cinta = fila_producto.iloc[0]['CINTA NANO'] if 'CINTA NANO' in fila_producto.columns else "0"
                imagen_nombre = fila_producto.iloc[0]['IMAGEN'] if 'IMAGEN' in fila_producto.columns else None
                
                msg_caja = f"📦 {caja}" if str(caja).upper() not in ["0", "NAN", "SIN CAJA"] else "⚠️ SIN CAJA (Mandar en Bolsa/Playo)"
                msg_cinta = f"🔒 Lleva Cinta: {cinta}" if str(cinta).upper() not in ["0", "NAN", "SIN CINTA"] else "🚫 No requiere Cinta Nano"

                ruta_img = None
                if pd.notna(imagen_nombre) and str(imagen_nombre).strip() != "" and str(imagen_nombre).strip().upper() != "NAN":
                    clave_busqueda = str(imagen_nombre).strip().lower()
                    ruta_img = inventario_imagenes.get(clave_busqueda)

                if ruta_img:
                    col_espacio1, col_img, col_espacio2 = st.columns([1, 4, 1])
                    with col_img:
                        st.image(ruta_img, use_container_width=True)
                else:
                    if pd.notna(imagen_nombre) and str(imagen_nombre).strip() != "" and str(imagen_nombre).strip().upper() != "NAN":
                        st.warning(f"📸 Archivo de imagen '{imagen_nombre}' no encontrado en el servidor.")
                
                st.markdown(f"<h1 style='text-align: center; margin-bottom: 0px; font-size: 2.5rem;'>{titulo}</h1>", unsafe_allow_html=True)
                
                if pd.notna(variante) and str(variante).strip().upper() not in ["-", "NAN", ""]:
                    st.markdown(f"<h3 style='text-align: center; color: #555; font-weight: 400;'>Variante: <b>{variante}</b></h3>", unsafe_allow_html=True)
                    
                if pd.notna(nombre_chino) and str(nombre_chino).strip().upper() not in ["-", "NAN", "SIN NOMBRE CHINO", ""]:
                    st.markdown(f"<p style='text-align: center; font-family: monospace; color: #999;'>Fábrica: {nombre_chino}</p>", unsafe_allow_html=True)
                
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
                st.error(f"❌ La guía mapeó al SKU `{sku_encontrado}`, pero ese SKU no existe en tu pestaña de Catálogo.")
    else:
        st.warning(f"No se reconoció el código o SKU `{codigo}`.")
