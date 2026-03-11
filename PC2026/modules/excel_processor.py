"""
Procesador de Excel: lee valores y colores de fondo de cada celda usando openpyxl.

Estructura conocida del archivo "PLAN DE CUENTAS Y HEATMAP 2026.xlsx":
  - Fila 9:  secciones (Info General, Relacionamiento, Areas, Heatmap, etc.)
  - Fila 11: headers de columnas
  - Fila 12+: datos
  - Col 2-15:  info general + relacionamiento
  - Col 17-26: relacion con areas internas
  - Col 28-30: entornos del cliente
  - Col 32-68: heatmap productos
  - Col 70-76: heatmap servicios
  - Col 78-79: estrategia
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import PatternFill


# ---------------------------------------------------------------------------
# Resolucion de colores de tema de Excel (Office default theme)
# ---------------------------------------------------------------------------

THEME_COLORS = [
    (255, 255, 255),  # 0 - lt1 (blanco)
    (0, 0, 0),        # 1 - dk1 (negro)
    (68, 114, 196),   # 4 - accent1 (azul)
    (237, 125, 49),   # 5 - accent2 (naranja)
    (165, 165, 165),  # 6 - accent3 (gris)
    (255, 192, 0),    # 7 - accent4 (amarillo)
    (91, 155, 213),   # 8 - accent5 (azul claro)
    (112, 173, 71),   # 9 - accent6 (verde)
    (158, 72, 14),    # 2 - lt2
    (99, 99, 99),     # 3 - dk2
]

_THEME_INDEX_MAP = {0: 0, 1: 1, 2: 8, 3: 9, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7}


def _apply_tint(rgb: tuple[int, int, int], tint: float) -> tuple[int, int, int]:
    r, g, b = rgb
    if tint > 0:
        r = int(r + (255 - r) * tint)
        g = int(g + (255 - g) * tint)
        b = int(b + (255 - b) * tint)
    elif tint < 0:
        r = int(r * (1 + tint))
        g = int(g * (1 + tint))
        b = int(b * (1 + tint))
    return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))


def _resolve_theme_color(theme_idx: int, tint: float) -> str | None:
    mapped = _THEME_INDEX_MAP.get(theme_idx)
    if mapped is None or mapped >= len(THEME_COLORS):
        return None
    base = THEME_COLORS[mapped]
    r, g, b = _apply_tint(base, tint)
    return f"#{r:02X}{g:02X}{b:02X}"


# ---------------------------------------------------------------------------
# Extraccion de color de celda
# ---------------------------------------------------------------------------

def _cell_bg_hex(cell: Cell) -> str | None:
    fill: PatternFill = cell.fill
    if fill.patternType is None or fill.patternType == "none":
        return None
    color = fill.fgColor
    if color is None or color.type is None:
        return None
    if color.type == "rgb" and color.rgb:
        rgb = str(color.rgb)
        if len(rgb) == 8:
            rgb = rgb[2:]
        if len(rgb) == 6 and rgb != "000000":
            return f"#{rgb}"
    elif color.type == "theme":
        tint = float(color.tint) if color.tint else 0.0
        return _resolve_theme_color(int(color.theme), tint)
    elif color.type == "indexed" and color.indexed is not None:
        return f"indexed:{color.indexed}"
    return None


# ---------------------------------------------------------------------------
# Auto-deteccion de fila de headers
# ---------------------------------------------------------------------------

# Palabras clave que indican una fila de encabezados del plan de cuentas
_HEADER_KEYWORDS = {
    "cliente", "zona", "sector", "comercial", "tipo de cuenta",
    "nivel de relacionamiento", "#", "ciberseguridad", "descripción",
}


def _detect_header_row(ws, max_scan: int = 20) -> int:
    """
    Detecta automaticamente la fila de headers escaneando las primeras filas.
    Busca la fila con mayor cantidad de celdas con texto que coincidan con
    palabras clave conocidas del plan de cuentas.

    Returns:
        Numero de fila (1-based). Default 1 si no detecta nada.
    """
    best_row = 1
    best_score = 0

    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan), start=1):
        vals = [str(c.value).strip().lower() for c in row if c.value]
        if len(vals) < 3:
            continue

        # Contar cuantos headers conocidos hay en esta fila
        score = sum(1 for v in vals if any(kw in v for kw in _HEADER_KEYWORDS))
        # Bonus por tener muchas celdas con texto (tipico de fila de headers)
        if len(vals) >= 10:
            score += len(vals) // 5

        if score > best_score:
            best_score = score
            best_row = row_idx

    return best_row


# ---------------------------------------------------------------------------
# Estructura de datos
# ---------------------------------------------------------------------------

# Hojas que NO contienen datos de cuentas (se excluyen del analisis)
SKIP_SHEETS = {
    "indice", "introduccion y objetivos", "criterios de clasificación",
    "criterios de clasificacion", "terminos y condiciones", "hoja 2",
}

# Secciones de columnas del plan de cuentas (rangos 1-based)
SECTIONS = {
    "info_general": (2, 8),       # #, Zona, Tipo, Cliente, Descripcion, Sector, Comercial
    "relacionamiento": (9, 15),   # Nivel, Valorizacion, C-level, Direccion, Gerente, Op, Influenciador
    "areas_internas": (17, 26),   # Ciberseguridad, Seg Info, Infra, Riesgos, TD, VP, Compras, etc.
    "entornos": (28, 30),         # Premisas, Cloud, OT/SCADA
    "heatmap_productos": (32, 68),  # CyberAcademy, EDR, ... hasta Criptografia Post-Cuantica
    "heatmap_servicios": (70, 76),  # CSOC, Vulnerabilidades, Ethical Hacking, etc.
    "estrategia": (78, 79),       # Estrategia, Pasos a seguir
}


@dataclass
class SheetData:
    """Datos extraidos de una hoja del Excel."""
    name: str
    df: pd.DataFrame
    colors: pd.DataFrame
    raw_headers: list[str] = field(default_factory=list)
    header_row: int = 1
    sections: dict[str, list[str]] = field(default_factory=dict)


def _build_section_map(headers: list[str], col_offset: int) -> dict[str, list[str]]:
    """Mapea cada seccion a las columnas reales que le corresponden."""
    section_map = {}
    for sec_name, (start, end) in SECTIONS.items():
        cols = []
        for i in range(start, end + 1):
            idx = i - col_offset
            if 0 <= idx < len(headers) and headers[idx] not in (f"col_{idx}", ""):
                cols.append(headers[idx])
        if cols:
            section_map[sec_name] = cols
    return section_map


def read_worksheet_with_colors(
    ws,
    header_row: int | None = None,
) -> SheetData:
    """
    Lee una hoja pre-cargada de openpyxl y retorna valores + colores de cada celda.
    Auto-detecta la fila de headers si no se especifica.
    """
    rows = list(ws.iter_rows(min_row=1))
    if not rows:
        return SheetData(name=ws.title, df=pd.DataFrame(), colors=pd.DataFrame())

    # Auto-detectar fila de headers
    if header_row is None:
        header_row = _detect_header_row(ws)

    header_cells = rows[header_row - 1]

    # Encontrar primera columna con datos (skip col A que suele estar vacia)
    col_offset = 0
    for i, c in enumerate(header_cells):
        if c.value:
            col_offset = i
            break

    # Headers desde col_offset
    headers = []
    for i, c in enumerate(header_cells):
        if i < col_offset:
            continue
        if c.value:
            headers.append(str(c.value).strip())
        else:
            headers.append(f"col_{i}")

    # Datos y colores desde la fila siguiente al header
    data_rows = rows[header_row:]
    values = []
    color_rows = []

    for row in data_rows:
        cells = list(row[col_offset: col_offset + len(headers)])
        # Saltar filas completamente vacias
        if not any(c.value for c in cells):
            continue
        val_row = [c.value for c in cells]
        clr_row = [_cell_bg_hex(c) for c in cells]
        values.append(val_row)
        color_rows.append(clr_row)

    df = pd.DataFrame(values, columns=headers) if values else pd.DataFrame(columns=headers)
    colors = pd.DataFrame(
        color_rows, columns=[f"{h}_color" for h in headers]
    ) if color_rows else pd.DataFrame(columns=[f"{h}_color" for h in headers])

    # Mapeo de secciones
    section_map = _build_section_map(headers, col_offset)

    return SheetData(
        name=ws.title,
        df=df,
        colors=colors,
        raw_headers=headers,
        header_row=header_row,
        sections=section_map,
    )
