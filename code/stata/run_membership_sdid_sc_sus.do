version 18
clear all
set more off

local input_csv "data/analysis_dataset.csv"
local out_dir "output/econometrics"
local temp_dir "data/temp"
local log_dir "`out_dir'/logs"

local outcome "strategy_sus"
local seed 20260411
local requested_lags 12
local window 5
local min_side 4
local min_raw_control 8

capture mkdir "`out_dir'"
capture mkdir "`temp_dir'"
capture mkdir "`log_dir'"

log using "`log_dir'/membership_sdid_sc_sus.log", text replace

* ------------------------------------------------------------
* Build annual country panel (all policies)
* ------------------------------------------------------------
import delimited "`input_csv'", varnames(1) encoding(utf8) clear
keep country date_original `outcome'
keep if !missing(country) & !missing(date_original) & !missing(`outcome')
drop if strpos(country, ";") > 0

gen policy_date = daily(date_original, "DMY")
replace policy_date = daily(date_original, "YMD") if missing(policy_date)
gen year_only = real(date_original) if missing(policy_date) & regexm(trim(date_original), "^[0-9]{4}$")
replace policy_date = mdy(7, 1, year_only) if missing(policy_date) & !missing(year_only)
drop year_only
format policy_date %td
keep if !missing(policy_date)

gen year = yofd(policy_date)
keep if inrange(year, 1950, 2025)

collapse (mean) `outcome' (count) policy_count = `outcome', by(country year)
gen byte raw_obs = 1

egen country_id = group(country), label
xtset country_id year
tsfill, full

drop country
decode country_id, gen(country)
replace raw_obs = 0 if missing(raw_obs)
replace policy_count = 0 if missing(policy_count)

* Fill outcome to get balanced panel required by synthetic methods
bysort country_id (year): replace `outcome' = `outcome'[_n-1] if missing(`outcome')
gsort country_id -year
by country_id: replace `outcome' = `outcome'[_n-1] if missing(`outcome')
sort country_id year
by country_id: egen country_mean_sus = mean(`outcome')
replace `outcome' = country_mean_sus if missing(`outcome')
quietly summarize `outcome'
replace `outcome' = r(mean) if missing(`outcome')
drop country_mean_sus

