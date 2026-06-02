import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS
# ==========================================
st.set_page_config(page_title="Tablero de Empaque Almacén", layout="centered", initial_sidebar_state="collapsed")

# Inyección de diseño vivo, limpio y profesional (Tarjetas y tipografía)
st.markdown("""
<style>
    .stApp {
        background-color: #f4f6f9;
    }
    .main-title {
        text-align: center;
        color: #1e293b;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 5px;
    }
    .sub-title {
        text-align: center;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 25px;
    }
    .product-title {
        text-align: center;
        color: #0f172a;
        font-size: 2.4rem;
        font-weight: 700;
        margin-top: 15px;
        line-height: 1.2;
    }
    .sku-badge {
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1.2rem;
        background-color: #e2e8f0;
        color: #334155;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 600;
        display: block;
        margin: 10px auto 25px auto;
        width: fit-content;
    }
</style>
""", unsafe_allow_html=True)

# Cabecera de marca: Carga el logo automáticamente si existe en el repositorio
col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1])
with col_logo_2:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 class='main-title'>SISTEMA DE EMPAQUE</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Control Logístico de Flujo de Inventario en Nube</p>", unsafe_allow_html=True)


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
# MOTOR DE INVENTARIO DE IMÁGENES (RAÍZ)
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
tab_pistola, tab_camara = st.tabs(["🔫 Escáner de Pistola / SKU Manual", "📸 Cámara Automática (Móvil)"])

with tab_pistola:
    st.text_input("ESCANEE CÓDIGO O ESCRIBA EL SKU AQUÍ:", key="temp_pistola", on_change=procesar_pistola, placeholder="Dispare el láser o teclee el SKU...")
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
    st.info("💡 Usa Google Chrome o Safari para habilitar el lente trasero.")
    components.html(
        """
        <div id="reader" style="width:100%; max-width:450px; margin:0 auto; border-radius:12px; overflow:hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"></div>
        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
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
                let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(targetInput, decodedText);
                
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                targetInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // HACK DE AUTO-ENTER: Quita el foco para forzar el procesamiento instantáneo sin presionar botón
                targetInput.blur();
                
                if (window.html5QrCode && window.html5QrCode.getState() === 2) {
                    window.html5QrCode.pause(true);
                    setTimeout(() => window.html5QrCode.resume(), 2500);
                }
            }
        }
        
        function inicializarEscaner() {
            if (typeof Html5Qrcode !== "undefined") {
                window.html5QrCode = new Html5Qrcode("reader");
                const config = { fps: 15, qrbox: {width: 260, height: 160} };
                
                window.html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess)
                .catch(err => {
                    document.getElementById("reader").innerHTML = "<p style='color:#ef4444; font-weight:600; text-align:center; padding:20px; background:#fef2f2; border:1px solid #fee2e2; border-radius:8px;'>⚠️ Cámara no detectada o bloqueada<br><br><span style='font-weight:400; font-size:0.9rem; color:#64748b;'>Si estás en celular, no abras el link dentro de WhatsApp. Cópialo y pégalo directo en la app de Chrome o Safari para activar los permisos.</span></p>";
                });
            } else {
                setTimeout(inicializarEscaner, 200);
            }
        }
        setTimeout(inicializarEscaner, 300);
        </script>
        """, height=360
    )
    st.text_input("✏️ Código capturado (o entrada manual):", key="temp_camara", on_change=procesar_camara, placeholder="Escriba o edite el código...")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. LÓGICA DE BÚSQUEDA ROBUSTA (MALLA DE RED)
# ==========================================
codigo = st.session_state.codigo_final.strip().upper()

