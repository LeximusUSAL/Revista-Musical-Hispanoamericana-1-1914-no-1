#!/usr/bin/env python3
"""
Visor de Transcripciones - Generador de HTML autocontenido
Genera una página HTML portable que muestra pares imagen/texto
con navegación entre páginas.
"""

import os
import sys
import base64
import html
import glob
from pathlib import Path


def obtener_carpeta(mensaje):
    """Solicita una carpeta al usuario y valida que exista."""
    while True:
        carpeta = input(mensaje).strip()
        # Eliminar comillas si el usuario arrastra la carpeta al terminal
        carpeta = carpeta.strip("'\"")
        # Interpretar barras invertidas de escape del shell (e.g. carpeta\ con\ espacios)
        carpeta = carpeta.replace("\\ ", " ")
        if os.path.isdir(carpeta):
            return carpeta
        print(f"  Error: '{carpeta}' no es una carpeta válida. Inténtalo de nuevo.")


def imagen_a_base64(ruta_imagen):
    """Convierte una imagen JPG a una cadena base64."""
    with open(ruta_imagen, "rb") as f:
        datos = f.read()
    return base64.b64encode(datos).decode("utf-8")


def leer_texto(ruta_txt):
    """Lee un archivo de texto probando varias codificaciones."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(ruta_txt, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Último recurso
    with open(ruta_txt, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def emparejar_archivos(carpeta_img, carpeta_txt):
    """Empareja JPGs con TXTs por nombre base."""
    # Recoger imágenes (jpg y jpeg, case-insensitive)
    imagenes = {}
    for ext in ("*.jpg", "*.JPG", "*.jpeg", "*.JPEG"):
        for ruta in glob.glob(os.path.join(carpeta_img, ext)):
            nombre_base = Path(ruta).stem.lower()
            imagenes[nombre_base] = ruta

    # Recoger textos
    textos = {}
    for ext in ("*.txt", "*.TXT"):
        for ruta in glob.glob(os.path.join(carpeta_txt, ext)):
            nombre_base = Path(ruta).stem.lower()
            textos[nombre_base] = ruta

    # Emparejar
    nombres_comunes = sorted(set(imagenes.keys()) & set(textos.keys()))
    pares = []
    for nombre in nombres_comunes:
        pares.append({
            "nombre": Path(imagenes[nombre]).stem,
            "ruta_img": imagenes[nombre],
            "ruta_txt": textos[nombre],
        })

    return pares


def generar_html(pares, ruta_salida):
    """Genera el archivo HTML autocontenido."""
    print(f"\nGenerando HTML con {len(pares)} páginas...")

    # Preparar datos de cada página
    paginas_js = []
    for i, par in enumerate(pares):
        print(f"  Procesando {i+1}/{len(pares)}: {par['nombre']}", end="\r")
        b64 = imagen_a_base64(par["ruta_img"])
        texto = leer_texto(par["ruta_txt"])
        texto_escaped = html.escape(texto)
        # Escapar para insertar en JS
        texto_js = texto_escaped.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        paginas_js.append(
            f'  {{\n'
            f'    nombre: `{html.escape(par["nombre"])}`,\n'
            f'    imagen: "data:image/jpeg;base64,{b64}",\n'
            f'    texto: `{texto_js}`\n'
            f'  }}'
        )

    paginas_str = ",\n".join(paginas_js)
    print()

    html_contenido = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Visor de Transcripciones</title>
<style>
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  /* Barra superior */
  .toolbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 20px;
    background: #16213e;
    border-bottom: 1px solid #0f3460;
    flex-shrink: 0;
    min-height: 50px;
  }}
  .toolbar h1 {{
    font-size: 16px;
    font-weight: 600;
    color: #e94560;
  }}
  .nav-controls {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .nav-btn {{
    background: #0f3460;
    color: #e0e0e0;
    border: 1px solid #533483;
    padding: 6px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.2s;
  }}
  .nav-btn:hover:not(:disabled) {{
    background: #533483;
  }}
  .nav-btn:disabled {{
    opacity: 0.4;
    cursor: default;
  }}
  .page-info {{
    font-size: 14px;
    color: #a0a0b0;
    min-width: 120px;
    text-align: center;
  }}
  .page-name {{
    font-size: 13px;
    color: #e94560;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  /* Contenido principal */
  .viewer {{
    display: flex;
    flex: 1;
    overflow: hidden;
  }}
  /* Panel imagen */
  .panel-imagen {{
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: auto;
    background: #0d0d1a;
    padding: 10px;
    position: relative;
  }}
  .panel-imagen img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: 4px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  /* Separador arrastrable */
  .divider {{
    width: 6px;
    background: #0f3460;
    cursor: col-resize;
    flex-shrink: 0;
    transition: background 0.2s;
  }}
  .divider:hover, .divider.active {{
    background: #e94560;
  }}
  /* Panel texto */
  .panel-texto {{
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    background: #16213e;
    font-family: "Courier New", Courier, monospace;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
    color: #d0d0e0;
  }}
  /* Barra inferior */
  .statusbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 20px;
    background: #16213e;
    border-top: 1px solid #0f3460;
    font-size: 12px;
    color: #707090;
    flex-shrink: 0;
  }}
  /* Selector de página */
  .page-select {{
    background: #0f3460;
    color: #e0e0e0;
    border: 1px solid #533483;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 13px;
  }}
  /* Zoom */
  .zoom-controls {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .zoom-btn {{
    background: #0f3460;
    color: #e0e0e0;
    border: 1px solid #533483;
    width: 28px;
    height: 28px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
  }}
  .zoom-btn:hover {{
    background: #533483;
  }}
  .zoom-level {{
    font-size: 12px;
    color: #a0a0b0;
    min-width: 40px;
    text-align: center;
  }}
  /* Atajos teclado */
  .shortcuts {{
    font-size: 11px;
    color: #505070;
  }}
  .shortcuts kbd {{
    background: #0f3460;
    padding: 1px 5px;
    border-radius: 3px;
    border: 1px solid #533483;
    font-size: 11px;
  }}
  /* Responsive */
  @media (max-width: 768px) {{
    .viewer {{
      flex-direction: column;
    }}
    .divider {{
      width: 100%;
      height: 6px;
      cursor: row-resize;
    }}
    .panel-imagen, .panel-texto {{
      flex: none;
      height: 50%;
    }}
  }}
</style>
</head>
<body>

<div class="toolbar">
  <h1>Visor de Transcripciones</h1>
  <div class="nav-controls">
    <button class="nav-btn" id="btnPrev" onclick="irPagina(paginaActual - 1)">&larr; Anterior</button>
    <select class="page-select" id="pageSelect" onchange="irPagina(parseInt(this.value))"></select>
    <span class="page-info" id="pageInfo"></span>
    <button class="nav-btn" id="btnNext" onclick="irPagina(paginaActual + 1)">Siguiente &rarr;</button>
  </div>
  <span class="page-name" id="pageName"></span>
</div>

<div class="viewer">
  <div class="panel-imagen" id="panelImg">
    <img id="visorImg" src="" alt="Imagen escaneada">
  </div>
  <div class="divider" id="divider"></div>
  <div class="panel-texto" id="panelTxt"></div>
</div>

<div class="statusbar">
  <span class="shortcuts">
    <kbd>&larr;</kbd> <kbd>&rarr;</kbd> navegar &nbsp;
    <kbd>+</kbd> <kbd>-</kbd> zoom imagen &nbsp;
    <kbd>F</kbd> pantalla completa
  </span>
  <div class="zoom-controls">
    <button class="zoom-btn" onclick="cambiarZoom(-10)">−</button>
    <span class="zoom-level" id="zoomLevel">100%</span>
    <button class="zoom-btn" onclick="cambiarZoom(10)">+</button>
  </div>
  <span id="totalInfo"></span>
</div>

<script>
const paginas = [
{paginas_str}
];

let paginaActual = 0;
let zoom = 100;

// Inicializar selector
const sel = document.getElementById("pageSelect");
paginas.forEach((p, i) => {{
  const opt = document.createElement("option");
  opt.value = i;
  opt.textContent = p.nombre;
  sel.appendChild(opt);
}});

document.getElementById("totalInfo").textContent = paginas.length + " páginas";

function irPagina(n) {{
  if (n < 0 || n >= paginas.length) return;
  paginaActual = n;
  const p = paginas[n];
  document.getElementById("visorImg").src = p.imagen;
  document.getElementById("panelTxt").innerHTML = p.texto;
  document.getElementById("pageInfo").textContent = (n + 1) + " / " + paginas.length;
  document.getElementById("pageName").textContent = p.nombre;
  document.getElementById("btnPrev").disabled = (n === 0);
  document.getElementById("btnNext").disabled = (n === paginas.length - 1);
  sel.value = n;
  // Reset scroll del texto al cambiar de página
  document.getElementById("panelTxt").scrollTop = 0;
}}

function cambiarZoom(delta) {{
  zoom = Math.max(20, Math.min(300, zoom + delta));
  document.getElementById("visorImg").style.maxWidth = zoom + "%";
  document.getElementById("visorImg").style.maxHeight = zoom + "%";
  document.getElementById("zoomLevel").textContent = zoom + "%";
}}

// Atajos de teclado
document.addEventListener("keydown", function(e) {{
  if (e.target.tagName === "SELECT" || e.target.tagName === "INPUT") return;
  switch(e.key) {{
    case "ArrowLeft":
      irPagina(paginaActual - 1);
      e.preventDefault();
      break;
    case "ArrowRight":
      irPagina(paginaActual + 1);
      e.preventDefault();
      break;
    case "+":
    case "=":
      cambiarZoom(10);
      break;
    case "-":
      cambiarZoom(-10);
      break;
    case "f":
    case "F":
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen();
      }} else {{
        document.exitFullscreen();
      }}
      break;
  }}
}});

// Divisor arrastrable
(function() {{
  const divider = document.getElementById("divider");
  const panelImg = document.getElementById("panelImg");
  const panelTxt = document.getElementById("panelTxt");
  let arrastrando = false;

  divider.addEventListener("mousedown", function(e) {{
    arrastrando = true;
    divider.classList.add("active");
    e.preventDefault();
  }});

  document.addEventListener("mousemove", function(e) {{
    if (!arrastrando) return;
    const viewer = document.querySelector(".viewer");
    const rect = viewer.getBoundingClientRect();
    const porcentaje = ((e.clientX - rect.left) / rect.width) * 100;
    if (porcentaje > 15 && porcentaje < 85) {{
      panelImg.style.flex = "none";
      panelImg.style.width = porcentaje + "%";
      panelTxt.style.flex = "none";
      panelTxt.style.width = (100 - porcentaje) + "%";
    }}
  }});

  document.addEventListener("mouseup", function() {{
    if (arrastrando) {{
      arrastrando = false;
      divider.classList.remove("active");
    }}
  }});
}})();

// Mostrar primera página
if (paginas.length > 0) {{
  irPagina(0);
}}
</script>
</body>
</html>'''

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html_contenido)

    tamano = os.path.getsize(ruta_salida)
    if tamano > 1024 * 1024:
        tamano_str = f"{tamano / (1024*1024):.1f} MB"
    else:
        tamano_str = f"{tamano / 1024:.1f} KB"

    print(f"\n  Archivo generado: {ruta_salida}")
    print(f"  Tamaño: {tamano_str}")
    print(f"  Páginas: {len(pares)}")


def main():
    print("=" * 60)
    print("  VISOR DE TRANSCRIPCIONES")
    print("  Generador de HTML autocontenido")
    print("=" * 60)
    print()

    carpeta_img = obtener_carpeta("Carpeta con las imágenes JPG: ")
    carpeta_txt = obtener_carpeta("Carpeta con los archivos TXT: ")

    pares = emparejar_archivos(carpeta_img, carpeta_txt)

    if not pares:
        print("\nNo se encontraron pares imagen/texto con nombres coincidentes.")
        print("Asegúrate de que los archivos tengan el mismo nombre base:")
        print("  pagina_001.jpg  <->  pagina_001.txt")
        sys.exit(1)

    print(f"\nSe encontraron {len(pares)} pares imagen/texto:")
    for p in pares[:5]:
        print(f"  {p['nombre']}")
    if len(pares) > 5:
        print(f"  ... y {len(pares) - 5} más")

    # Nombre de salida
    nombre_salida = input("\nNombre del archivo HTML de salida (Enter = visor_transcripciones.html): ").strip()
    if not nombre_salida:
        nombre_salida = "visor_transcripciones.html"
    if not nombre_salida.endswith(".html"):
        nombre_salida += ".html"

    ruta_salida = os.path.join(os.getcwd(), nombre_salida)
    generar_html(pares, ruta_salida)
    print("\n  Listo. Abre el archivo en cualquier navegador.")


if __name__ == "__main__":
    main()
