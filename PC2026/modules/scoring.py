"""
Modelo de puntuacion basado en colores de celda del heatmap.

Asigna puntajes numericos a cada color de fondo detectado en el Excel.
Los colores se normalizan y agrupan por proximidad para manejar variaciones.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

# ---------------------------------------------------------------------------
# Mapeo de colores por defecto (configurable)
# ---------------------------------------------------------------------------
# Colores tipicos de heatmap en Plan de Cuentas.
# Formato: hex_lower -> (score, label, descripcion)

DEFAULT_COLOR_MAP: dict[str, tuple[int, str, str]] = {
    # === Colores reales detectados en PLAN DE CUENTAS Y HEATMAP 2026.xlsx ===

    # Verdes (positivo / activo / foco) — score 5
    "#00ff00": (5, "verde_fuerte", "Foco principal / maximo interes"),
    "#92d050": (5, "verde_lima", "Foco principal"),
    "#00b050": (5, "verde_oscuro", "Foco principal"),

    # Azul claro / seguimiento activo — score 4
    "#00b0f0": (4, "azul_claro", "Interes alto / seguimiento activo"),
    "#0070c0": (4, "azul_oscuro", "Interes alto / estrategico"),
    "#4472c4": (4, "azul_medio", "Interes alto"),
    "#5b9bd5": (4, "azul", "Interes alto"),
    "#2e75b5": (4, "azul_header", "Encabezado / categoria"),

    # Azul palido / cobertura parcial — score 3
    "#9cc2e5": (3, "azul_palido_medio", "Cobertura parcial / en proceso"),
    "#bdd7ee": (3, "azul_palido", "Interes moderado"),
    "#d9e2f3": (3, "azul_muy_claro", "Cuenta identificada / en revision"),
    "#deeaf6": (3, "azul_hielo", "Cuenta identificada"),

    # Amarillos (atencion / oportunidad media) — score 3
    "#ffff00": (3, "amarillo", "Atencion / oportunidad media"),
    "#ffc000": (3, "naranja_claro", "Atencion / seguimiento"),
    "#ffd966": (3, "amarillo_suave", "Oportunidad media"),

    # Naranjas (riesgo / necesita accion) — score 2
    "#ff8c00": (2, "naranja", "Riesgo / necesita accion"),
    "#ed7d31": (2, "naranja_excel", "Riesgo medio"),
    "#f4b084": (2, "salmon", "Riesgo bajo-medio"),

    # Rojos (critico / inactivo / perdido) — score 1
    "#ff0000": (1, "rojo", "Critico / inactivo"),
    "#c00000": (1, "rojo_oscuro", "Perdido / critico"),
    "#ff4444": (1, "rojo_claro", "En riesgo"),

    # Grises (sin informacion / no aplica) — score 0
    "#d9d9d9": (0, "gris_claro", "Sin informacion"),
    "#d8d8d8": (0, "gris_claro2", "Sin informacion"),
    "#a5a5a5": (0, "gris_medio", "Estructura / no aplica"),
    "#bfbfbf": (0, "gris", "No aplica"),
    "#808080": (0, "gris_oscuro", "No aplica"),

    # Blanco / sin relleno — score 0
    "#ffffff": (0, "blanco", "Sin dato"),
}


@dataclass
class ColorScore:
    hex_color: str | None
    score: int
    label: str
    description: str


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convierte '#RRGGBB' a tupla (R, G, B)."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(c1: str, c2: str) -> float:
    """Distancia euclidiana en espacio RGB entre dos colores hex."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def score_color(
    hex_color: str | None,
    color_map: dict | None = None,
    distance_threshold: float = 60.0,
) -> ColorScore:
    """
    Asigna puntuacion a un color de celda.

    Busca primero coincidencia exacta; si no, busca el color mas cercano
    dentro del umbral de distancia.
    """
    if hex_color is None or not hex_color.startswith("#"):
        return ColorScore(hex_color, 0, "sin_color", "Sin color de fondo")

    cmap = color_map or DEFAULT_COLOR_MAP
    key = hex_color.lower()

    # Coincidencia exacta
    if key in cmap:
        s, label, desc = cmap[key]
        return ColorScore(key, s, label, desc)

    # Buscar mas cercano por distancia RGB
    best_dist = float("inf")
    best_key = None
    for ref_hex in cmap:
        if not ref_hex.startswith("#"):
            continue
        d = _color_distance(key, ref_hex)
        if d < best_dist:
            best_dist = d
            best_key = ref_hex

    if best_key and best_dist <= distance_threshold:
        s, label, desc = cmap[best_key]
        return ColorScore(key, s, f"{label}_aprox", desc)

    # Color no reconocido
    return ColorScore(key, 0, "desconocido", f"Color {key} no mapeado")


def score_color_dataframe(
    colors_df: pd.DataFrame,
    color_map: dict | None = None,
) -> pd.DataFrame:
    """
    Convierte un DataFrame de colores hex a un DataFrame de scores numericos.

    Args:
        colors_df: DataFrame donde cada celda es un hex color o None.
        color_map: Mapeo personalizado (opcional).

    Returns:
        DataFrame del mismo shape con scores enteros.
    """
    return colors_df.map(lambda c: score_color(c, color_map).score)


def score_color_labels(
    colors_df: pd.DataFrame,
    color_map: dict | None = None,
) -> pd.DataFrame:
    """Retorna DataFrame con labels descriptivos en vez de scores."""
    return colors_df.map(lambda c: score_color(c, color_map).label)


def detect_unique_colors(colors_df: pd.DataFrame) -> dict[str, int]:
    """
    Detecta todos los colores unicos en el DataFrame y cuenta sus ocurrencias.
    Util para diagnosticar que colores tiene el archivo y ajustar el mapa.
    """
    counts: dict[str, int] = {}
    for col in colors_df.columns:
        for val in colors_df[col].dropna():
            if val and isinstance(val, str):
                counts[val] = counts.get(val, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def build_score_summary(
    values_df: pd.DataFrame,
    scores_df: pd.DataFrame,
    index_col: str,
) -> pd.DataFrame:
    """
    Construye un resumen de puntuacion por entidad (cuenta/cliente).

    Suma los scores de todas las columnas de color para cada fila,
    usando index_col como identificador.
    """
    if index_col not in values_df.columns:
        return pd.DataFrame()

    summary = pd.DataFrame()
    summary[index_col] = values_df[index_col]

    score_cols = [c for c in scores_df.columns if c.endswith("_color")]
    if score_cols:
        summary["score_total"] = scores_df[score_cols].sum(axis=1)
        summary["score_promedio"] = scores_df[score_cols].mean(axis=1).round(2)
        summary["celdas_evaluadas"] = scores_df[score_cols].count(axis=1)
        summary["celdas_con_color"] = (scores_df[score_cols] > 0).sum(axis=1)
    else:
        summary["score_total"] = 0
        summary["score_promedio"] = 0.0
        summary["celdas_evaluadas"] = 0
        summary["celdas_con_color"] = 0

    return summary.sort_values("score_total", ascending=False).reset_index(drop=True)
