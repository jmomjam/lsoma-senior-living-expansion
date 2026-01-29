#!/usr/bin/env Rscript
# ==============================================================================
# GENERADOR DE FIGURAS PARA INFORME L-SOMA
# Ejecutar: Rscript generar_figuras.R
# ==============================================================================

# --- INSTALACIÓN DE PAQUETES ---
# micromamba install -c conda-forge r-ggplot2 r-dplyr r-sf r-viridis r-scales \
#   r-arrow r-tidyr r-ggthemes r-patchwork r-rnaturalearth r-rnaturalearthdata \
#   r-giscoR

library(ggplot2)
library(dplyr)
library(sf)
library(viridis)
library(scales)
library(arrow)
library(tidyr)
library(ggthemes)
library(patchwork)
library(rnaturalearth)
library(rnaturalearthdata)

# Configuración global - tema limpio
theme_set(theme_minimal(base_size = 11))
options(scipen = 999)

# Rutas
DATA_DIR <- "../datos"
SHAPE_DIR <- "../datos/seccionado_2024"
OUTPUT_DIR <- "."

cat("=== GENERADOR DE FIGURAS L-SOMA (PDF Vectorial) ===\n\n")

# ------------------------------------------------------------------------------
# CARGAR DATOS GEOGRÁFICOS
# ------------------------------------------------------------------------------
cat(">>> Cargando mapas base...\n")

# Mapa de España (contorno país)
spain <- ne_countries(scale = "medium", country = "Spain", returnclass = "sf")
europe <- ne_countries(scale = "medium", continent = "Europe", returnclass = "sf")

# Intentar cargar CCAA desde giscoR o usar alternativa
tryCatch({
  library(giscoR)
  ccaa <- gisco_get_nuts(country = "ES", nuts_level = 2, resolution = "10", year = "2021")
  cat("   ✓ Comunidades Autónomas cargadas desde giscoR\n")
}, error = function(e) {
  cat("   ℹ giscoR no disponible, usando contorno simple de España\n")
  ccaa <<- NULL
})

# Cargar secciones censales para Madrid
cat(">>> Cargando secciones censales...\n")
tryCatch({
  secciones <- st_read(file.path(SHAPE_DIR, "SECC_CE_20240101.shp"), quiet = TRUE)
  # Filtrar Madrid (códigos que empiezan por 28)
  madrid_secciones <- secciones %>% filter(grepl("^28", CUSEC))
  cat("   ✓ Secciones censales cargadas (Madrid:", nrow(madrid_secciones), "secciones)\n")
}, error = function(e) {
  cat("   ✗ Error cargando shapefile:", e$message, "\n")
  madrid_secciones <<- NULL
})

# ==============================================================================
# FIGURA 1: Heatmap de Matriz P (100 secciones - Muestreo Aleatorio Simple)
# ==============================================================================
cat("\n>>> Generando Figura 1: Heatmap Matriz P (MAS)...\n")

