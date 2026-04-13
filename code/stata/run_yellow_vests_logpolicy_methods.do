version 18
clear all
set more off

local input_csv "data/analysis_dataset.csv"
local out_dir "output/econometrics"
local temp_dir "data/temp"
local treat_country "France"
local reps 200
local seed 20260411
local requested_lags 12

capture mkdir "`out_dir'"
capture mkdir "`temp_dir'"
capture mkdir "`out_dir'/logs"

log using "`out_dir'/logs/yellow_vests_logpolicy_methods.log", text replace

* ------------------------------------------------------------
* Load + clean base data (world universe, no OECD prefilter)
* ------------------------------------------------------------
import delimited "`input_csv'", varnames(1) encoding(utf8) clear
keep country date_original
keep if !missing(country) & !missing(date_original)
drop if strpos(country, ";") > 0

gen policy_date = daily(date_original, "DMY")
format policy_date %td
keep if !missing(policy_date)

* OECD marker only for donor-pool slicing
local oecd_countries ///
    `" "Australia" "Austria" "Belgium" "Canada" "Chile" "Colombia" "Costa Rica" "Czechia" "Denmark" "Estonia" "' ///
    `" "Finland" "France" "Germany" "Greece" "Hungary" "Iceland" "Ireland" "Israel" "Italy" "Japan" "' ///
    `" "Latvia" "Lithuania" "Luxembourg" "Mexico" "Netherlands (Kingdom of the)" "New Zealand" "Norway" "Poland" "Portugal" "Republic of Korea" "' ///
    `" "Slovakia" "Slovenia" "Spain" "Sweden" "Switzerland" "Türkiye" "United Kingdom of Great Britain and Northern Ireland" "United States of America" "'
gen byte is_oecd = 0
foreach c of local oecd_countries {
    replace is_oecd = 1 if country == "`c'"
}

tempfile rawclean
save `rawclean', replace

* ------------------------------------------------------------
* Result collector
* ------------------------------------------------------------
tempname rs
postfile `rs' str10 frequency str18 donor_spec str6 method double att se ci95_lb ci95_ub ///
    int chosen_lags int n_countries int n_controls int n_obs int rc str120 covariates ///
    using "`out_dir'/yellow_vests_logpolicy_results_raw.dta", replace

