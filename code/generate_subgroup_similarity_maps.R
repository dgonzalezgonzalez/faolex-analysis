#!/usr/bin/env Rscript
#
# Subgroup Similarity Maps - Demand vs Supply Side
# Outputs: 6 static maps (3 strategies × 2 categories)
#   strategy_sus_demand_map.pdf/png
#   strategy_sus_supply_map.pdf/png
#   strategy_fs_demand_map.pdf/png
#   strategy_fs_supply_map.pdf/png
#   strategy_nut_demand_map.pdf/png
#   strategy_nut_supply_map.pdf/png

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

# Extract year from date_original using robust method (like Python script)
# Keep only last 4 characters and check if they are all digits
df$year_str <- substr(df$date_original, nchar(df$date_original)-3, nchar(df$date_original))
valid_year_mask <- grepl("^\\d{4}$", df$year_str)
df <- df[valid_year_mask, ]
df$year <- as.integer(df$year_str)
# Filter to optimal year window: 1992-2025 (stable coverage, recent past)
df <- df %>% filter(year >= 1992 & year <= 2025)

# Load world map (load once, reuse)
world <- ne_countries(scale = "medium", returnclass = "sf")
if (is.null(world$iso3)) world$iso3 <- countrycode(world$name, "country.name", "iso3c", warn = FALSE)

# ============================
# HELPER: Create map for one variable
# ============================
make_map <- function(data, value_col, fill_name) {
  map_df <- world %>% left_join(data, by = "iso3")

  # Use unified sequential color scale based on observed data percentiles
  # 5th percentile across all strategies: ~0.061, 95th: ~0.467
  # This captures the core variation across countries without distortion from extreme outliers
  ggplot(map_df) +
    geom_sf(aes(fill = .data[[value_col]]), color = "gray70", linewidth = 0.1) +
    scale_fill_gradient(
      name = fill_name,
      low = "#deebf7",    # Very light blue
      high = "#08519e",   # Dark blue
      limits = c(0.061, 0.467),
      labels = scales::number_format(accuracy = 0.01),
      oob = scales::squish  # Squish out-of-bounds values to nearest limit
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
# CREATE 6 STATIC MAPS (3 strategies × 2 categories)
# ============================
cat("Generating subgroup similarity maps...\n")

strategies <- c("strategy_sus", "strategy_fs", "strategy_nut")
strategy_labels <- c("Sustainability", "Food Systems", "Nutrition")
categories <- c("demand_side", "supply_side")
category_labels <- c("Demand-side", "Supply-side")

country_counts <- list()

for (strat in strategies) {
  for (cat in categories) {
    # Filter by category
    cat_data <- df %>% filter(Category == cat)

    # Aggregate by country for this strategy
    country_data <- cat_data %>%
      group_by(country) %>%
      summarise(
        value = mean(.data[[strat]], na.rm = TRUE),
        .groups = 'drop'
      )

    # Map to ISO3
    country_data$iso3 <- countrycode(country_data$country, "country.name", "iso3c", warn = FALSE)
    country_data <- country_data[!is.na(country_data$iso3), ]

    # Store count for reporting
    cat_label <- ifelse(cat == "demand_side", "demand", "supply")
    strat_label <- ifelse(strat == "strategy_sus", "sus",
                  ifelse(strat == "strategy_fs", "fs", "nut"))
    key <- paste0(strat_label, "_", cat_label)
    country_counts[[key]] <- nrow(country_data)

    # Create map
    strat_label_pretty <- strategy_labels[which(strategies == strat)]
    cat_label_pretty <- category_labels[which(categories == cat)]
    fill_name <- paste0(strat_label_pretty, " (", cat_label_pretty, ")")

    p <- make_map(country_data, "value", fill_name)

    # Save outputs
    filename_base <- sprintf("strategy_%s_%s_map", strat_label, cat_label)
    ggsave(file.path(output_dir, paste0(filename_base, ".pdf")), p, width = 6, height = 4, units = "in", dpi = 300)
    ggsave(file.path(output_dir, paste0(filename_base, ".png")), p, width = 6, height = 4, units = "in", dpi = 300, bg = "white")
  }
}

cat("  ✓ Static maps saved\n")

# ============================
# REPORT SUMMARY
# ============================
cat("\n✅ Subgroup similarity maps generated successfully!\n")
cat(sprintf("   Year range: 1992-2025\n"))
cat("   Countries with data by subgroup:\n")
for (key in names(country_counts)) {
  cat(sprintf("     - %s: %d countries\n", key, country_counts[[key]]))
}
