#!/usr/bin/env Rscript
#
# World Map Visualization - Policy Counts by Country
# Outputs: policy_counts_total_map.pdf/png, policy_counts_demand_map.pdf/png, policy_counts_supply_map.pdf/png

library(ggplot2)
library(sf)
library(rnaturalearth)
library(countrycode)
library(dplyr)
library(scales)

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
cat("Loading analysis dataset...\n")
df <- read.csv(input_file, stringsAsFactors = FALSE)

# Extract year from date_original using robust method
df$year_str <- substr(df$date_original, nchar(df$date_original)-3, nchar(df$date_original))
valid_year_mask <- grepl("^\\d{4}$", df$year_str)
df <- df[valid_year_mask, ]
df$year <- as.integer(df$year_str)

# Filter to optimal year window: 1992-2025
df <- df %>% filter(year >= 1992 & year <= 2025)

cat(sprintf("Loaded %d records from %s\n", nrow(df), input_file))
cat(sprintf("Year range: %d-%d\n", min(df$year), max(df$year)))

# ============================
# AGGREGATE BY COUNTRY AND CATEGORY
# ============================
cat("Aggregating policy counts by country...\n")

# Count by country for each category
country_counts <- df %>%
  group_by(country) %>%
  summarise(
    total = n(),
    demand = sum(Category == "demand_side", na.rm = TRUE),
    supply = sum(Category == "supply_side", na.rm = TRUE),
    .groups = 'drop'
  )

# Map to ISO3
country_counts$iso3 <- countrycode(country_counts$country, "country.name", "iso3c", warn = FALSE)
country_counts <- country_counts[!is.na(country_counts$iso3), ]

cat(sprintf("Mapped %d countries to ISO3 codes\n", nrow(country_counts)))

# Compute dynamic color scale limits (5th and 95th percentiles) for each category
get_limits <- function(data, col) {
  p_low <- quantile(data[[col]], 0.05, na.rm = TRUE)
  p_high <- quantile(data[[col]], 0.95, na.rm = TRUE)
  c(p_low, p_high)
}

limits_total <- get_limits(country_counts, "total")
limits_demand <- get_limits(country_counts, "demand")
limits_supply <- get_limits(country_counts, "supply")

cat("Color scale limits (5th, 95th percentiles):\n")
cat(sprintf("  Total: [%.0f, %.0f]\n", limits_total[1], limits_total[2]))
cat(sprintf("  Demand: [%.0f, %.0f]\n", limits_demand[1], limits_demand[2]))
cat(sprintf("  Supply: [%.0f, %.0f]\n", limits_supply[1], limits_supply[2]))

# Load world map
world <- ne_countries(scale = "medium", returnclass = "sf")
if (is.null(world$iso3)) world$iso3 <- countrycode(world$name, "country.name", "iso3c", warn = FALSE)

# ============================
# HELPER: Create map for one variable
# ============================
make_count_map <- function(data, value_col, fill_name, limits) {
  map_df <- world %>% left_join(data, by = "iso3")

  ggplot(map_df) +
    geom_sf(aes(fill = .data[[value_col]]), color = "gray70", linewidth = 0.1) +
    scale_fill_gradient(
      name = fill_name,
      low = "#deebf7",    # Very light blue
      high = "#08519e",   # Dark blue
      limits = limits,
      labels = scales::number_format(accuracy = 1),
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
# CREATE 3 STATIC MAPS
# ============================
cat("Generating policy count maps...\n")

# Total policies
p_total <- make_count_map(country_counts, "total", "Total Policies", limits_total)
ggsave(file.path(output_dir, "policy_counts_total_map.pdf"), p_total, width = 6, height = 4, units = "in", dpi = 300)
ggsave(file.path(output_dir, "policy_counts_total_map.png"), p_total, width = 6, height = 4, units = "in", dpi = 300, bg = "white")
cat("  ✓ Total policy map saved\n")

# Demand-side policies
p_demand <- make_count_map(country_counts, "demand", "Demand-Side Policies", limits_demand)
ggsave(file.path(output_dir, "policy_counts_demand_map.pdf"), p_demand, width = 6, height = 4, units = "in", dpi = 300)
ggsave(file.path(output_dir, "policy_counts_demand_map.png"), p_demand, width = 6, height = 4, units = "in", dpi = 300, bg = "white")
cat("  ✓ Demand-side policy map saved\n")

# Supply-side policies
p_supply <- make_count_map(country_counts, "supply", "Supply-Side Policies", limits_supply)
ggsave(file.path(output_dir, "policy_counts_supply_map.pdf"), p_supply, width = 6, height = 4, units = "in", dpi = 300)
ggsave(file.path(output_dir, "policy_counts_supply_map.png"), p_supply, width = 6, height = 4, units = "in", dpi = 300, bg = "white")
cat("  ✓ Supply-side policy map saved\n")

cat("✅ All policy count maps generated successfully!\n")
cat(sprintf("   Countries mapped: %d\n", nrow(country_counts)))
cat(sprintf("   Total policies (all countries): %d\n", sum(country_counts$total)))
cat(sprintf("   Demand-side policies: %d\n", sum(country_counts$demand)))
cat(sprintf("   Supply-side policies: %d\n", sum(country_counts$supply)))
