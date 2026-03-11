# Manual de Analítica — Plan de Cuentas & Heatmap 2026

## Índice

1. [Origen de los Datos](#1-origen-de-los-datos)
2. [Modelo de Scoring por Colores](#2-modelo-de-scoring-por-colores)
3. [Normalización de Datos](#3-normalización-de-datos)
4. [Dashboard General](#4-dashboard-general)
5. [Semáforo de Oportunidades](#5-semáforo-de-oportunidades)
6. [Análisis de Zonas](#6-análisis-de-zonas)
7. [Portafolio de Soluciones](#7-portafolio-de-soluciones)
8. [Perfilación de Cuentas](#8-perfilación-de-cuentas)
9. [Estrategias BDM](#9-estrategias-bdm)
10. [Resumen de Fórmulas](#10-resumen-de-fórmulas)

---

## 1. Origen de los Datos

### Fuente
El archivo **"PLAN DE CUENTAS Y HEATMAP 2026.xlsx"** se descarga en tiempo real desde Google Drive usando la API de Drive con una cuenta de servicio.

### Estructura del Excel
El archivo contiene las siguientes hojas relevantes:

| Hoja | Contenido | Filas |
|------|-----------|-------|
| **Total Cuentas Gamma** | Lista maestra de todos los clientes con información general, relacionamiento, áreas internas, entornos y estrategia | ~214 clientes |
| **[Nombre de BDM]** (18 hojas) | Cartera individual de cada ejecutivo con los mismos campos + **colores de heatmap** en las celdas de productos/servicios | 4-63 clientes cada una |

### Columnas del Excel (79 columnas organizadas en secciones)

| Sección | Columnas | Rango |
|---------|----------|-------|
| Información General | #, Zona, Tipo de Cuenta, Cliente, Descripción, Sector, Comercial | Col 2-8 |
| Relacionamiento y Contacto | Nivel de Relacionamiento, Valorización, C-level, Dirección, Gerente, Operativo, Influenciador | Col 9-15 |
| Relación con Áreas Internas | Ciberseguridad, Seguridad de la Información, Infraestructura, Riesgos, Transformación Digital, VP, Compras, Financiero, Jurídico, Mercadeo | Col 17-26 |
| Entornos del Cliente | Premisas, Cloud, OT/SCADA | Col 28-30 |
| Heatmap Productos | 37 productos (CyberAcademy, EDR, NGFW, SIEM, XDR, PAM, etc.) | Col 32-68 |
| Heatmap Servicios | 7 servicios (CSOC, Ethical Hacking, Consultoría, etc.) | Col 70-76 |
| Estrategia | Estrategia, Pasos a Seguir | Col 78-79 |

### Proceso de carga

1. **Descarga**: Se obtiene el archivo completo como `.xlsx` desde Google Drive
2. **Lectura master**: Se lee la hoja "Total Cuentas Gamma" para obtener la lista completa de clientes con su información general
3. **Extracción de heatmap**: Se recorren las 18 hojas individuales de BDM extrayendo los **colores de fondo** de cada celda del heatmap (la hoja Total NO tiene colores de heatmap, solo texto)
4. **Fusión**: Los scores de heatmap de las hojas BDM se unen al master por nombre de cliente (normalizado a mayúsculas y sin espacios)
5. **Cálculo de métricas derivadas**: Se calculan `score_heatmap` y `cobertura_productos` para cada cliente

> **¿Por qué se usan los colores y no el texto?**
> El texto en las celdas de heatmap es inconsistente (mezcla "Si", "si", "SI", nombres de productos, "No", vacío). Los colores de fondo, en cambio, siguen un estándar visual definido por el equipo: verde = foco, azul = interés, amarillo = atención, etc. El scoring por colores permite cuantificar de manera uniforme.

---

## 2. Modelo de Scoring por Colores

### Razón del modelo
El archivo Excel usa **colores de fondo** como lenguaje visual para indicar el estado de cada producto/servicio en cada cuenta. Este modelo traduce esos colores a valores numéricos comparables.

### Escala de scoring (0-5)

| Score | Colores (hex) | Etiqueta | Significado |
|-------|--------------|----------|-------------|
| **5** | `#00FF00`, `#92D050`, `#00B050` | Verde | Foco principal / máximo interés |
| **4** | `#00B0F0`, `#0070C0`, `#4472C4`, `#5B9BD5` | Azul | Interés alto / seguimiento activo |
| **3** | `#D9E2F3`, `#BDD7EE`, `#9CC2E5`, `#FFFF00`, `#FFC000`, `#FFD966` | Azul pálido / Amarillo | Cuenta identificada / oportunidad media |
| **2** | `#FF8C00`, `#ED7D31`, `#F4B084` | Naranja | Riesgo / necesita acción |
| **1** | `#FF0000`, `#C00000`, `#FF4444` | Rojo | Crítico / inactivo / perdido |
| **0** | `#D9D9D9`, `#FFFFFF`, grises, sin color | Gris / Blanco | Sin información / no aplica |

### Coincidencia de colores
El archivo Excel puede producir variaciones sutiles de color. El sistema usa dos métodos de coincidencia:

1. **Coincidencia exacta**: Si el hex del color coincide exactamente con alguno del mapa, se asigna su score
2. **Coincidencia por proximidad**: Si no hay coincidencia exacta, se calcula la **distancia euclidiana en espacio RGB** contra todos los colores del mapa:

```
distancia = √((R1-R2)² + (G1-G2)² + (B1-B2)²)
```

Si la distancia es ≤ 60 (umbral configurable), se asigna el score del color más cercano. Si supera el umbral, score = 0.

### Métricas derivadas por cliente

| Métrica | Fórmula | Descripción |
|---------|---------|-------------|
| `score_heatmap` | `Σ scores de todos los productos y servicios` | Score total del heatmap para el cliente |
| `cobertura_productos` | `count(score > 0)` | Cantidad de productos/servicios donde el cliente tiene presencia (score > 0) |

---

## 3. Normalización de Datos

### Sectores
Los sectores en el Excel tienen inconsistencias ("FINANCIERO", "Financiero", "financiero"). Se normalizan con un mapeo predefinido:

| Valor original | Valor normalizado |
|---------------|-------------------|
| "FINANCIERO", "Financiero" | Financiero |
| "GOBIERNO", "Gobierno" | Gobierno |
| "INDUSTRIA Y COMERCIO" | Industria y Comercio |
| "EDUCACION", "EDUCACIÓN" | Educación |
| (vacío / nulo) | Sin Sector |
| Otros | Title Case del valor original |

### Ejecutivos (Comercial)
Se normaliza a **Title Case** ("KAROL LOPEZ" → "Karol Lopez"). Valores vacíos se reemplazan con "Sin Asignar".

### Claves de fusión (cliente)
Para unir la hoja Total con las hojas BDM, los nombres de cliente se normalizan a **MAYÚSCULAS sin espacios laterales** (`str.strip().upper()`). Se usa la función `max()` para resolver duplicados (un cliente que aparece en más de una hoja BDM toma el score más alto).

### Auto-detección de columnas
Las columnas clave se detectan automáticamente por coincidencia parcial de nombre (case-insensitive). Esto permite que el sistema funcione aunque cambien los nombres exactos de columnas en el Excel:

| Campo | Aliases buscados |
|-------|-----------------|
| Cliente | "cliente", "client" |
| Comercial | "comercial", "ejecutivo", "bdm", "owner" |
| Zona | "zona", "region" |
| Sector | "sector", "industria" |
| Tipo de Cuenta | "tipo de cuenta", "tipo_cuenta" |

---

## 4. Dashboard General

### Propósito
Vista ejecutiva de alto nivel: responde a "¿cuántos clientes tenemos, cómo están distribuidos, y quién los atiende?"

### KPIs (fila superior)

| KPI | Cálculo |
|-----|---------|
| Total Clientes | `len(master)` — conteo simple de filas |
| Ejecutivos (BDM) | `master["Comercial"].nunique()` — valores únicos |
| Zonas | Conteo de zonas únicas en los datos |
| Sectores | `master["Sector"].nunique()` |
| Con Estrategia | `count(ESTRATEGIA no es nulo) / total * 100` |

### Visualizaciones

| Gráfico | Tipo | Datos | Razón |
|---------|------|-------|-------|
| Clientes por Ejecutivo | Barras horizontales | `value_counts()` de Comercial | Identificar carga de trabajo por BDM |
| Distribución por Zona | Donut (pie con hueco) | `value_counts()` de Zona | Ver concentración geográfica |
| Tipo de Cuenta | Barras verticales | `value_counts()` de Tipo | Comparar Base Instalada vs Nuevos Logos vs Reputación |
| Nivel de Relacionamiento | Barras verticales | `value_counts()` de Nivel | Evaluar profundidad de relaciones |
| Top Sectores | Barras horizontales (top 15) | `value_counts().head(15)` de Sector | Identificar industrias con mayor presencia |

**Código de colores del Nivel de Relacionamiento:**
- ALTO → Verde (`#92d050`)
- MEDIO → Amarillo (`#ffd966`)
- BAJO → Naranja (`#ed7d31`)
- NINGUNO → Gris (`#d9d9d9`)

---

## 5. Semáforo de Oportunidades

### Propósito
Clasificar cada cuenta en un sistema de **semáforo (Verde/Amarillo/Rojo)** para priorizar la gestión comercial. Responde a "¿qué cuentas necesitan atención inmediata y cuáles van bien?"

### Algoritmo de clasificación

**Paso 1 — Calcular umbrales dinámicos:**
```
Q75 = percentil 75 de score_heatmap (todos los clientes)
Q25 = percentil 25 de score_heatmap (todos los clientes)
MAX_COB = máximo de cobertura_productos
```

**Paso 2 — Clasificar cada cliente:**

| Semáforo | Condición | Interpretación |
|----------|-----------|----------------|
| 🟢 **Verde** | `score ≥ Q75` **Y** `cobertura ≥ 30% del máximo` | Alto potencial: buen score Y buena cobertura de portafolio |
| 🟡 **Amarillo** | `score ≥ Q25` **O** `cobertura ≥ 10% del máximo` | Oportunidad: tiene score o cobertura parcial |
| 🔴 **Rojo** | Todo lo demás | Sin cobertura: bajo score Y baja presencia de soluciones |

### Razón del diseño
- Se usan **percentiles** (no valores absolutos) porque son adaptativos: si los datos cambian, los umbrales se ajustan automáticamente
- El **Verde requiere ambas condiciones** (AND): un cliente no es "verde" solo por tener alto score si su cobertura es baja — necesita ambas dimensiones
- El **Amarillo acepta cualquiera** (OR): basta con que tenga algo de score o algo de cobertura para no ser clasificado como rojo
- Los **porcentajes de cobertura (30%, 10%)** se aplican sobre el máximo observado, lo que mantiene la escala relativa

### Visualizaciones

| Gráfico | Datos | Razón |
|---------|-------|-------|
| KPIs (4 métricas) | Conteo por semáforo + score promedio | Visión rápida del estado general |
| Semáforo por Sector | `groupby(Sector, semáforo).size()` — barras apiladas | Identificar sectores con mayor concentración de rojo |
| Semáforo por Ejecutivo | `groupby(Comercial, semáforo).size()` — barras apiladas | Comparar la salud de la cartera de cada BDM |
| Distribución general | Pie chart de conteos | Proporción global |
| Tabla de detalle | Filtrable por zona, tipo, color | Drill-down para acción específica |

### Filtros interactivos
- **Zona**: multiselect (default: todas)
- **Tipo de Cuenta**: multiselect (default: todos)
- **Semáforo**: multiselect (Verde/Amarillo/Rojo)

Todos los gráficos se recalculan dinámicamente al cambiar los filtros.

---

## 6. Análisis de Zonas

### Propósito
Análisis geográfico comparativo para decisiones de cobertura territorial. Responde a "¿cómo se comparan las zonas entre sí y dónde hay oportunidades?"

### Métricas por zona

| Métrica | Cálculo |
|---------|---------|
| Clientes | `count()` por zona |
| Ejecutivos | `nunique()` de Comercial por zona |
| Sectores | `nunique()` de Sector por zona |
| Score Promedio | `mean(score_heatmap)` por zona |
| Cobertura Promedio | `mean(cobertura_productos)` por zona |

Todas las métricas se calculan con `groupby(Zona).agg()` y se redondean a 1 decimal.

### Visualizaciones

| Gráfico | Datos | Razón |
|---------|-------|-------|
| Comparativa de clientes por zona | Barras con etiqueta | Ver volumen relativo |
| Score vs Cobertura por zona | Barras agrupadas (2 métricas) | Comparar calidad (score) y amplitud (cobertura) |
| Top sectores en la zona | `value_counts().head(12)` del sector filtrado | Identificar industrias dominantes |
| Tipo de cuenta (donut) | `value_counts()` de Tipo filtrado | Proporción de base instalada vs nuevos logos |
| Tabla de ejecutivos | `groupby(Comercial).agg(count, sum, mean)` | Rendimiento de cada BDM en la zona |

---

## 7. Portafolio de Soluciones

### Propósito
Análisis de penetración del portafolio de productos y servicios. Responde a "¿qué soluciones tienen mayor adopción, dónde hay gaps, y dónde hay oportunidades de cross-sell?"

### KPIs

| KPI | Fórmula |
|-----|---------|
| Productos/Servicios | Conteo de columnas de heatmap disponibles |
| Clientes Analizados | `count(score_heatmap > 0)` |
| Penetración Global | `celdas_activas / (clientes × soluciones) × 100` |
| Producto Líder | Solución con mayor suma de scores |

Donde:
- `celdas_activas` = cantidad de celdas con score > 0 en toda la matriz clientes × soluciones

### Análisis de adopción
Para cada solución (producto o servicio):
- **Clientes con presencia**: `count(score > 0)` por columna
- **Score acumulado**: `sum(score)` por columna
- **Clasificación**: Cada solución se etiqueta como "Producto" o "Servicio"

### Heatmap visual
Matriz de **Clientes × Soluciones** con valores de 0 a 5 y la siguiente escala de colores:

```
0.0 → #f5f5f5  (vacío)
0.2 → #ff4444  (crítico)
0.4 → #ed7d31  (riesgo)
0.6 → #ffd966  (atención)
0.8 → #5b9bd5  (alto)
1.0 → #92d050  (foco)
```

Solo se muestran clientes que tengan al menos 1 celda con score > 0.

### Análisis de Cross-Sell

| Métrica | Fórmula |
|---------|---------|
| Score Productos | `Σ scores de productos` por cliente |
| Score Servicios | `Σ scores de servicios` por cliente |
| Cobertura Productos | `count(score_producto > 0)` por cliente |
| Cobertura Servicios | `count(score_servicio > 0)` por cliente |

**Identificación de gaps**: Clientes donde `Score Productos > 0` AND `Score Servicios = 0`. Estos son clientes que ya compran productos pero no tienen ningún servicio contratado — oportunidad directa de venta cruzada.

### Scatter plot
- Eje X: Score de Productos
- Eje Y: Score de Servicios
- Color: Cobertura de Productos (gradiente rojo→amarillo→verde)
- Tamaño de burbuja: Cobertura de Servicios

---

## 8. Perfilación de Cuentas

### Propósito
Ficha individual por cuenta con vista 360°. Responde a "¿cuál es el estado completo de esta cuenta y qué oportunidades tiene?"

### Datos mostrados por cuenta

| Sección | Campos |
|---------|--------|
| Información General | Zona, Sector, Tipo de Cuenta, Ejecutivo, Nivel de Relacionamiento, Valorización |
| Descripción | Texto libre de la cuenta |
| Métricas | Score Heatmap, Cobertura de productos, % del portafolio cubierto |
| Productos | Barra horizontal por producto con score (0-5), ordenados de menor a mayor |
| Servicios | Barra horizontal por servicio con score (0-5) |
| Entornos | Premisas, Cloud, OT/SCADA — valores del Excel |
| Estrategia | Texto de estrategia actual |
| Pasos a Seguir | Texto de próximos pasos |

### Cobertura del portafolio
```
cobertura_pct = cobertura_productos / total_productos_y_servicios × 100
```

### Radar Chart (6-8 dimensiones)
Se construye un gráfico radar para visualizar el perfil multidimensional del cliente:

| Dimensión | Valor |
|-----------|-------|
| Ciberseguridad | 3 si tiene dato, 0 si no |
| Infraestructura | 3 si tiene dato, 0 si no |
| Riesgos | 3 si tiene dato, 0 si no |
| Transformación Digital | 3 si tiene dato, 0 si no |
| Compras | 3 si tiene dato, 0 si no |
| Productos | `promedio(scores de productos)` |
| Servicios | `promedio(scores de servicios)` |

**Razón**: Las áreas internas son binarias (tiene relación o no), mientras que los productos/servicios son promedios continuos (0-5). Esto permite ver de un vistazo si el cliente tiene relación con áreas clave y qué tan fuerte es su presencia en el portafolio.

### Código de colores en barras de productos/servicios

| Rango | Color |
|-------|-------|
| Score ≥ 4 | Verde (`#92d050`) |
| Score ≥ 3 | Azul (`#5b9bd5`) |
| Score ≥ 2 | Amarillo (`#ffd966`) |
| Score ≥ 1 | Naranja (`#ed7d31`) |
| Score = 0 | Gris (`#e0e0e0`) |

---

## 9. Estrategias BDM

### Propósito
Gestión y seguimiento de las estrategias definidas por los ejecutivos de desarrollo de negocio. Responde a "¿qué cuentas tienen estrategia definida, cuáles no, y cuál es el estado de cada BDM?"

### KPIs

| KPI | Fórmula |
|-----|---------|
| Cuentas | `count()` del ejecutivo seleccionado (o total) |
| Con Estrategia | `count(ESTRATEGIA no nulo)` + porcentaje |
| Con Pasos Definidos | `count(PASOS A SEGUIR no nulo)` + porcentaje |
| Score Promedio | `mean(score_heatmap)` del ejecutivo/total |

### Cobertura por ejecutivo (vista "Todos")
```
Por cada ejecutivo:
  Con_Estrategia = count(ESTRATEGIA no nulo)
  Sin_Estrategia = Total - Con_Estrategia
  Porcentaje = Con_Estrategia / Total × 100
```

Se visualiza como barra apilada horizontal (verde = con estrategia, gris = sin estrategia).

### Tarjetas de cuenta
Cada cuenta se muestra como un expander con:
- **Header**: Nombre del cliente, sector, score, tipo de cuenta
- **Detalle**: Ejecutivo, zona, score, cantidad de soluciones activas
- **Estrategia**: Texto completo de la estrategia definida (o "sin estrategia definida")
- **Pasos a seguir**: Texto completo (o "sin pasos definidos")
- **Soluciones activas**: Lista de productos/servicios con score > 0

### Filtros
- **Ejecutivo**: Selector (incluye "Todos")
- **Modo de visualización**: Todas / Con estrategia / Sin estrategia

---

## 10. Resumen de Fórmulas

### Fórmulas core

```
score_color(hex) = {
    coincidencia exacta → score del mapa
    coincidencia por proximidad (distancia RGB ≤ 60) → score más cercano
    sin coincidencia → 0
}

score_heatmap(cliente) = Σ score_color(celda) para todos los productos y servicios

cobertura_productos(cliente) = count(score_color(celda) > 0)

penetración_global = Σ(score > 0 en toda la matriz) / (clientes × soluciones) × 100

semáforo(cliente) = {
    Verde   si score ≥ Q75(scores) AND cobertura ≥ 30% × max(coberturas)
    Amarillo si score ≥ Q25(scores) OR  cobertura ≥ 10% × max(coberturas)
    Rojo    en otro caso
}

distancia_rgb(c1, c2) = √((R1-R2)² + (G1-G2)² + (B1-B2)²)
```

### Agregaciones principales

| Nivel | Métricas calculadas |
|-------|-------------------|
| Por cliente | score_heatmap, cobertura_productos, semáforo, cobertura_pct |
| Por ejecutivo | count clientes, sum/mean scores, con/sin estrategia |
| Por zona | count clientes, nunique ejecutivos/sectores, mean score/cobertura |
| Por sector | count clientes, distribución de semáforo |
| Por solución | count clientes con presencia, sum score acumulado |

---

*Documento generado automáticamente a partir del código fuente de la aplicación.*
*Última actualización: Marzo 2026*