tryCatch({
  matriz_P <- read_parquet(file.path(DATA_DIR, "matriz_P_nacional_filtrada.parquet"))
  
  # Muestreo Aleatorio Simple: seleccionar 100 secciones al azar
  set.seed(2026)  # Semilla para reproducibilidad
  indices_muestra <- sample(1:nrow(matriz_P), size = 100, replace = FALSE)
  matriz_sample <- matriz_P[indices_muestra, ]
  cols_demo <- names(matriz_sample)[grepl("^[HM]_", names(matriz_sample))]
  
  if(length(cols_demo) > 0) {
    matriz_long <- matriz_sample %>%
      mutate(Seccion_ID = row_number()) %>%
      select(Seccion_ID, all_of(cols_demo)) %>%
      pivot_longer(cols = -Seccion_ID, names_to = "Bin", values_to = "Probabilidad")
    
    matriz_long$Bin <- factor(matriz_long$Bin, levels = cols_demo)
    
    p1 <- ggplot(matriz_long, aes(x = Bin, y = Seccion_ID, fill = Probabilidad)) +
      geom_tile() +
      scale_fill_viridis(option = "plasma", trans = "sqrt", 
                         labels = percent_format(accuracy = 0.1)) +
      labs(title = "Matriz P: Distribución Demográfica por Sección Censal",
           subtitle = "Muestra de 100 secciones | Colores más intensos = mayor concentración",
           x = "Bin Edad-Sexo", y = "Sección Censal (ID)",
           fill = "Probabilidad") +
      theme(axis.text.x = element_text(angle = 90, hjust = 1, size = 5),
            legend.position = "right",
            plot.title = element_text(face = "bold", size = 12))
    
    ggsave(file.path(OUTPUT_DIR, "matriz_p_heatmap.pdf"), p1, 
           width = 18, height = 10, units = "cm", device = cairo_pdf)
    cat("   ✓ matriz_p_heatmap.pdf generado\n")
  }
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 2: Histograma de Resonancias
# ==============================================================================
cat(">>> Generando Figura 2: Histograma de Resonancias...\n")

tryCatch({
  ranking <- read.csv(file.path(DATA_DIR, "ranking_fase3_resonancia.csv"), sep = ";")
  umbral_85 <- quantile(ranking$Resonancia, 0.85, na.rm = TRUE)
  
  p2 <- ggplot(ranking, aes(x = Resonancia)) +
    geom_histogram(bins = 50, fill = "#3498db", color = "white", alpha = 0.8) +
    geom_vline(xintercept = umbral_85, color = "#e74c3c", linetype = "dashed", linewidth = 0.8) +
    annotate("text", x = umbral_85 + 0.015, y = Inf, vjust = 2, hjust = 0,
             label = paste0("Percentil 85\n(", round(umbral_85, 3), ")"),
             color = "#e74c3c", fontface = "bold", size = 3) +
    labs(title = "Distribución de Resonancia Demográfica",
         subtitle = paste0("N = ", format(nrow(ranking), big.mark = "."), " secciones censales"),
         x = "Resonancia (1 - JSD)", y = "Frecuencia") +
    scale_x_continuous(labels = number_format(accuracy = 0.01)) +
    scale_y_continuous(labels = comma_format()) +
    theme(plot.title = element_text(face = "bold", size = 12))
  
  ggsave(file.path(OUTPUT_DIR, "histograma_resonancia.pdf"), p2, 
         width = 15, height = 9, units = "cm", device = cairo_pdf)
  cat("   ✓ histograma_resonancia.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 3: Mapa de España con CCAA y Clusters DBSCAN
# ==============================================================================
cat(">>> Generando Figura 3: Mapa de Clusters España con CCAA...\n")

tryCatch({
  geo_data <- read.csv(file.path(DATA_DIR, "ranking_fase8_puntos_con_cluster.csv"), sep = ";")
  
  geo_data <- geo_data %>% 
    filter(!is.na(LATITUD) & !is.na(LONGITUD)) %>%
    filter(Cluster_ID >= 0)
  
  p3 <- ggplot() +
    # Capa base: países europeos
    geom_sf(data = europe, fill = "#f5f5f5", color = "gray70", linewidth = 0.15)
  
  # Añadir CCAA si están disponibles
  if(!is.null(ccaa)) {
    p3 <- p3 + geom_sf(data = ccaa, fill = "white", color = "gray50", linewidth = 0.3)
  } else {
    p3 <- p3 + geom_sf(data = spain, fill = "white", color = "gray40", linewidth = 0.4)
  }
  
  p3 <- p3 +
    # Puntos de clusters
    geom_point(data = geo_data, aes(x = LONGITUD, y = LATITUD, color = factor(Cluster_ID)),
               alpha = 0.75, size = 0.6) +
    scale_color_viridis_d(option = "turbo") +
    coord_sf(xlim = c(-10, 5), ylim = c(35.5, 44), expand = FALSE) +
    labs(title = "Clusters de Demanda Identificados (DBSCAN)",
         subtitle = paste0(n_distinct(geo_data$Cluster_ID), " clusters | ",
                          format(nrow(geo_data), big.mark = "."), " secciones"),
         x = NULL, y = NULL) +
    theme_minimal(base_size = 10) +
    theme(legend.position = "none",
          plot.title = element_text(face = "bold", size = 11),
          panel.background = element_rect(fill = "#e6f2ff", color = NA),
          panel.grid = element_line(color = "white", linewidth = 0.2),
          axis.text = element_text(size = 7))
  
  ggsave(file.path(OUTPUT_DIR, "mapa_clusters_espana.pdf"), p3, 
         width = 16, height = 14, units = "cm", device = cairo_pdf)
  cat("   ✓ mapa_clusters_espana.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 4: Gráfico de Barras Top 10 Clusters
# ==============================================================================
cat(">>> Generando Figura 4: Top 10 Clusters...\n")

tryCatch({
  clusters <- read.csv(file.path(DATA_DIR, "ranking_fase7_clusters.csv"), sep = ";")
  
  # Extraer el nombre de la ciudad del campo Toponimos
  # El formato es: "['2807911123 Madrid sección 11123', ...]"
  # Queremos extraer solo "Madrid" o "Donostia/San Sebastián"
  extraer_ciudad <- function(toponimo) {
    # Buscar patrón: código + espacio + nombre (con espacios) + " sección"
    # Usamos .+? para capturar cualquier carácter (incluyendo espacios) de forma no codiciosa
    match <- regmatches(toponimo, regexpr("[0-9]+ (.+?) sección", toponimo))
    if (length(match) > 0 && nchar(match) > 0) {
      # Extraer solo el nombre (quitar código y " sección")
      ciudad <- sub("^[0-9]+ ", "", match)
      ciudad <- sub(" sección$", "", ciudad)
      return(ciudad)
    }
    return("Desconocido")
  }
  
  top10 <- clusters %>%
    arrange(desc(Potencia_Total)) %>%
    head(10) %>%
    mutate(Ciudad = sapply(Toponimos, extraer_ciudad))
  
  p4 <- ggplot(top10, aes(x = reorder(Ciudad, Potencia_Total), y = Potencia_Total)) +
    geom_col(aes(fill = Potencia_Total), show.legend = FALSE) +
    geom_text(aes(label = round(Potencia_Total, 1)), hjust = -0.1, size = 3) +
    scale_fill_viridis_c(option = "plasma", direction = -1) +
    coord_flip() +
    labs(title = "Top 10 Clusters por Potencia Total",
         subtitle = "Potencia = Σ Score_Global de todas las secciones del cluster",
         x = "", y = "Potencia Total") +
    theme(plot.title = element_text(face = "bold", size = 11)) +
    expand_limits(y = max(top10$Potencia_Total) * 1.15)
  
  ggsave(file.path(OUTPUT_DIR, "barras_top10_clusters.pdf"), p4, 
         width = 15, height = 9, units = "cm", device = cairo_pdf)
  cat("   ✓ barras_top10_clusters.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 5: Mapa Detalle Madrid con Secciones Censales
# ==============================================================================
cat(">>> Generando Figura 5: Mapa Detalle Madrid con secciones...\n")

tryCatch({
  geo_data <- read.csv(file.path(DATA_DIR, "ranking_fase8_puntos_con_cluster.csv"), sep = ";")
  
  madrid_puntos <- geo_data %>%
    filter(LONGITUD > -4.5 & LONGITUD < -3.3,
           LATITUD > 40.2 & LATITUD < 40.7,
           !is.na(LATITUD) & !is.na(LONGITUD),
           Cluster_ID >= 0)
  
  p5 <- ggplot()
  
  # Añadir secciones censales de Madrid si están disponibles
  if(!is.null(madrid_secciones)) {
    # Recortar al área de interés
    madrid_crop <- madrid_secciones %>%
      st_transform(4326) %>%
      st_crop(xmin = -4.0, xmax = -3.5, ymin = 40.3, ymax = 40.55)
    
    p5 <- p5 + geom_sf(data = madrid_crop, fill = "gray98", color = "gray60", linewidth = 0.1)
  }
  
  p5 <- p5 +
    geom_point(data = madrid_puntos, 
               aes(x = LONGITUD, y = LATITUD, color = Score_Global, size = Score_Global), 
               alpha = 0.8) +
    scale_color_viridis_c(option = "inferno") +
    scale_size_continuous(range = c(0.8, 3)) +
    coord_sf(xlim = c(-4.0, -3.5), ylim = c(40.3, 40.55), expand = FALSE) +
    labs(title = "Detalle: Área Metropolitana de Madrid",
         subtitle = paste0(format(nrow(madrid_puntos), big.mark = "."), 
                          " secciones en clusters viables"),
         x = NULL, y = NULL,
         color = "Score Global", size = "Score Global") +
    theme_minimal(base_size = 10) +
    theme(plot.title = element_text(face = "bold", size = 11),
          panel.background = element_rect(fill = "#fffef0", color = "gray70"),
          legend.position = "right",
          legend.key.size = unit(0.4, "cm"),
          axis.text = element_text(size = 7))
  
  ggsave(file.path(OUTPUT_DIR, "mapa_madrid_clusters.pdf"), p5, 
         width = 15, height = 12, units = "cm", device = cairo_pdf)
  cat("   ✓ mapa_madrid_clusters.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 6: Gráfico de Sensibilidad
# ==============================================================================
cat(">>> Generando Figura 6: Análisis de Sensibilidad...\n")

tryCatch({
  # DATOS REALES calculados desde los CSVs
  sensibilidad <- data.frame(
    Share = c(1.5, 2.0, 3.0, 5.0),
    Clusters_Viables = c(6, 12, 19, 25),      # Datos corregidos
    Residencias = c(17, 29, 50, 91),          # Datos corregidos
    Gap = c(-983, -971, -950, -909)           # Datos corregidos
  )
  
  p6a <- ggplot(sensibilidad, aes(x = Share, y = Residencias)) +
    geom_line(color = "#2ecc71", linewidth = 1.2) +
    geom_point(size = 3, color = "#27ae60") +
    geom_hline(yintercept = 1000, linetype = "dashed", color = "#e74c3c", linewidth = 0.6) +
    annotate("text", x = 4, y = 1000, vjust = -0.5, label = "Objetivo: 1000",
             color = "#e74c3c", fontface = "bold", size = 3) +
    geom_text(aes(label = Residencias), vjust = -1, fontface = "bold", size = 3) +
    labs(title = "Análisis de Sensibilidad",
         subtitle = "Residencias viables según cuota de mercado",
         x = "Market Share (%)", y = "Residencias") +
    scale_x_continuous(breaks = sensibilidad$Share, labels = paste0(sensibilidad$Share, "%")) +
    scale_y_continuous(limits = c(0, 1100)) +
    theme(plot.title = element_text(face = "bold", size = 11))
  
  p6b <- ggplot(sensibilidad, aes(x = Share, y = Clusters_Viables)) +
    geom_col(fill = "#3498db", alpha = 0.8, width = 0.6) +
    geom_text(aes(label = Clusters_Viables), vjust = -0.5, fontface = "bold", size = 3) +
    labs(x = "Market Share (%)", y = "Clusters Viables") +
    scale_x_continuous(breaks = sensibilidad$Share, labels = paste0(sensibilidad$Share, "%")) +
    expand_limits(y = 35)
  
  p6_combined <- p6a / p6b + plot_annotation(
    title = "Impacto del Market Share en la Viabilidad",
    theme = theme(plot.title = element_text(face = "bold", size = 12))
  )
  
  ggsave(file.path(OUTPUT_DIR, "sensibilidad_share.pdf"), p6_combined, 
         width = 14, height = 16, units = "cm", device = cairo_pdf)
  cat("   ✓ sensibilidad_share.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 7: Mapa de Clusters Viables (solo los que sobreviven)
# ==============================================================================
cat(">>> Generando Figura 7: Mapa Clusters Viables...\n")

tryCatch({
  geo_data <- read.csv(file.path(DATA_DIR, "ranking_fase8_puntos_con_cluster.csv"), sep = ";")
  
  # FILTRAR SOLO CLUSTERS VIABLES (Es_Viable viene como texto "True"/"False")
  geo_data <- geo_data %>%
    filter(!is.na(LATITUD) & !is.na(LONGITUD)) %>%
    filter(Es_Viable == "True" | Es_Viable == TRUE)  # Acepta texto o booleano
  
  n_viables <- n_distinct(geo_data$Cluster_ID)
  n_secciones <- nrow(geo_data)
  
  p7 <- ggplot() +
    geom_sf(data = europe, fill = "#f5f5f5", color = "gray70", linewidth = 0.15)
  
  if(!is.null(ccaa)) {
    p7 <- p7 + geom_sf(data = ccaa, fill = "white", color = "gray50", linewidth = 0.3)
  } else {
    p7 <- p7 + geom_sf(data = spain, fill = "white", color = "gray40", linewidth = 0.4)
  }
  
  p7 <- p7 +
    geom_point(data = geo_data, aes(x = LONGITUD, y = LATITUD, color = factor(Cluster_ID)),
               alpha = 0.8, size = 0.8) +
    scale_color_viridis_d(option = "turbo") +
    coord_sf(xlim = c(-10, 5), ylim = c(35.5, 44), expand = FALSE) +
    labs(title = "Clusters Viables para Construcción de Residencias",
         subtitle = paste0(n_viables, " clusters viables | ", format(n_secciones, big.mark = "."), " secciones"),
         x = NULL, y = NULL) +
    theme_minimal(base_size = 10) +
    theme(plot.title = element_text(face = "bold", size = 11),
          legend.position = "none",
          panel.background = element_rect(fill = "#e6f2ff", color = NA),
          panel.grid = element_line(color = "white", linewidth = 0.2),
          axis.text = element_text(size = 7))
  
  ggsave(file.path(OUTPUT_DIR, "mapa_viables_subcriticos.pdf"), p7, 
         width = 16, height = 14, units = "cm", device = cairo_pdf)
  cat("   ✓ mapa_viables_subcriticos.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 8: Diagrama de Arquitectura
# ==============================================================================
cat(">>> Generando Figura 8: Diagrama Arquitectura...\n")

tryCatch({
  fases <- data.frame(
    Fase = c("Fase 1", "Fase 2", "Fase 3", "Fase 4", "Fase 5"),
    Nombre = c("Resonancia\nDemográfica", "Filtro\nEconómico", "Feature\nEngineering", 
               "Score\nGlobal", "Clustering\nDBSCAN"),
    x = 1:5,
    y = rep(0, 5)
  )
  
  p8 <- ggplot(fases, aes(x = x, y = y)) +
    geom_segment(aes(x = x + 0.35, xend = x + 0.65, y = y, yend = y),
                 arrow = arrow(length = unit(0.2, "cm"), type = "closed"), 
                 color = "gray40", linewidth = 0.8,
                 data = fases[1:4, ]) +
    geom_label(aes(label = Nombre, fill = factor(x)), size = 3.5, 
               fontface = "bold", color = "white", label.padding = unit(0.4, "lines")) +
    geom_text(aes(label = Fase, y = y - 0.12), size = 2.5, fontface = "italic") +
    scale_fill_viridis_d(option = "plasma") +
    coord_cartesian(xlim = c(0.5, 5.5), ylim = c(-0.25, 0.25)) +
    labs(title = "Arquitectura del Algoritmo L-SOMA",
         subtitle = "Pipeline de procesamiento en 5 fases") +
    theme_void() +
    theme(plot.title = element_text(face = "bold", hjust = 0.5, size = 12),
          plot.subtitle = element_text(hjust = 0.5, size = 10),
          legend.position = "none")
  
  ggsave(file.path(OUTPUT_DIR, "arquitectura_lsoma.pdf"), p8, 
         width = 16, height = 5, units = "cm", device = cairo_pdf)
  cat("   ✓ arquitectura_lsoma.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 9: Curva de Convergencia del Algoritmo de Expansión
# ==============================================================================
cat(">>> Generando Figura 9: Curva de Convergencia Expansión...\n")

tryCatch({
  expansion_log <- read.csv(file.path(DATA_DIR, "expansion_log.csv"), sep = ";")
  
  # Crear etiquetas para los parámetros modificados
  expansion_log <- expansion_log %>%
    mutate(Fase = case_when(
      Param_Modificado == "INICIAL" ~ "Inicial",
      Param_Modificado == "percentil_score" ~ "Nivel 1",
      Param_Modificado == "market_share" ~ "Nivel 2", 
      Param_Modificado == "penalizacion_renta" ~ "Nivel 3",
      Param_Modificado == "camas_minimas" ~ "Nivel 4",
      TRUE ~ "Otro"
    ))
  
  p9 <- ggplot(expansion_log, aes(x = Iteracion, y = Residencias_Viables)) +
    geom_line(color = "#2ecc71", linewidth = 1.2) +
    geom_point(aes(color = Fase), size = 2, alpha = 0.8) +
    geom_hline(yintercept = 1000, linetype = "dashed", color = "#e74c3c", linewidth = 0.8) +
    geom_hline(yintercept = 64, linetype = "dotted", color = "#3498db", linewidth = 0.7) +
    annotate("text", x = 40, y = 1000, vjust = -0.8, label = "Objetivo: 1.000",
             color = "#e74c3c", fontface = "bold", size = 3.2) +
    annotate("text", x = 40, y = 64, vjust = 1.8, label = "Modelo Prime: 64",
             color = "#3498db", fontface = "bold", size = 3.2) +
    annotate("text", x = 55, y = 359, vjust = -1.2, label = "Límite: 359",
             color = "#27ae60", fontface = "bold", size = 3.2) +
    scale_color_manual(values = c(
      "Inicial" = "#95a5a6",
      "Nivel 1" = "#3498db",
      "Nivel 2" = "#f39c12",
      "Nivel 3" = "#e67e22",
      "Nivel 4" = "#e74c3c"
    )) +
    scale_y_continuous(limits = c(0, 1100), breaks = seq(0, 1000, 200)) +
    labs(title = "Curva de Convergencia del Algoritmo de Expansión Adaptativa",
         subtitle = "71 iteraciones | Gap final: 641 residencias",
         x = "Iteración", y = "Residencias Viables",
         color = "Nivel de Riesgo") +
    theme_minimal(base_size = 10) +
    theme(plot.title = element_text(face = "bold", size = 11),
          plot.margin = margin(10, 15, 10, 10),
          legend.position = "bottom",
          legend.key.size = unit(0.4, "cm"))
  
  ggsave(file.path(OUTPUT_DIR, "expansion_convergencia.pdf"), p9, 
         width = 16, height = 12, units = "cm", device = cairo_pdf)
  cat("   ✓ expansion_convergencia.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 10: Mapa de Clusters Expandidos
# ==============================================================================
cat(">>> Generando Figura 10: Mapa Clusters Expandidos...\n")

tryCatch({
  expansion_clusters <- read.csv(file.path(DATA_DIR, "expansion_clusters_final.csv"), sep = ";")
  
  # Filtrar solo península para visualización
  expansion_clusters_pen <- expansion_clusters %>%
    filter(LATITUD > 35, LATITUD < 44, LONGITUD > -10, LONGITUD < 5)
  
  # Usar conteo total (no filtrado) para el título
  n_clusters <- nrow(expansion_clusters)
  camas_total <- sum(expansion_clusters$Camas_Potenciales)
  
  p10 <- ggplot() +
    geom_sf(data = europe, fill = "#f5f5f5", color = "gray70", linewidth = 0.15)
  
  if(!is.null(ccaa)) {
    p10 <- p10 + geom_sf(data = ccaa, fill = "white", color = "gray50", linewidth = 0.3)
  } else {
    p10 <- p10 + geom_sf(data = spain, fill = "white", color = "gray40", linewidth = 0.4)
  }
  
  p10 <- p10 +
    geom_point(data = expansion_clusters_pen, 
               aes(x = LONGITUD, y = LATITUD, size = Camas_Potenciales, color = Renta_Hogar),
               alpha = 0.7) +
    scale_size_continuous(range = c(1, 8), name = "Camas", 
                          breaks = c(100, 500, 1000, 2000)) +
    scale_color_viridis_c(option = "plasma", name = "Renta (€)", 
                          labels = scales::comma, limits = c(30000, 65000)) +
    coord_sf(xlim = c(-10, 5), ylim = c(35.5, 44), expand = FALSE) +
    labs(title = "Clusters Viables tras Expansión Adaptativa",
         subtitle = paste0(n_clusters, " clusters | ", format(round(camas_total), big.mark = "."), " camas potenciales"),
         x = NULL, y = NULL) +
    theme_minimal(base_size = 10) +
    theme(plot.title = element_text(face = "bold", size = 11),
          legend.position = "right",
          legend.key.size = unit(0.4, "cm"),
          panel.background = element_rect(fill = "#e6f2ff", color = NA),
          panel.grid = element_line(color = "white", linewidth = 0.2),
          axis.text = element_text(size = 7))
  
  ggsave(file.path(OUTPUT_DIR, "expansion_mapa_clusters.pdf"), p10, 
         width = 18, height = 14, units = "cm", device = cairo_pdf)
  cat("   ✓ expansion_mapa_clusters.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 11: Comparativa Prime vs Expandido (Barras)
# ==============================================================================
cat(">>> Generando Figura 11: Comparativa Prime vs Expandido...\n")

tryCatch({
  comparativa <- data.frame(
    Metrica = c("Residencias", "Clusters\nViables", "Renta Media\n(miles €)", "Score\nDemográfico"),
    Prime = c(64, 21, 42.5, 0.594),
    Expandido = c(359, 91, 40.4, 0.470)
  )
  
  comparativa_long <- comparativa %>%
    pivot_longer(cols = c(Prime, Expandido), names_to = "Modelo", values_to = "Valor")
  
  # Normalizar para visualización (escalar a 0-100 para comparar)
  comparativa_norm <- comparativa %>%
    mutate(
      Prime_norm = c(64/359*100, 21/91*100, 42.5/42.5*100, 0.594/0.594*100),
      Expandido_norm = c(100, 100, 40.4/42.5*100, 0.470/0.594*100)
    ) %>%
    pivot_longer(cols = c(Prime_norm, Expandido_norm), 
                 names_to = "Modelo", values_to = "Valor_Norm") %>%
    mutate(Modelo = gsub("_norm", "", Modelo))
  
  p11 <- ggplot(comparativa_long, aes(x = Metrica, y = Valor, fill = Modelo)) +
    geom_col(position = position_dodge(width = 0.8), width = 0.7, alpha = 0.9) +
    geom_text(aes(label = ifelse(Metrica %in% c("Score\nDemográfico"), 
                                  sprintf("%.3f", Valor),
                                  ifelse(Metrica == "Renta Media\n(miles €)", 
                                         sprintf("%.1f", Valor),
                                         as.character(Valor)))),
              position = position_dodge(width = 0.8), vjust = -0.3, size = 2.8, fontface = "bold") +
    scale_fill_manual(values = c("Prime" = "#3498db", "Expandido" = "#e74c3c")) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
    facet_wrap(~ Metrica, scales = "free", nrow = 1) +
    labs(title = "Comparativa: Modelo Prime vs Modelo Expandido",
         subtitle = "Trade-off entre volumen y calidad demográfica/económica",
         x = NULL, y = "Valor") +
    theme_minimal(base_size = 10) +
    theme(plot.title = element_text(face = "bold", size = 11),
          plot.margin = margin(15, 10, 10, 10),
          legend.position = "bottom",
          strip.text = element_blank(),
          axis.text.x = element_text(size = 8))
  
  ggsave(file.path(OUTPUT_DIR, "expansion_comparativa.pdf"), p11, 
         width = 18, height = 11, units = "cm", device = cairo_pdf)
  cat("   ✓ expansion_comparativa.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
# FIGURA 12: Distribución de Saturación (Competencia)
# ==============================================================================
cat(">>> Generando Figura 12: Distribución Saturación Competencia...\n")

tryCatch({
  competencia <- read.csv(file.path(DATA_DIR, "clusters_359_validado_FINAL.csv"), sep = ";")
  
  # Contar por tipo
  saturacion_counts <- competencia %>%
    group_by(Tipo_Oceano) %>%
    summarise(n = n(), .groups = "drop") %>%
    mutate(
      pct = n / sum(n) * 100,
      Tipo_Oceano = factor(Tipo_Oceano, levels = c("Blue Ocean", "Batalla", "Saturado"))
    )
  
  colores <- c("Blue Ocean" = "#3498db", "Batalla" = "#f39c12", "Saturado" = "#e74c3c")
  
  p12 <- ggplot(saturacion_counts, aes(x = Tipo_Oceano, y = n, fill = Tipo_Oceano)) +
    geom_col(width = 0.7, alpha = 0.9) +
    geom_text(aes(label = paste0(n, "\n(", round(pct, 1), "%)")), 
              vjust = -0.3, size = 4, fontface = "bold") +
    scale_fill_manual(values = colores) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.25))) +
    labs(title = "Clasificación de Clusters por Nivel de Competencia",
         subtitle = "91 clusters analizados mediante Google Places API",
         x = NULL, y = "Número de Clusters") +
    theme_minimal(base_size = 11) +
    theme(plot.title = element_text(face = "bold", size = 12),
          legend.position = "none",
          panel.grid.major.x = element_blank(),
          plot.margin = margin(t = 15, r = 10, b = 10, l = 10))
  
  ggsave(file.path(OUTPUT_DIR, "competencia_distribucion.pdf"), p12, 
         width = 14, height = 12, units = "cm", device = cairo_pdf)
  cat("   ✓ competencia_distribucion.pdf generado\n")
  
}, error = function(e) cat("   ✗ Error:", e$message, "\n"))

# ==============================================================================
cat("\n=== GENERACIÓN COMPLETADA ===\n")
cat("Imágenes vectoriales (PDF) guardadas en:", normalizePath(OUTPUT_DIR), "\n")
cat("NOTA: Recuerda actualizar el .tex para usar .pdf en lugar de .png\n")
