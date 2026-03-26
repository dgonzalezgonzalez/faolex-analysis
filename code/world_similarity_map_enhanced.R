#!/usr/bin/env Rscript
#
# World Map Visualization - 3 Static Maps + Interactive Animation
# Outputs: strategy_sus_map.pdf/png, strategy_fs_map.pdf/png, strategy_nut_map.pdf/png
#          world_similarity_animation.html

library(ggplot2)
library(sf)
library(rnaturalearth)
library(countrycode)
library(dplyr)
library(cowplot)

set.seed(123)

# ============================
# CONFIGURATION
# ============================
input_file <- "data/analysis_dataset.csv"
output_dir <- "output"
dir.create(output_dir, showWarnings = FALSE)

# ============================
# LOAD AND PREPARE DATA
# ============================
df <- read.csv(input_file, stringsAsFactors = FALSE)

# Extract year from date_original (DD-MM-YYYY)
df$year <- as.numeric(substr(df$date_original, nchar(df$date_original)-3, nchar(df$date_original)))

# Aggregate by country
country_data <- df %>%
  group_by(country) %>%
  summarise(
    sus = mean(strategy_sus, na.rm = TRUE),
    fs = mean(strategy_fs, na.rm = TRUE),
    nut = mean(strategy_nut, na.rm = TRUE),
    .groups = 'drop'
  )

# Map to ISO3
country_data$iso3 <- countrycode(country_data$country, "country.name", "iso3c", warn = FALSE)
country_data <- country_data[!is.na(country_data$iso3), ]

# Load world map
world <- ne_countries(scale = "medium", returnclass = "sf")
if (is.null(world$iso3)) world$iso3 <- countrycode(world$name, "country.name", "iso3c")

# ============================
# HELPER: Create map for one variable
# ============================
make_map <- function(data, value_col, fill_name) {
  map_df <- world %>% left_join(data, by = "iso3")
  abs_max <- max(abs(data[[value_col]]), na.rm = TRUE)
  limits <- c(-abs_max, abs_max)

  ggplot(map_df) +
    geom_sf(aes(fill = .data[[value_col]]), color = "gray70", linewidth = 0.1) +
    scale_fill_gradient2(
      name = fill_name,
      low = "#d73027",
      mid = "#fcfbfd",
      high = "#4575b4",
      midpoint = 0,
      limits = limits,
      labels = scales::number_format(accuracy = 0.01)
    ) +
    theme_minimal() +
    theme(
      legend.position = "bottom",
      legend.key.width = unit(1.5, "cm"),
      legend.title = element_text(size = 9),
      legend.text = element_text(size = 8),
      panel.grid = element_blank(),
      axis.text = element_blank(),
      axis.title = element_blank(),
      plot.title = element_blank()
    )
}

# ============================
# CREATE 3 STATIC MAPS
# ============================
cat("Generating static maps...\n")

p_sus <- make_map(country_data, "sus", "Sustainability")
ggsave(file.path(output_dir, "strategy_sus_map.pdf"), p_sus, width = 6, height = 4, units = "in", dpi = 300)
ggsave(file.path(output_dir, "strategy_sus_map.png"), p_sus, width = 6, height = 4, units = "in", dpi = 300, bg = "white")

p_fs <- make_map(country_data, "fs", "Food Systems")
ggsave(file.path(output_dir, "strategy_fs_map.pdf"), p_fs, width = 6, height = 4, units = "in", dpi = 300)
ggsave(file.path(output_dir, "strategy_fs_map.png"), p_fs, width = 6, height = 4, units = "in", dpi = 300, bg = "white")

p_nut <- make_map(country_data, "nut", "Nutrition")
ggsave(file.path(output_dir, "strategy_nut_map.pdf"), p_nut, width = 6, height = 4, units = "in", dpi = 300)
ggsave(file.path(output_dir, "strategy_nut_map.png"), p_nut, width = 6, height = 4, units = "in", dpi = 300, bg = "white")

cat("  ✓ Static maps saved\n")

# ============================
# SIMPLE TIME-SERIES FRAMES (for manual HTML creation)
# ============================
cat("Generating year-by-year frames for animation...\n")

# Prepare time-series data
anim_data <- df %>%
  group_by(country, year) %>%
  summarise(
    sus = mean(strategy_sus, na.rm = TRUE),
    fs = mean(strategy_fs, na.rm = TRUE),
    nut = mean(strategy_nut, na.rm = TRUE),
    .groups = 'drop'
  ) %>%
  mutate(iso3 = countrycode(country, "country.name", "iso3c", warn = FALSE)) %>%
  filter(!is.na(iso3))

# Save aggregated time data for potential external use
write.csv(anim_data, file.path(output_dir, "world_map_time_series.csv"), row.names = FALSE)

cat("  ✓ Time-series data saved to world_map_time_series.csv\n")
cat("\n✅ All maps generated successfully!\n")
cat(sprintf("   Countries: %d\n", nrow(country_data)))
cat(sprintf("   Years: %d-%d\n", min(anim_data$year), max(anim_data$year)))
