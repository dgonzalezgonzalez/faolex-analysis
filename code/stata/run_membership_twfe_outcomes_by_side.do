version 18
clear all
set more off

local input_csv "data/analysis_dataset.csv"
local out_dir "output/econometrics"
local temp_dir "data/temp"
local log_dir "`out_dir'/logs"

local pre_window 10
local post_window 10
local min_pre 4
local min_post 4
local min_control_obs 10

capture mkdir "`out_dir'"
capture mkdir "`temp_dir'"
capture mkdir "`log_dir'"

log using "`log_dir'/membership_twfe_outcomes_by_side.log", text replace

* ------------------------------------------------------------
* Base annual panel by side
* ------------------------------------------------------------
import delimited "`input_csv'", varnames(1) encoding(utf8) clear
capture confirm variable Category
if _rc == 0 rename Category category
keep country date_original category strategy_sus strategy_fs strategy_nut
keep if !missing(country) & !missing(date_original)
drop if strpos(country, ";") > 0

gen str20 side = lower(trim(category))
keep if inlist(side, "supply_side", "demand_side")

gen policy_date = daily(date_original, "DMY")
replace policy_date = daily(date_original, "YMD") if missing(policy_date)
gen year_only = real(date_original) if missing(policy_date) & regexm(trim(date_original), "^[0-9]{4}$")
replace policy_date = mdy(7, 1, year_only) if missing(policy_date) & !missing(year_only)
drop year_only
format policy_date %td
keep if !missing(policy_date)

gen year = yofd(policy_date)
keep if inrange(year, 1950, 2025)

collapse (mean) strategy_sus strategy_fs strategy_nut (count) policy_count = policy_date, by(country year side)
gen byte raw_obs = 1

egen country_id = group(country), label
egen panel_id = group(country side), label
xtset panel_id year
tsfill, full

replace raw_obs = 0 if missing(raw_obs)
replace policy_count = 0 if missing(policy_count)
bysort panel_id (year): replace strategy_fs = strategy_fs[_n-1] if missing(strategy_fs)
bysort panel_id (year): replace strategy_nut = strategy_nut[_n-1] if missing(strategy_nut)
bysort panel_id (year): replace strategy_sus = strategy_sus[_n-1] if missing(strategy_sus)
gsort panel_id -year
by panel_id: replace strategy_fs = strategy_fs[_n-1] if missing(strategy_fs)
by panel_id: replace strategy_nut = strategy_nut[_n-1] if missing(strategy_nut)
by panel_id: replace strategy_sus = strategy_sus[_n-1] if missing(strategy_sus)
sort panel_id year

tempfile base_panel
save `base_panel', replace

* ------------------------------------------------------------
* Collectors
* ------------------------------------------------------------
tempname rs
postfile `rs' str12 outcome str12 side str8 organization double beta se ci95_lb ci95_ub pretrend_pvalue ///
    int n_countries n_treated n_controls N pre_window post_window min_pre min_post year_min year_max ///
    using "`out_dir'/membership_twfe_outcomes_by_side_static_raw.dta", replace

tempname es
postfile `es' str12 outcome str12 side str8 organization int rel_time double beta se ci95_lb ci95_ub str6 period ///
    using "`out_dir'/membership_twfe_outcomes_by_side_eventstudy_raw.dta", replace

