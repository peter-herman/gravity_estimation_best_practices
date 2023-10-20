
/* -------------

CODE EXAMPLES FOR "GRAVITY ESTIMATION: BEST PRACTICES AND USEFUL APPROACHES"

- PETER HERMAN


INTRO
	This file runs demonstrates some of the most common types of gravity specifications. It
	also aims to highlight some of the underlying motivations for why one might want to 
	include many of the different variations discussed below and provide advice on which to 
	generally use.


CONTENTS:
	0. Naive gravity
	1. Multilateral resistance controls
	2. PPML
	5. Country pair fixed effects
	6. Intranational trade
	7. Global openess trends
	8. Country-pair trends
	9. Three-way fixed effect bias correction
	10. Sector-level estimates
	
------------- */




clear all

* Set current directory to folder contianing the 3 data files.
cd "C:\gravity_estimation"


* Load saggregate international trade gravity dataset
use "aggregate_foreign_trade.dta", replace

* Create factor variables of identifiers
encode exporter, gen(exp)
encode importer, gen(imp)



* ---
* 0. Naive Gravity (No multilateral resistance controls)
* ---

* Prep some additional log variables
reghdfe ln_trade ln_gdp_exporter ln_gdp_importer pta eu wto colony contiguity language ln_distance, cluster(i.exp#i.imp)
estimates store naive



* ---
* 2. Multilateral Resistances (Anderson & Van Wincoop, 2003 - "Gravity with Gravitas")
* ---
* Replace importer/exporter GDP's with Importer-year and expoerter-year fixed effects

reghdfe ln_trade pta eu wto colony contiguity language ln_distance, absorb(i.exp#i.year i.imp#i.year) cluster(i.exp#i.imp)
estimates store resistances



* ----
* 3. Poisson Psuedo Maximum Likelihood (Santos Silva & Tenreyro, 2011 - "The Log of Gravity")
* ----

* Replace OLS regression with PPML (NOTE: trade is no longer logged, the continuous dependent variables still are)
ppmlhdfe trade pta eu wto colony contiguity language ln_distance, absorb(i.exp#i.year i.imp#i.year) cluster(i.exp#i.imp)
estimates store ppml



* ---
* 4. Country Pair Fixed Effects (Baier and Bergstrand, 2007 - "Do free trade agreements actually increase members' international trade?" )
* ---

* Add asymetric country-pair fixed effects (drop non-time-varrying bilateral variables)
ppmlhdfe trade pta eu wto, absorb(i.exp#i.year i.imp#i.year i.exp#i.imp) cluster(i.exp#i.imp)
estimates store pair_fe



* ---
* 6. Intranational Trade (Yotov, 2022 - "On the role of domestic trade flows for estimating the gravity model of trade")
* ---
 
* Add domestic trade flows
append using "aggregate_domestic_trade.dta"

* Re-encode identifiers with domestic rows
drop exp imp
encode exporter, gen(exp)
encode importer, gen(imp)


* With indicator for foreign trade, without exporter-importer fixed effects 
ppmlhdfe trade foreign pta eu wto colony contiguity language ln_distance, absorb(i.exp#i.year i.imp#i.year)
estimates store intra_no_pair

* Without foreign indicator but with pair fixed effects
ppmlhdfe trade pta eu wto, absorb(i.exp#i.year i.imp#i.year i.exp#i.imp) cluster(i.exp#i.imp) 
estimates store intra_pair


* ---
* 7. Global openess trends (Bergstrand, Larch, and Yotov, 2015)
* ---

* Add border x year dummies
ppmlhdfe trade pta eu wto c.foreign#i.year, absorb(i.exp#i.year i.imp#i.year i.exp#i.imp)
estimates store border_year


* ---
* 8. Country-pair trends (Bergstrand, Larch, and Yotov, 2015)
* ---

* Add country-pair linear trend
		
ppmlhdfe trade pta eu wto c.foreign#i.year, absorb(i.exp#i.year i.imp#i.year i.exp#i.imp#c.year) cluster(i.exp#i.imp)
estimates store pair_trend

* ppmlhdfe trade pta eu wto c.foreign#i.year, absorb(i.exp#i.year i.imp#i.year i.exp#i.imp##c.year) cluster(i.exp#i.imp)


* ---
* 9. Three-way fixed effect bias correction (Weidner and Zylkin, 2021)
* ---
* Re-estimate model with "d" option, which saves the sum of the fixed effect estimates to use to create predicted values
ppmlhdfe trade pta eu wto, absorb(i.exp#i.year i.imp#i.year i.exp#i.imp) cluster(i.exp#i.imp) d
estimates store pre_bias_correct

* Create conditional mean (lambda) and a matrix of coefficient estimates (beta)
predict lambda
matrix beta = e(b)
ppml_fe_bias trade pta eu wto, i(exp) j(imp) t(year) lambda(lambda) beta(beta)

estimates store post_bias_correct

* If you encounter issues outputting the results, insure that the packages frmttable, gtools, and rowmatutils are installed. 
* See http://fmwww.bc.edu/repec/bocode/p/ppml_fe_bias.ado for additional details.



* ---
* 10: Sectoral Gravity
* ---

use sectoral_trade.dta, clear

* Create factor variables from identifiers
encode exporter, gen(exp)
encode importer, gen(imp)
encode broad_sector, gen(sect)

* Individual sectors
foreach s in "Agriculture" "Manufacturing" "MiningEnergy" "Services" {
	ppmlhdfe trade pta eu wto if broad_sector=="`s'", absorb(i.exp#i.year i.imp#i.year i.exp#i.imp) cluster(i.exp#i.imp) 
	estimates store sect_`s'
} 

* Pooled
ppmlhdfe trade pta eu wto, absorb(i.exp#i.year#i.sect i.imp#i.year#i.sect i.exp#i.imp#i.sect) cluster(i.exp#i.imp)
estimates store sect_pool


* ---
* Store Results table
* ---
esttab naive resistances ppml pair_fe intra_no_pair intra_pair border_year pair_trend pre_bias_correct post_bias_correct sect_pool ///
            using "aggregate_estimates.csv", se ar2 pr2 aic bic mtitles star(* 0.10 ** 0.05 *** 0.01) replace
			
esttab sect_pool sect_Agriculture sect_Manufacturing sect_MiningEnergy sect_Services ///
            using "sector_estimates.csv", se ar2 pr2 aic bic mtitles star(* 0.10 ** 0.05 *** 0.01) replace



