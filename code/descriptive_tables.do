* Descriptive Statistics for FAOLEX Strategy Similarity Analysis
* Generates LaTeX tables: sample overview, stats by category, top/bottom policies
* Output: output/descriptive_statistics.tex

version 18
clear all
set more off
capture log close

// =====================================================
// CONFIGURATION
// =====================================================
local data_file "data/analysis_dataset.csv"
local output_file "output/descriptive_statistics.tex"

capture mkdir "output"

// =====================================================
// LOAD DATA
// =====================================================
import delimited "`data_file'", stringcols(1 2 3 4 5 6 8 9) clear

// Generate year from date
gen year = real(substr(date_original, -4, .))
format year %4.0g

// =====================================================
// TABLE 1: SAMPLE OVERVIEW
// =====================================================
count
local n_total = r(N)

count if Category == "demand_side"
local n_demand = r(N)

count if Category == "supply_side"
local n_supply = r(N)

count if Category == "unclear"
local n_unclear = r(N)

levelsof country, local(countries)
local n_countries : word count `countries'

levelsof `Language of document', local(languages)
local n_languages : word count `languages'

summarize year, meanonly
local year_min = r(min)
local year_max = r(max)

// Write Table 1 to LaTeX
file open fh using "`output_file'", write text replace
file write fh "% LaTeX tables generated automatically\n\n"

file write fh "\begin{table}[htbp]" _n
file write fh "\centering" _n
file write fh "\caption{Sample Overview (n=`n_total')}" _n
file write fh "\label{tab:sample_overview}" _n
file write fh "\begin{tabular}{lcccc}" _n
file write fh "\toprule" _n
file write fh " & Count & \\" _n
file write fh "\midrule" _n
file write fh "Total Policies & `n_total' & \\" _n
file write fh "\quad Demand-side & `n_demand' & \\" _n
file write fh "\quad Supply-side & `n_supply' & \\" _n
file write fh "\quad Unclear & `n_unclear' & \\" _n
file write fh "\midrule" _n
file write fh "Countries & `n_countries' & \\" _n
file write fh "Languages & `n_languages' & \\" _n
file write fh "Date Range & `year_min'--`year_max' & \\" _n
file write fh "\bottomrule" _n
file write fh "\end{tabular}" _n
file write fh "\end{table}" _n
file write fh _n _n

// =====================================================
// TABLE 2: STRATEGY SIMILARITY BY CATEGORY
// =====================================================
file write fh "\begin{table}[htbp]" _n
file write fh "\centering" _n
file write fh "\caption{Strategy Similarity Scores by Policy Category}" _n
file write fh "\label{tab:strategy_stats_by_category}" _n
file write fh "\begin{tabular}{l l c c c c c}" _n
file write fh "\toprule" _n
file write fh "Category & Strategy & N & Mean & Std & Min & Max & Median \\" _n
file write fh "\midrule" _n

// Categories in order: demand_side, supply_side, unclear
local categories "demand_side supply_side unclear"
local catnames "Demand Side Supply Side Unclear"

local i = 1
foreach cat of local categories {
    local catname : word `i' of `catnames'

    // For each strategy in order: sus, fs, nut
    foreach var in strategy_sus strategy_fs strategy_nut {
        count if Category == "`cat'"
        local n_cat = r(N)

        if `n_cat' > 0 {
            summarize `var' if Category == "`cat'", meanonly
            local mean_val = string(r(mean), "%9.4f")
            local std_val = string(r(sd), "%9.4f")
            local min_val = string(r(min), "%9.4f")
            local max_val = string(r(max), "%9.4f")
            quietly: summ `var' if Category == "`cat'", detail
            local median_val = string(r(p50), "%9.4f")

            // Strategy name
            if "`var'" == "strategy_sus" local stratname "Environmentally Sustainable Strategies"
            if "`var'" == "strategy_fs" local stratname "Food Systems Strategy"
            if "`var'" == "strategy_nut" local stratname "Nutrition Strategy"

            // Multirow for first strategy only
            if "`var'" == "strategy_sus" {
                file write fh "\multirow{3}{*}{`catname'} & `stratname' & `n_cat' & `mean_val' & `std_val' & `min_val' & `max_val' & `median_val' \\" _n
            }
            else {
                file write fh " & `stratname' & `n_cat' & `mean_val' & `std_val' & `min_val' & `max_val' & `median_val' \\" _n
            }
        }
    }
    local i = `i' + 1
}

file write fh "\bottomrule" _n
file write fh "\end{tabular}" _n
file write fh "\end{table}" _n
file write fh _n _n

// =====================================================
// TABLE 3: TOP AND BOTTOM POLICIES FOR EACH STRATEGY
// =====================================================
foreach var in strategy_sus strategy_fs strategy_nut {
    if "`var'" == "strategy_sus" local stratname "Environmentally Sustainable Strategies"
    if "`var'" == "strategy_fs" local stratname "Food Systems Strategy"
    if "`var'" == "strategy_nut" local stratname "Nutrition Strategy"

    file write fh "\subsubsection{`stratname'}" _n
    file write fh "\begin{table}[htbp]" _n
    file write fh "\centering" _n
    file write fh "\begin{tabular}{l l l c}" _n
    file write fh "\toprule" _n
    file write fh " & Country & Category & Similarity \\" _n

    // Top 5
    file write fh "\midrule" _n
    file write fh "\multicolumn{4}{c}{\textbf{Top 5}} \\" _n

    // Get top 5
    tempvar rank_top
    gen `rank_top' = .
    egen `rank_top' = rank(-`var'), field
    keep if `rank_top' <= 5 & !missing(`var')
    sort `rank_top'

    local topN = _N
    forvalues i = 1/`topN' {
        local rec_id = record_id[`i']
        local country = country[`i']
        local category = Category[`i']
        local cat_display = subinstr("`category'", "_", " ", .)
        local cat_display = strupper(substr("`cat_display'", 1, 1)) + substr("`cat_display'", 2, .)
        local sim = string(`var'[`i'], "%9.4f")
        file write fh "`rec_id' & `country' & `cat_display' & `sim' \\" _n
    }

    // Bottom 5
    file write fh "\midrule" _n
    file write fh "\multicolumn{4}{c}{\textbf{Bottom 5}} \\" _n

    // Get bottom 5 (from full dataset, not just top)
    use "`data_file'", clear
    // Keep only valid category and strategy values
    drop if missing(`var') | missing(Category)
    gen `rank_bot' = .
    egen `rank_bot' = rank(`var'), field
    keep if `rank_bot' <= 5
    sort `rank_bot'

    local botN = _N
    forvalues i = 1/`botN' {
        local rec_id = record_id[`i']
        local country = country[`i']
        local category = Category[`i']
        local cat_display = subinstr("`category'", "_", " ", .)
        local cat_display = strupper(substr("`cat_display'", 1, 1)) + substr("`cat_display'", 2, .)
        local sim = string(`var'[`i'], "%9.4f")
        file write fh "`rec_id' & `country' & `cat_display' & `sim' \\" _n
    }

    file write fh "\bottomrule" _n
    file write fh "\end{tabular}" _n
    file write fh "\caption{Top and bottom policies for `stratname'}" _n
    file write fh "\label{tab:top_bottom_" + substr("`var'", 10, .) + "}" _n
    file write fh "\end{table}" _n
    file write fh _n

    // Reload main dataset for next strategy
    use "`data_file'", clear
}

file close fh

display "LaTeX tables saved to `output_file'"
