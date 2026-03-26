#!/usr/bin/env Rscript
#
# World Map Visualization of Strategy Similarity Scores by Country
# Creates three maps (sustainability, food systems, nutrition) showing
# average cosine similarity scores per country

# Load required libraries
library(ggplot2)
library(sf)
library(rnaturalearth)
library(countrycode)
library(dplyr)
library(cowplot)  # For combining plots

# Set seed for reproducibility
set.seed(123)

# ============================
# CONFIGURATION
# ============================
input_file <- "data/analysis_dataset.csv"
output_dir <- "output"
output_pdf <- file.path(output_dir, "world_similarity_map.pdf")
output_png <- file.path(output_dir, "world_similarity_map.png")

# Create output directory if it doesn't exist
if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# ============================
# LOAD DATA
# ============================
cat("Loading analysis dataset...\n")
df <- read.csv(input_file, stringsAsFactors = FALSE)

# Aggregate by country: mean of each strategy
cat("Aggregating by country...\n")
country_data <- df %>%
  group_by(country) %>%
  summarise(
    strategy_sus = mean(strategy_sus, na.rm = TRUE),
    strategy_fs = mean(strategy_fs, na.rm = TRUE),
    strategy_nut = mean(strategy_nut, na.rm = TRUE),
    n_policies = n(),
    .groups = 'drop'
  )

# Map country names to ISO3 codes
cat("Converting country names to ISO3 codes...\n")
country_data$iso3 <- countrycode(
  sourcevar = country_data$country,
  origin = "country.name",
  destination = "iso3c",
  warn = TRUE
)

# Check for unmatched countries
unmatched <- country_data[is.na(country_data$iso3), ]
if (nrow(unmatched) > 0) {
  cat("Warning: Could not match these countries to ISO3 codes:\n")
  print(unmatched$country)
  # Remove them from mapping
  country_data <- country_data[!is.na(country_data$iso3), ]
}

# ============================
# LOAD WORLD MAP DATA
# ============================
cat("Loading world map shapefile...\n")
world <- ne_countries(scale = "medium", returnclass = "sf")

# Ensure ISO3 codes are present
if (is.null(world$iso3)) {
  world$iso3 <- countrycode(world$name, "country.name", "iso3c")
}

# ============================
# CREATE MAP FUNCTION
# ============================
create_map <- function(values_df, value_col, title_str) {
  # Merge data with world map
  map_data <- world %>%
    left_join(values_df, by = c("iso3" = "iso3"))

  # Determine color scale limits (symmetric around zero if negative values exist)
  all_values <- values_df[[value_col]]
  abs_max <- max(abs(all_values), na.rm = TRUE)
  limits <- c(-abs_max, abs_max)

  # Create diverging palette: red (negative) to blue (positive)
  # Using RdBu with reverse so blue = positive
  colors <- scales::gradient_n_pal(
    colours = c("#d73027", "#fcfbfd", "#4575b4"),
    values = scales::rescale(c(-1, 0, 1))
  )

  p <- ggplot(map_data) +
    geom_sf(aes(fill = .data[[value_col]]), color = "gray70", linewidth = 0.1) +
    scale_fill_gradient2(
      name = "Similarity",
      low = "#d73027",
      mid = "#fcfbfd",
      high = "#4575b4",
      midpoint = 0,
      limits = limits,
      labels = scales::number_format(accuracy = 0.01)
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(hjust = 0.5, size = 12, face = "bold"),
      legend.position = "bottom",
      legend.key.width = unit(1.5, "cm"),
      panel.grid = element_blank(),
      axis.text = element_blank(),
      axis.title = element_blank()
    ) +
    labs(title = title_str)

  return(p)
}

# ============================
# GENERATE THREE MAPS
# ============================
cat("Creating world maps...\n")

p_sus <- create_map(
  country_data,
  "strategy_sus",
  "Sustainability Strategy Similarity by Country"
) +
  theme(legend.position = "none")  # Remove legend from individual plots

p_fs <- create_map(
  country_data,
  "strategy_fs",
  "Food Systems Strategy Similarity by Country"
) +
  theme(legend.position = "none")

p_nut <- create_map(
  country_data,
  "strategy_nut",
  "Nutrition Strategy Similarity by Country"
) +
  theme(legend.position = "none")

# ============================
# COMBINE INTO SINGLE FIGURE
# ============================
cat("Combining maps into multi-panel figure...\n")

# Extract a common legend
legend_plot <- create_map(country_data, "strategy_sus", "") +
  theme(
    legend.position = "bottom",
    legend.text = element_text(size = 8),
    legend.title = element_text(size = 9)
  )

# Get legend as a separate grob
legend_grob <- cowplot::get_legend(legend_plot)

# Combine the three maps in a row
combined_plot <- plot_grid(
  p_sus, p_fs, p_nut,
  ncol = 3,
  align = "hv",
  axis = "tblr",
  rel_widths = c(1, 1, 1)
)

# Add legend below
final_plot <- plot_grid(
  combined_plot,
  legend_grob,
  ncol = 1,
  rel_heights = c(1, 0.08)
)

# Add overall title
final_plot <- ggdraw(final_plot) +
  draw_label(
    "Strategy Similarity Scores by Country (n = 7)",
    fontface = "bold",
    size = 14,
    x = 0.5,
    y = 0.98,
    hjust = 0.5
  )

# ============================
# SAVE OUTPUTS
# ============================
cat("Saving figures to", output_dir, "...\n")

# Save PDF
ggsave(
  output_pdf,
  plot = final_plot,
  width = 12,
  height = 5,
  units = "in",
  dpi = 300
)
cat("  Saved PDF:", output_pdf, "\n")

# Save PNG
ggsave(
  output_png,
  plot = final_plot,
  width = 12,
  height = 5,
  units = "in",
  dpi = 300,
  bg = "white"
)
cat("  Saved PNG:", output_png, "\n")

cat("\n✅ World map visualization complete!\n")
cat(sprintf("   Countries mapped: %d\n", nrow(country_data)))
cat(sprintf("   Total policies: %d\n", nrow(df)))
