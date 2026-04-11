version 18
clear all
set more off

* ------------------------------------------------------------
* Config
* ------------------------------------------------------------
local input_csv "data/analysis_dataset.csv"
local out_dir "output/econometrics"
local temp_dir "data/temp"
local treat_country "France"
local pre_start 2014
local pre_end 2017
local post_start 2019
local post_end 2022
local requested_lags 12

capture mkdir "`out_dir'"
capture mkdir "`out_dir'/logs"
capture mkdir "`temp_dir'"

log using "`out_dir'/logs/yellow_vests_sdid.log", text replace

* ------------------------------------------------------------
* Import and clean
* ------------------------------------------------------------
import delimited "`input_csv'", varnames(1) encoding(utf8) clear

keep country date_original strategy_sus
keep if !missing(country) & !missing(date_original) & !missing(strategy_sus)
drop if strpos(country, ";") > 0

gen policy_date = daily(date_original, "DMY")
format policy_date %td
keep if !missing(policy_date)
gen year = yofd(policy_date)

* OECD pool map (including France)
gen byte is_oecd = 0
local oecd_countries ///
    `" "Australia" "Austria" "Belgium" "Canada" "Chile" "Colombia" "Costa Rica" "Czechia" "Denmark" "Estonia" "' ///
    `" "Finland" "France" "Germany" "Greece" "Hungary" "Iceland" "Ireland" "Israel" "Italy" "Japan" "' ///
    `" "Latvia" "Lithuania" "Luxembourg" "Mexico" "Netherlands (Kingdom of the)" "New Zealand" "Norway" "Poland" "Portugal" "Republic of Korea" "' ///
    `" "Slovakia" "Slovenia" "Spain" "Sweden" "Switzerland" "Türkiye" "United Kingdom of Great Britain and Northern Ireland" "United States of America" "'
foreach c of local oecd_countries {
    replace is_oecd = 1 if country == "`c'"
}

keep if is_oecd == 1

* Collapse policy-level to country-year panel
collapse (mean) strategy_sus (count) policy_count = strategy_sus, by(country year)
sort country year

* Build observational lags (requested up to 12)
forvalues k = 1/12 {
    by country (year): gen lag`k'_sus = strategy_sus[_n-`k']
}

* Keep near-symmetric window around intervention (drop transition year 2018)
keep if inrange(year, `pre_start', `post_end')
drop if year == 2018

* Keep only countries with complete window support
local n_periods = (`pre_end' - `pre_start' + 1) + (`post_end' - `post_start' + 1)
by country: egen n_obs_window = count(strategy_sus)
keep if n_obs_window == `n_periods'

* Treatment indicator: France in post period
gen byte tr = (country == "`treat_country'" & inrange(year, `post_start', `post_end'))

* Encode group id
egen country_id = group(country), label
xtset country_id year

* Save panel used in SDiD
order country country_id year strategy_sus policy_count tr
export delimited using "`temp_dir'/yellow_vests_country_year_panel.csv", replace

* ------------------------------------------------------------
* Adaptive lag block: start at 12, downshift until feasible
* ------------------------------------------------------------
local chosen_lags 0
local covars ""
forvalues L = `requested_lags'(-1)1 {
    local ok = 1
    forvalues k = 1/`L' {
        quietly count if missing(lag`k'_sus)
        if r(N) > 0 local ok = 0
    }
    if `ok' == 1 {
        local chosen_lags `L'
        local covars ""
        forvalues k = 1/`L' {
            local covars `covars' lag`k'_sus
        }
        continue, break
    }
}

* Always include policy_count as optional intensity covariate when available
quietly count if missing(policy_count)
if r(N) == 0 {
    local covars `covars' policy_count
}

di "Chosen lag depth: `chosen_lags'"
di "Covariates used: `covars'"

* ------------------------------------------------------------
* Run SDiD
* ------------------------------------------------------------
if "`covars'" != "" {
    sdid strategy_sus country_id year tr, vce(placebo) reps(200) seed(20260411) ///
        covariates(`covars', projected) graph g2_opt(xtitle("Year") ytitle("Mean strategy_sus") ///
        title("France vs Synthetic OECD: Yellow Vests SDiD"))
}
else {
    sdid strategy_sus country_id year tr, vce(placebo) reps(200) seed(20260411) ///
        graph g2_opt(xtitle("Year") ytitle("Mean strategy_sus") ///
        title("France vs Synthetic OECD: Yellow Vests SDiD"))
}

* Export figure
capture graph export "`out_dir'/yellow_vests_sdid_trends.png", replace width(2400)

* Export core stats
matrix b = e(b)
matrix V = e(V)
scalar att = b[1,1]
scalar se_att = sqrt(V[1,1])
scalar lb95 = att - invnormal(0.975)*se_att
scalar ub95 = att + invnormal(0.975)*se_att

preserve
clear
set obs 1
gen att = att
gen se = se_att
gen ci95_lb = lb95
gen ci95_ub = ub95
gen chosen_lags = `chosen_lags'
gen pre_start = `pre_start'
gen pre_end = `pre_end'
gen post_start = `post_start'
gen post_end = `post_end'
export delimited using "`out_dir'/yellow_vests_sdid_main.csv", replace
restore

capture postutil clear
tempname fh
postfile `fh' str40 metric str60 value using "`out_dir'/yellow_vests_sdid_main_raw.dta", replace
post `fh' ("att") (string(att, "%9.6f"))
post `fh' ("se") (string(se_att, "%9.6f"))
post `fh' ("ci95_lb") (string(lb95, "%9.6f"))
post `fh' ("ci95_ub") (string(ub95, "%9.6f"))
post `fh' ("chosen_lags") ("`chosen_lags'")
post `fh' ("covariates") ("`covars'")
postclose `fh'

use "`out_dir'/yellow_vests_sdid_main_raw.dta", clear
export delimited using "`out_dir'/yellow_vests_sdid_main.txt", replace
erase "`out_dir'/yellow_vests_sdid_main_raw.dta"

log close
