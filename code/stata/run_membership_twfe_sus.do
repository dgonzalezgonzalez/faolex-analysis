version 18
clear all
set more off

local input_csv "data/analysis_dataset.csv"
local out_dir "output/econometrics"
local temp_dir "data/temp"
local log_dir "`out_dir'/logs"

local outcome "strategy_sus"
local window 5
local min_side 4
local min_year_obs 8

capture mkdir "`out_dir'"
capture mkdir "`temp_dir'"
capture mkdir "`log_dir'"

log using "`log_dir'/membership_twfe_sus.log", text replace

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

bysort country_id: egen n_year_nonmiss = total(!missing(`outcome'))
keep if n_year_nonmiss >= `min_year_obs'

tempfile base_panel
save `base_panel', replace

* ------------------------------------------------------------
* Postfiles
* ------------------------------------------------------------
tempname rs
postfile `rs' str8 organization double beta se ci95_lb ci95_ub ///
    int n_countries n_treated n_controls N window min_side using ///
    "`out_dir'/membership_twfe_static_results_raw.dta", replace

tempname es
postfile `es' str8 organization int rel_time double beta se ci95_lb ci95_ub ///
    str6 side using "`out_dir'/membership_twfe_eventstudy_raw.dta", replace

tempname ms
postfile `ms' str8 organization str120 country int entry_year int exit_year byte in_data ///
    using "`out_dir'/membership_entry_years_raw.dta", replace

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
    local min_cal = r(min) - `window'
    local max_cal = r(max) + `window'

    keep if inrange(year, `min_cal', `max_cal')

    gen byte in_sym_window = ever_treated == 1 & inrange(rel_time, -`window', `window')
    by country_id: egen npre = total(!missing(`outcome') & inrange(rel_time, -`window', -1))
    by country_id: egen npost = total(!missing(`outcome') & inrange(rel_time, 0, `window'))
    keep if ever_treated == 0 | (npre >= `min_side' & npost >= `min_side')

    by country_id: egen has_outcome = total(!missing(`outcome'))
    keep if has_outcome > 0

    egen cid = group(country)
    quietly xtset cid year

    * Entry-year table (only countries present after filters)
    preserve
        egen __tag_m = tag(country)
        quietly count if __tag_m == 1
        local nm = r(N)
        forvalues i = 1/`=_N' {
            if __tag_m[`i'] == 1 {
                local c = country[`i']
                local e = entry_year[`i']
                local x = exit_year[`i']
                local d = !missing(entry_year[`i'])
                post `ms' ("`org'") ("`c'") (`e') (`x') (`d')
            }
        }
    restore

    preserve
        keep if !missing(`outcome')
        export delimited country cid year `outcome' policy_count treated ever_treated entry_year exit_year rel_time ///
            using "`temp_dir'/membership_`org'_twfe_panel.csv", replace
    restore

    * Static TWFE
    quietly xtreg `outcome' treated i.year if !missing(`outcome'), fe vce(cluster cid)
    quietly lincom treated
    scalar b_hat = r(estimate)
    scalar lb_hat = r(lb)
    scalar ub_hat = r(ub)
    scalar se_hat = (ub_hat - b_hat) / invnormal(0.975)
    local b_val = b_hat
    local s_val = se_hat
    local lb_val = lb_hat
    local ub_val = ub_hat

    egen __tag_c = tag(cid)
    quietly count if __tag_c == 1
    local n_c = r(N)
    quietly count if __tag_c == 1 & ever_treated == 1
    local n_t = r(N)
    quietly count if __tag_c == 1 & ever_treated == 0
    local n_n = r(N)
    quietly count if e(sample)
    local n_obs = r(N)
    drop __tag_c

    post `rs' ("`org'") (`b_val') (`s_val') (`lb_val') (`ub_val') (`n_c') (`n_t') (`n_n') (`n_obs') (`window') (`min_side')

    * Event-study TWFE with symmetric relative window
    forvalues k = 1/`window' {
        capture drop evt_m`k'
        gen byte evt_m`k' = (ever_treated == 1 & rel_time == -`k')
    }
    forvalues k = 0/`window' {
        capture drop evt_p`k'
        gen byte evt_p`k' = (ever_treated == 1 & rel_time == `k')
    }

    local rhs ""
    forvalues k = `window'(-1)2 {
        local rhs `rhs' evt_m`k'
    }
    forvalues k = 0/`window' {
        local rhs `rhs' evt_p`k'
    }

    quietly xtreg `outcome' `rhs' i.year if !missing(`outcome'), fe vce(cluster cid)

    forvalues k = `window'(-1)2 {
        local v = "evt_m`k'"
        scalar bb = _b[`v']
        scalar ss = _se[`v']
        scalar ll = bb - invnormal(0.975)*ss
        scalar uu = bb + invnormal(0.975)*ss
        post `es' ("`org'") (-`k') (bb) (ss) (ll) (uu) ("pre")
    }
    forvalues k = 0/`window' {
        local v = "evt_p`k'"
        scalar bb = _b[`v']
        scalar ss = _se[`v']
        scalar ll = bb - invnormal(0.975)*ss
        scalar uu = bb + invnormal(0.975)*ss
        post `es' ("`org'") (`k') (bb) (ss) (ll) (uu) ("post")
    }

    testparm evt_m*
    scalar p_pre = r(p)

    * Save p-value of pre-trend in tiny temp file for merge later
    preserve
        clear
        set obs 1
        gen str8 organization = "`org'"
        gen double pretrend_pvalue = p_pre
        save "`temp_dir'/membership_`org'_pretrend_pvalue.dta", replace
    restore
}

postclose `rs'
postclose `es'
postclose `ms'

* ------------------------------------------------------------
* Export static results
* ------------------------------------------------------------
use "`out_dir'/membership_twfe_static_results_raw.dta", clear
merge 1:1 organization using "`temp_dir'/membership_oecd_pretrend_pvalue.dta", nogen update replace
merge 1:1 organization using "`temp_dir'/membership_eu_pretrend_pvalue.dta", nogen update replace
order organization beta se ci95_lb ci95_ub pretrend_pvalue n_countries n_treated n_controls N window min_side
export delimited using "`out_dir'/membership_twfe_static_results.csv", replace
save "`out_dir'/membership_twfe_static_results.dta", replace

* ------------------------------------------------------------
* Export event-study table + figures
* ------------------------------------------------------------
use "`out_dir'/membership_twfe_eventstudy_raw.dta", clear
sort organization rel_time
export delimited using "`out_dir'/membership_twfe_eventstudy_results.csv", replace
save "`out_dir'/membership_twfe_eventstudy_results.dta", replace

levelsof organization, local(orgs)
foreach o of local orgs {
    preserve
        keep if organization == "`o'"
        sort rel_time
        twoway ///
            (rcap ci95_lb ci95_ub rel_time, lcolor(navy%60)) ///
            (scatter beta rel_time, mcolor(navy) msymbol(O) msize(medsmall)) ///
            (line beta rel_time, lcolor(navy) lwidth(medthick)) ///
            , yline(0, lcolor(maroon) lpattern(dash)) ///
              xline(-1, lcolor(gs8) lpattern(shortdash)) ///
              xtitle("Relative year to entry (k)") ///
              ytitle("TWFE coefficient on event time dummies") ///
              title("`=upper("`o'")' membership: annual TWFE event-study (`outcome')") ///
              legend(off)
        graph export "`out_dir'/membership_`o'_twfe_eventstudy.png", replace width(2200)
    restore
}

* ------------------------------------------------------------
* Export entry-year table
* ------------------------------------------------------------
use "`out_dir'/membership_entry_years_raw.dta", clear
sort organization country
export delimited using "`out_dir'/membership_entry_years.csv", replace
save "`out_dir'/membership_entry_years.dta", replace

log close
