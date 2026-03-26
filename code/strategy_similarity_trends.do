* Strategy Similarity Time Trends Analysis
* This do-file creates line graphs showing evolution of cosine similarity scores
* for three strategy dimensions across time, comparing all policies vs demand-side vs supply-side

version 18
clear all

// =====================================================
// CONFIGURATION
// =====================================================
local data_file "data/strategy_similarities_with_dates.csv"
local output_dir "output"

// Ensure output directory exists
capture mkdir "`output_dir'"

// =====================================================
// LOAD AND PREPARE DATA
// =====================================================
import delimited "`data_file'", stringcols(1 2 3 4) clear

// Convert date from DD-MM-YYYY to Stata date
gen date_raw = date(date_original, "DMY")
format date_raw %tdDD-Mon-YYYY
drop if missing(date_raw)

// Extract year for aggregation
gen year = year(date_raw)

// Generate indicator variables
gen is_demand = (category == "demand_side")
gen is_supply = (category == "supply_side")
gen is_all = 1

// Keep relevant variables
keep year is_* sus fs nut

// =====================================================
// AGGREGATE BY YEAR AND CATEGORY AND PLOT
// =====================================================

// Preserve original data for repeated use
preserve

// ---------- Strategy SUS ----------
keep year is_demand is_supply sus
gen group_type = .
replace group_type = 0 if 1  // all = 0 (use original value directly)
replace group_type = 1 if is_demand == 1
replace group_type = 2 if is_supply == 1
collapse (mean) sus, by(year group_type)
reshape wide sus, i(year) j(group_type)
rename sus0 sus_all
rename sus1 sus_demand
rename sus2 sus_supply
sort year

twoway ///
    (line sus_all year, lcolor(black) lwidth(medium) lpattern(solid) msymbol(O) mcolor(black)) ///
    (line sus_demand year, lcolor(blue) lwidth(medium) lpattern(dash) msymbol(T) mcolor(blue)) ///
    (line sus_supply year, lcolor(red) lwidth(medium) lpattern(dot) msymbol(S) mcolor(red)) ///
    , ///
    title("") ///
    legend(order(1 "All Policies" 2 "Demand-Side" 3 "Supply-Side") ring(0) position(6) cols(1)) ///
    ylabel(, angle(horizontal) format(%4.2f)) ///
    xlabel(, angle(45)) ///
    ytitle("Strategy Sus Cosine Similarity") ///
    xtitle("Year") ///
    graphregion(fcolor(white) lcolor(white) ifcolor(white) ilcolor(white)) ///
    plotregion(fcolor(white) lcolor(white))

graph export "`output_dir'/strategy_sus_trends.png", replace width(1600) height(900)
graph export "`output_dir'/strategy_sus_trends.pdf", replace
display "Created: `output_dir'/strategy_sus_trends.png"

restore

// ---------- Strategy FS ----------
preserve
keep year is_demand is_supply fs
gen group_type = .
replace group_type = 0 if 1
replace group_type = 1 if is_demand == 1
replace group_type = 2 if is_supply == 1
collapse (mean) fs, by(year group_type)
reshape wide fs, i(year) j(group_type)
rename fs0 fs_all
rename fs1 fs_demand
rename fs2 fs_supply
sort year

twoway ///
    (line fs_all year, lcolor(black) lwidth(medium) lpattern(solid) msymbol(O) mcolor(black)) ///
    (line fs_demand year, lcolor(blue) lwidth(medium) lpattern(dash) msymbol(T) mcolor(blue)) ///
    (line fs_supply year, lcolor(red) lwidth(medium) lpattern(dot) msymbol(S) mcolor(red)) ///
    , ///
    title("") ///
    legend(order(1 "All Policies" 2 "Demand-Side" 3 "Supply-Side") ring(0) position(6) cols(1)) ///
    ylabel(, angle(horizontal) format(%4.2f)) ///
    xlabel(, angle(45)) ///
    ytitle("Strategy FS Cosine Similarity") ///
    xtitle("Year") ///
    graphregion(fcolor(white) lcolor(white) ifcolor(white) ilcolor(white)) ///
    plotregion(fcolor(white) lcolor(white))

graph export "`output_dir'/strategy_fs_trends.png", replace width(1600) height(900)
graph export "`output_dir'/strategy_fs_trends.pdf", replace
display "Created: `output_dir'/strategy_fs_trends.png"
restore

// ---------- Strategy NUT ----------
preserve
keep year is_demand is_supply nut
gen group_type = .
replace group_type = 0 if 1
replace group_type = 1 if is_demand == 1
replace group_type = 2 if is_supply == 1
collapse (mean) nut, by(year group_type)
reshape wide nut, i(year) j(group_type)
rename nut0 nut_all
rename nut1 nut_demand
rename nut2 nut_supply
sort year

twoway ///
    (line nut_all year, lcolor(black) lwidth(medium) lpattern(solid) msymbol(O) mcolor(black)) ///
    (line nut_demand year, lcolor(blue) lwidth(medium) lpattern(dash) msymbol(T) mcolor(blue)) ///
    (line nut_supply year, lcolor(red) lwidth(medium) lpattern(dot) msymbol(S) mcolor(red)) ///
    , ///
    title("") ///
    legend(order(1 "All Policies" 2 "Demand-Side" 3 "Supply-Side") ring(0) position(6) cols(1)) ///
    ylabel(, angle(horizontal) format(%4.2f)) ///
    xlabel(, angle(45)) ///
    ytitle("Strategy Nut Cosine Similarity") ///
    xtitle("Year") ///
    graphregion(fcolor(white) lcolor(white) ifcolor(white) ilcolor(white)) ///
    plotregion(fcolor(white) lcolor(white))

graph export "`output_dir'/strategy_nut_trends.png", replace width(1600) height(900)
graph export "`output_dir'/strategy_nut_trends.pdf", replace
display "Created: `output_dir'/strategy_nut_trends.png"
restore

// =====================================================
// CLEANUP
// =====================================================
clear all

display "All figures saved to `output_dir'/"
display "Files created:"
display "  - strategy_sus_trends.png/pdf"
display "  - strategy_fs_trends.png/pdf"
display "  - strategy_nut_trends.png/pdf"