bysort country_id: egen n_year_nonmiss = total(!missing(`outcome'))
keep if n_year_nonmiss >= 10

tempfile base_panel
save `base_panel', replace

* ------------------------------------------------------------
* Result collector
* ------------------------------------------------------------
tempname rs
postfile `rs' str8 organization str6 method double att se ci95_lb ci95_ub ///
    int chosen_lags int n_countries int n_treated int n_controls int n_obs ///
    int year_min int year_max int rc str180 covariates ///
    using "`out_dir'/membership_sdid_sc_sus_results_raw.dta", replace

foreach org in oecd eu {

    use `base_panel', clear

    gen entry_year = .
    gen exit_year = .

    if "`org'" == "oecd" {
        replace entry_year = 1961 if country == "Austria"
        replace entry_year = 1961 if country == "Belgium"
        replace entry_year = 1961 if country == "Canada"
        replace entry_year = 1961 if country == "Denmark"
        replace entry_year = 1961 if country == "France"
        replace entry_year = 1961 if country == "Germany"
        replace entry_year = 1961 if country == "Greece"
        replace entry_year = 1961 if country == "Iceland"
        replace entry_year = 1961 if country == "Ireland"
        replace entry_year = 1961 if country == "Italy"
        replace entry_year = 1961 if country == "Luxembourg"
        replace entry_year = 1961 if country == "Netherlands (Kingdom of the)"
        replace entry_year = 1961 if country == "Norway"
        replace entry_year = 1961 if country == "Portugal"
        replace entry_year = 1961 if country == "Spain"
        replace entry_year = 1961 if country == "Sweden"
        replace entry_year = 1961 if country == "Switzerland"
        replace entry_year = 1961 if country == "Türkiye"
        replace entry_year = 1961 if country == "United Kingdom of Great Britain and Northern Ireland"
        replace entry_year = 1961 if country == "United States of America"
        replace entry_year = 1962 if country == "Japan"
        replace entry_year = 1964 if country == "Finland"
        replace entry_year = 1969 if country == "Australia"
        replace entry_year = 1973 if country == "New Zealand"
        replace entry_year = 1994 if country == "Mexico"
        replace entry_year = 1995 if country == "Czechia"
        replace entry_year = 1996 if country == "Hungary"
        replace entry_year = 1996 if country == "Poland"
        replace entry_year = 1996 if country == "Republic of Korea"
        replace entry_year = 2000 if country == "Slovakia"
        replace entry_year = 2010 if country == "Chile"
        replace entry_year = 2010 if country == "Slovenia"
        replace entry_year = 2010 if country == "Israel"
        replace entry_year = 2010 if country == "Estonia"
        replace entry_year = 2016 if country == "Latvia"
        replace entry_year = 2018 if country == "Lithuania"
        replace entry_year = 2020 if country == "Colombia"
        replace entry_year = 2021 if country == "Costa Rica"
    }

    if "`org'" == "eu" {
        replace entry_year = 1958 if country == "Belgium"
        replace entry_year = 1958 if country == "France"
        replace entry_year = 1958 if country == "Germany"
        replace entry_year = 1958 if country == "Italy"
        replace entry_year = 1958 if country == "Luxembourg"
        replace entry_year = 1958 if country == "Netherlands (Kingdom of the)"
        replace entry_year = 1973 if country == "Denmark"
        replace entry_year = 1973 if country == "Ireland"
        replace entry_year = 1973 if country == "United Kingdom of Great Britain and Northern Ireland"
        replace entry_year = 1981 if country == "Greece"
        replace entry_year = 1986 if country == "Spain"
        replace entry_year = 1986 if country == "Portugal"
        replace entry_year = 1995 if country == "Austria"
        replace entry_year = 1995 if country == "Finland"
        replace entry_year = 1995 if country == "Sweden"
        replace entry_year = 2004 if country == "Czechia"
        replace entry_year = 2004 if country == "Estonia"
        replace entry_year = 2004 if country == "Cyprus"
        replace entry_year = 2004 if country == "Latvia"
        replace entry_year = 2004 if country == "Lithuania"
        replace entry_year = 2004 if country == "Hungary"
        replace entry_year = 2004 if country == "Malta"
        replace entry_year = 2004 if country == "Poland"
        replace entry_year = 2004 if country == "Slovakia"
        replace entry_year = 2004 if country == "Slovenia"
        replace entry_year = 2007 if country == "Bulgaria"
        replace entry_year = 2007 if country == "Romania"
        replace entry_year = 2013 if country == "Croatia"
        replace exit_year = 2020 if country == "United Kingdom of Great Britain and Northern Ireland"
    }

    gen byte ever_treated = !missing(entry_year)
    gen byte treated = (ever_treated == 1 & year >= entry_year)
    replace treated = 0 if !missing(exit_year) & year > exit_year

    gen rel_time = year - entry_year if ever_treated

    quietly summarize entry_year if ever_treated
    local ymin = r(min) - `window'
    local ymax = r(max) + `window'

    keep if inrange(year, `ymin', `ymax')
    gen byte core_window = 1

    by country_id: egen pre_raw = total(raw_obs * inrange(rel_time, -`window', -1))
    by country_id: egen post_raw = total(raw_obs * inrange(rel_time, 0, `window'))
    by country_id: egen total_raw = total(raw_obs)

    keep if (ever_treated == 0 & total_raw >= `min_raw_control') | ///
            (ever_treated == 1 & pre_raw >= `min_side' & post_raw >= `min_side')

    egen __tag_c = tag(country_id)
    quietly count if __tag_c == 1
    local n_c = r(N)
    quietly count if __tag_c == 1 & ever_treated == 1
    local n_t = r(N)
    quietly count if __tag_c == 1 & ever_treated == 0
    local n_n = r(N)
    drop __tag_c

    if (`n_t' == 0 | `n_n' < 2) {
        post `rs' ("`org'") ("skip") (.) (.) (.) (.) (.) (`n_c') (`n_t') (`n_n') (.) (`ymin') (`ymax') (499) ("insufficient treated/control countries")
        continue
    }

    export delimited country year `outcome' policy_count treated ever_treated entry_year rel_time ///
        using "`temp_dir'/membership_`org'_sdid_sc_panel.csv", replace

    * Lags for SDID covariates
    sort country_id year
    forvalues k = 1/`requested_lags' {
        by country_id (year): gen lag`k'_sus = `outcome'[_n-`k']
        by country_id (year): replace lag`k'_sus = lag`k'_sus[_n-1] if missing(lag`k'_sus)
        gsort country_id -year
        by country_id: replace lag`k'_sus = lag`k'_sus[_n-1] if missing(lag`k'_sus)
        sort country_id year
    }

    local chosen_lags = 0
    local covars ""
    forvalues L = `requested_lags'(-1)1 {
        local ok = 1
        forvalues k = 1/`L' {
            quietly count if core_window == 1 & missing(lag`k'_sus)
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

    * Add policy_count as optional covariate
    quietly count if missing(policy_count)
    if r(N) == 0 local covars `covars' policy_count

    foreach m in sdid sc {
        gen byte tr = treated
        local this_cov ""
        if "`m'" == "sdid" local this_cov "`covars'"

        local gfile "`out_dir'/membership_`org'_`m'_sus_trends.png"

        capture noisily {
            if "`m'" == "sdid" {
                sdid `outcome' country_id year tr if core_window == 1, vce(noinference) ///
                    covariates(`this_cov', projected) graph ///
                    g2_opt(xtitle("Year") ytitle("Mean strategy_sus") ///
                    title("`=upper("`org'")' entry: annual SDID (strategy_sus)"))
            }
            else {
                sdid `outcome' country_id year tr if core_window == 1, vce(noinference) ///
                    method(sc) graph ///
                    g2_opt(xtitle("Year") ytitle("Mean strategy_sus") ///
                    title("`=upper("`org'")' entry: annual SC (strategy_sus)"))
            }

            scalar att = e(ATT)
            scalar se_att = e(se)
            scalar lb95 = .
            scalar ub95 = .
            if se_att < . {
                scalar lb95 = att - invnormal(0.975)*se_att
                scalar ub95 = att + invnormal(0.975)*se_att
            }

            graph export "`gfile'", replace width(2200)

            quietly count if core_window == 1
            local nobs = r(N)

            post `rs' ("`org'") ("`m'") (att) (se_att) (lb95) (ub95) ///
                (`chosen_lags') (`n_c') (`n_t') (`n_n') (`nobs') (`ymin') (`ymax') (0) ("`this_cov'")
        }

        if _rc {
            local rcx = _rc
            quietly count if core_window == 1
            local nobs = r(N)
            post `rs' ("`org'") ("`m'") (.) (.) (.) (.) ///
                (`chosen_lags') (`n_c') (`n_t') (`n_n') (`nobs') (`ymin') (`ymax') (`rcx') ("`this_cov'")
        }

        drop tr
    }
}

postclose `rs'

use "`out_dir'/membership_sdid_sc_sus_results_raw.dta", clear
order organization method att se ci95_lb ci95_ub chosen_lags n_countries n_treated n_controls n_obs year_min year_max rc covariates
export delimited using "`out_dir'/membership_sdid_sc_sus_results.csv", replace
save "`out_dir'/membership_sdid_sc_sus_results.dta", replace

log close