if codigo:
    skus_encontrados = []
    tienda_origen = "Desconocida"
    
    # A) Búsqueda en Hojas de Guías Diarias
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

    # B) Búsqueda Directa o por SKU Manual en Catálogo Maestro
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
        
        # LÓGICA DE ENTRADA DIRECTA POR TECLADO
        if not skus_encontrados and 'SKU' in df_maestro.columns:
            match_sku = df_maestro[df_maestro['SKU'] == codigo]
            if not match_sku.empty:
                skus_encontrados.append(codigo)
                tienda_origen = "Entrada Manual por SKU"

    # ==========================================
    # 6. INTERFAZ VISUAL VÍVIDA DE PRODUCTOS
    # ==========================================
    if skus_encontrados:
        total_productos = len(skus_encontrados)
        
        if total_productos > 1:
            st.error(f"### 🚨 ¡ALERTA! PEDIDO COMBINADO CON {total_productos} PRODUCTOS 🚨", icon="⚠️")
            st.markdown("<br>", unsafe_allow_html=True)
            
        for indice, sku_encontrado in enumerate(skus_encontrados):
            sku_limpio = str(sku_encontrado).strip().upper()
            fila_producto = df_maestro[df_maestro['SKU'] == sku_limpio]
            
            if not fila_producto.empty:
                titulo = fila_producto.iloc[0]['TITULO'] if 'TITULO' in fila_producto.columns else "Producto Técnico"
                variante = fila_producto.iloc[0]['VARIANTE'] if 'VARIANTE' in fila_producto.columns else "-"
                nombre_chino = fila_producto.iloc[0]['NOMBRE CHINO'] if 'NOMBRE CHINO' in fila_producto.columns else "-"
                
                caja = fila_producto.iloc[0]['CAJA'] if 'CAJA' in fila_producto.columns else "0"
                cinta = fila_producto.iloc[0]['CINTA NANO'] if 'CINTA NANO' in fila_producto.columns else "0"
                imagen_nombre = fila_producto.iloc[0]['IMAGEN'] if 'IMAGEN' in fila_producto.columns else None
                
                msg_caja = f"📦 {caja}" if str(caja).upper() not in ["0", "NAN", "SIN CAJA"] else "⚠️ Bolsa / Playo (Sin Caja)"
                msg_cinta = f"🔒 Lleva Cinta: {cinta}" if str(cinta).upper() not in ["0", "NAN", "SIN CINTA"] else "🚫 No requiere Cinta"

                # Llamada al buscador unificado en la raíz
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
                        st.warning(f"📸 Archivo de imagen '{imagen_nombre}' no indexado en GitHub.")
                
                # Renderizado estilizado
                st.markdown(f"<h1 class='product-title'>{titulo}</h1>", unsafe_allow_html=True)
                
                if pd.notna(variante) and str(variante).strip().upper() not in ["-", "NAN", ""]:
                    st.markdown(f"<h3 style='text-align: center; color: #475569; font-weight: 500;'>Variante: <b>{variante}</b></h3>", unsafe_allow_html=True)
                    
                if pd.notna(nombre_chino) and str(nombre_chino).strip().upper() not in ["-", "NAN", "SIN NOMBRE CHINO", ""]:
                    st.markdown(f"<p style='text-align: center; font-family: monospace; color: #94a3b8;'>Fábrica: {nombre_chino}</p>", unsafe_allow_html=True)
                
                st.markdown(f"<span class='sku-badge'>SKU: {sku_limpio}</span>", unsafe_allow_html=True)
                
                col_izq, col_der = st.columns(2)
                with col_izq:
                    st.info(f"**Instrucción de Caja:**\n### {msg_caja}")
                with col_der:
                    st.success(f"**Proceso de Sellado:**\n### {msg_cinta}")
                
                st.markdown(f"<p style='text-align: center; font-size: 0.85rem; color: #94a3b8; margin-top: 25px;'>Origen del Escaneo: {tienda_origen} | Ref: {codigo}</p>", unsafe_allow_html=True)
                
                if indice < total_productos - 1:
                    st.markdown("<hr style='border: 2px dashed #ef4444; margin: 45px 0;'>", unsafe_allow_html=True)
                
            else:
                st.error(f"❌ Mapeo Exitoso, pero el SKU `{sku_limpio}` no está dado de alta en la pestaña de 'Catalogo' en Google Sheets.")
    else:
        st.warning(f"El código o SKU `{codigo}` no existe en las listas logísticas ni en el catálogo maestro.")