* ------------------------------------------------------------
* Frequency loop: annual + quarterly
* ------------------------------------------------------------
foreach freq in annual quarterly {

    use `rawclean', clear

    if "`freq'" == "annual" {
        gen time = yofd(policy_date)
        collapse (count) policy_count = policy_date, by(country time is_oecd)
        gen byte raw_obs = 1

        egen country_id = group(country), label
        xtset country_id time
        tsfill, full

        drop country
        decode country_id, gen(country)
        bysort country_id: egen is_oecd_fix = max(is_oecd)
        replace is_oecd = is_oecd_fix if missing(is_oecd)
        drop is_oecd_fix

        replace raw_obs = 0 if missing(raw_obs)
        replace policy_count = 0 if missing(policy_count)
        gen ln_policy_count = ln(1 + policy_count)

        keep if inrange(time, 2002, 2022)
        gen byte core_window = inrange(time, 2014, 2022) & time != 2018

        by country_id: egen pre_raw = total(raw_obs * inrange(time, 2014, 2017) * core_window)
        by country_id: egen post_raw = total(raw_obs * inrange(time, 2019, 2022) * core_window)
        keep if pre_raw > 0 & post_raw > 0

        by country_id: egen n_obs_core = total(core_window)
        keep if n_obs_core == 8

        gen byte tr_base = (country == "`treat_country'" & inrange(time, 2019, 2022))
        format time %ty
    }

    if "`freq'" == "quarterly" {
        gen time = qofd(policy_date)
        collapse (count) policy_count = policy_date, by(country time is_oecd)
        gen byte raw_obs = 1

        egen country_id = group(country), label
        xtset country_id time
        tsfill, full

        drop country
        decode country_id, gen(country)
        bysort country_id: egen is_oecd_fix = max(is_oecd)
        replace is_oecd = is_oecd_fix if missing(is_oecd)
        drop is_oecd_fix

        replace raw_obs = 0 if missing(raw_obs)
        replace policy_count = 0 if missing(policy_count)
        gen ln_policy_count = ln(1 + policy_count)

        keep if inrange(time, yq(2012,4), yq(2021,3))
        gen byte core_window = inrange(time, yq(2015,4), yq(2021,3))

        by country_id: egen pre_raw = total(raw_obs * inrange(time, yq(2015,4), yq(2018,3)) * core_window)
        by country_id: egen post_raw = total(raw_obs * inrange(time, yq(2018,4), yq(2021,3)) * core_window)
        keep if pre_raw > 0 & post_raw > 0

        by country_id: egen n_obs_core = total(core_window)
        keep if n_obs_core == 24

        gen byte tr_base = (country == "`treat_country'" & inrange(time, yq(2018,4), yq(2021,3)))
        format time %tq
    }

    foreach donor in oecd oecd_exclshock world world_exclshock {

        preserve

        if "`donor'" == "oecd" | "`donor'" == "oecd_exclshock" {
            keep if country == "`treat_country'" | is_oecd == 1
        }

        if "`donor'" == "oecd_exclshock" | "`donor'" == "world_exclshock" {
            drop if inlist(country, "Spain", "Portugal", "Belgium", "Netherlands (Kingdom of the)", "United Kingdom of Great Britain and Northern Ireland")
        }

        by country_id: egen nobs2 = total(core_window)
        if "`freq'" == "annual" keep if nobs2 == 8
        if "`freq'" == "quarterly" keep if nobs2 == 24

        egen __tag_c = tag(country)
        quietly count if __tag_c == 1 & country == "`treat_country'"
        local n_treat = r(N)
        quietly count if __tag_c == 1 & country != "`treat_country'"
        local n_ctrl = r(N)
        drop __tag_c

        if (`n_treat' == 0 | `n_ctrl' < 2) {
            post `rs' ("`freq'") ("`donor'") ("skip") (.) (.) (.) (.) (.) (.) (`n_treat'+`n_ctrl') (`n_ctrl') (.) (499) ("insufficient donors or missing treated")
            restore
            continue
        }

        export delimited country time ln_policy_count policy_count raw_obs tr_base if core_window == 1 using "`temp_dir'/yellow_vests_logpolicy_`freq'_panel_`donor'.csv", replace

        sort country_id time
        forvalues k = 1/`requested_lags' {
            by country_id (time): gen lag`k'_lncount = ln_policy_count[_n-`k']
        }

        local chosen_lags = 0
        local covars ""
        forvalues L = `requested_lags'(-1)1 {
            local ok = 1
            forvalues k = 1/`L' {
                quietly count if core_window == 1 & missing(lag`k'_lncount)
                if r(N) > 0 local ok = 0
            }
            if `ok' == 1 {
                local chosen_lags `L'
                local covars ""
                forvalues k = 1/`L' {
                    local covars `covars' lag`k'_lncount
                }
                continue, break
            }
        }

        foreach m in sdid sc {
            gen byte tr = tr_base
            local this_cov ""
            if "`m'" == "sdid" local this_cov "`covars'"

            local gfile "`out_dir'/yellow_vests_logpolicy_`freq'_`m'_`donor'_trends.png"

            capture noisily {
                if "`m'" == "sdid" {
                    sdid ln_policy_count country_id time tr if core_window == 1, vce(placebo) reps(`reps') seed(`seed') ///
                        covariates(`this_cov', projected) graph ///
                        g2_opt(xtitle("`freq' time") ytitle("ln(1+policy_count)") ///
                        title("France vs synthetic controls: log policy count `=upper("`freq'")' `=upper("`m'")' `donor'"))
                }
                else {
                    sdid ln_policy_count country_id time tr if core_window == 1, vce(placebo) reps(`reps') seed(`seed') ///
                        method(sc) graph ///
                        g2_opt(xtitle("`freq' time") ytitle("ln(1+policy_count)") ///
                        title("France vs synthetic controls: log policy count `=upper("`freq'")' SC `donor'"))
                }

                graph export "`gfile'", replace width(2200)

                matrix b = e(b)
                matrix V = e(V)
                scalar att = b[1,1]
                scalar se_att = sqrt(V[1,1])
                scalar lb95 = att - invnormal(0.975)*se_att
                scalar ub95 = att + invnormal(0.975)*se_att

                quietly count if core_window == 1
                local nobs = r(N)
                egen __tag_country = tag(country_id)
                quietly count if __tag_country == 1
                local nc = r(N)
                drop __tag_country

                post `rs' ("`freq'") ("`donor'") ("`m'") (att) (se_att) (lb95) (ub95) ///
                    (`chosen_lags') (`nc') (`n_ctrl') (`nobs') (0) ("`this_cov'")
            }

            if _rc {
                local rcx = _rc
                quietly count if core_window == 1
                local nobs = r(N)
                egen __tag_country = tag(country_id)
                quietly count if __tag_country == 1
                local nc = r(N)
                drop __tag_country
                post `rs' ("`freq'") ("`donor'") ("`m'") (.) (.) (.) (.) ///
                    (`chosen_lags') (`nc') (`n_ctrl') (`nobs') (`rcx') ("`this_cov'")
            }

            drop tr
        }

        restore
    }
}

postclose `rs'

use "`out_dir'/yellow_vests_logpolicy_results_raw.dta", clear
order frequency donor_spec method att se ci95_lb ci95_ub chosen_lags n_countries n_controls n_obs rc covariates
export delimited using "`out_dir'/yellow_vests_logpolicy_results.csv", replace
erase "`out_dir'/yellow_vests_logpolicy_results_raw.dta"

log close