foreach sidev in supply_side demand_side {
    foreach outcome in policy_count strategy_sus strategy_fs strategy_nut {
        foreach org in oecd eu {

            use `base_panel', clear
            keep if side == "`sidev'"

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

            gen y = .
            if "`outcome'" == "policy_count" replace y = policy_count
            if "`outcome'" == "strategy_sus" replace y = strategy_sus
            if "`outcome'" == "strategy_fs" replace y = strategy_fs
            if "`outcome'" == "strategy_nut" replace y = strategy_nut

            gen byte ever_treated = !missing(entry_year)
            gen byte treated = (ever_treated == 1 & year >= entry_year)
            replace treated = 0 if !missing(exit_year) & year > exit_year
            gen rel_time = year - entry_year if ever_treated

            quietly summarize entry_year if ever_treated
            local ymin = r(min) - `pre_window'
            local ymax = r(max) + `post_window'
            keep if inrange(year, `ymin', `ymax')

            by panel_id: egen pre_obs = total(!missing(y) * inrange(rel_time, -`pre_window', -1))
            by panel_id: egen post_obs = total(!missing(y) * inrange(rel_time, 0, `post_window'))
            by panel_id: egen all_obs = total(!missing(y))
            keep if (ever_treated == 0 & all_obs >= `min_control_obs') | (ever_treated == 1 & pre_obs >= `min_pre' & post_obs >= `min_post')

            egen __tagc = tag(panel_id)
            quietly count if __tagc == 1
            local n_c = r(N)
            quietly count if __tagc == 1 & ever_treated == 1
            local n_t = r(N)
            quietly count if __tagc == 1 & ever_treated == 0
            local n_n = r(N)
            drop __tagc

            if (`n_t' == 0 | `n_n' < 2) {
                post `rs' ("`outcome'") ("`sidev'") ("`org'") (.) (.) (.) (.) (.) ///
                    (`n_c') (`n_t') (`n_n') (.) (`pre_window') (`post_window') (`min_pre') (`min_post') (`ymin') (`ymax')
                continue
            }

            quietly reghdfe y treated if !missing(y), absorb(panel_id year) vce(cluster panel_id)
            scalar b_hat = _b[treated]
            scalar se_hat = _se[treated]
            if missing(se_hat) {
                quietly lincom treated
                scalar b_hat = r(estimate)
                scalar lb_tmp = r(lb)
                scalar ub_tmp = r(ub)
                scalar se_hat = (ub_tmp - b_hat) / invnormal(0.975)
            }
            scalar lb_hat = b_hat - invnormal(0.975)*se_hat
            scalar ub_hat = b_hat + invnormal(0.975)*se_hat

            forvalues k = 1/`pre_window' {
                capture drop evt_m`k'
                gen byte evt_m`k' = (ever_treated == 1 & rel_time == -`k')
            }
            forvalues k = 0/`post_window' {
                capture drop evt_p`k'
                gen byte evt_p`k' = (ever_treated == 1 & rel_time == `k')
            }

            local rhs ""
            forvalues k = `pre_window'(-1)2 {
                local rhs `rhs' evt_m`k'
            }
            forvalues k = 0/`post_window' {
                local rhs `rhs' evt_p`k'
            }

            quietly reghdfe y `rhs' if !missing(y), absorb(panel_id year) vce(cluster panel_id)
            testparm evt_m*
            scalar p_pre = r(p)

            forvalues k = `pre_window'(-1)2 {
                local vv = "evt_m`k'"
                capture scalar bb = _b[`vv']
                if _rc scalar bb = .
                capture scalar ss = _se[`vv']
                if _rc scalar ss = .
                scalar ll = .
                scalar uu = .
                if !missing(ss) {
                    scalar ll = bb - invnormal(0.975)*ss
                    scalar uu = bb + invnormal(0.975)*ss
                }
                post `es' ("`outcome'") ("`sidev'") ("`org'") (-`k') (bb) (ss) (ll) (uu) ("pre")
            }
            post `es' ("`outcome'") ("`sidev'") ("`org'") (-1) (0) (0) (0) (0) ("pre")

            forvalues k = 0/`post_window' {
                local vv = "evt_p`k'"
                capture scalar bb = _b[`vv']
                if _rc scalar bb = .
                capture scalar ss = _se[`vv']
                if _rc scalar ss = .
                scalar ll = .
                scalar uu = .
                if !missing(ss) {
                    scalar ll = bb - invnormal(0.975)*ss
                    scalar uu = bb + invnormal(0.975)*ss
                }
                post `es' ("`outcome'") ("`sidev'") ("`org'") (`k') (bb) (ss) (ll) (uu) ("post")
            }

            quietly count if e(sample)
            local n_obs = r(N)
            post `rs' ("`outcome'") ("`sidev'") ("`org'") (b_hat) (se_hat) (lb_hat) (ub_hat) (p_pre) ///
                (`n_c') (`n_t') (`n_n') (`n_obs') (`pre_window') (`post_window') (`min_pre') (`min_post') (`ymin') (`ymax')
        }
    }
}

postclose `rs'
postclose `es'

use "`out_dir'/membership_twfe_outcomes_by_side_static_raw.dta", clear
order outcome side organization beta se ci95_lb ci95_ub pretrend_pvalue n_countries n_treated n_controls N pre_window post_window min_pre min_post year_min year_max
export delimited using "`out_dir'/membership_twfe_outcomes_by_side_static_results.csv", replace
save "`out_dir'/membership_twfe_outcomes_by_side_static_results.dta", replace

use "`out_dir'/membership_twfe_outcomes_by_side_eventstudy_raw.dta", clear
sort outcome side organization rel_time
export delimited using "`out_dir'/membership_twfe_outcomes_by_side_eventstudy_results.csv", replace
save "`out_dir'/membership_twfe_outcomes_by_side_eventstudy_results.dta", replace

levelsof outcome, local(outcomes)
foreach oo of local outcomes {
    levelsof side, local(sides)
    foreach ss of local sides {
        levelsof organization if outcome == "`oo'" & side == "`ss'", local(orgs)
        foreach org of local orgs {
            preserve
                keep if outcome == "`oo'" & side == "`ss'" & organization == "`org'"
                sort rel_time
                twoway ///
                    (rcap ci95_lb ci95_ub rel_time, lcolor(navy%60)) ///
                    (scatter beta rel_time, mcolor(navy) msymbol(O) msize(small)) ///
                    (line beta rel_time, lcolor(navy) lwidth(medthick)) ///
                    , yline(0, lcolor(maroon) lpattern(dash)) ///
                      xline(-1, lcolor(gs8) lpattern(shortdash)) ///
                      xlabel(-10(1)10) ///
                      xtitle("Relative year to entry (k)") ///
                      ytitle("TWFE coefficient") ///
                      title("`=upper("`org'")' `ss' `oo' TWFE event-study") ///
                      legend(off)
                graph export "`out_dir'/membership_`org'_`ss'_twfe_`oo'_eventstudy.png", replace width(2200)
            restore
        }
    }
}

log close
