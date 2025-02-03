__Author__ = "Peter Herman"
__Project__ = "gravity best practices"
__Created__ = "October 13, 2023"
__Description__ = '''Create Data for "Gravity Estimation: Best Practices and Useful Approaches"'''




import pandas as pd
import numpy as np

# Number of countries to retain (sorted by total imports+exports)
num_countries = 150

# Years to retain
year_list = [2000, 2003, 2006, 2009, 2012, 2015, 2018]

# Location of source data files
working_directory = "C:\gravity\\"
itpd_raw = pd.read_csv("{}ITPD_E_R02.csv".format(working_directory))
dgd_raw_a = pd.read_csv("{}release_2.1_2000_2004.csv".format(working_directory))
dgd_raw_b = pd.read_csv("{}release_2.1_2005_2009.csv".format(working_directory))
dgd_raw_c = pd.read_csv("{}release_2.1_2010_2014.csv".format(working_directory))
dgd_raw_d = pd.read_csv("{}release_2.1_2015_2019.csv".format(working_directory))

# Sepcify save folder for data
save_loc = "C:\gravity\\"



# ----
# Trade Data
# ----

# Load ITPD-E trade data
itpd = itpd_raw.loc[itpd_raw['year'].isin(year_list),:]
# Aggregate across all sectors
itpd_agg = itpd.groupby(['exporter_iso3', 'importer_iso3', 'year']).agg({'trade':'sum'}).reset_index()
itpd_agg['broad_sector'] = 'Total'
# Aggregate across broad sectors
itpd_sect = itpd.groupby(['exporter_iso3', 'importer_iso3', 'year', 'broad_sector']).agg({'trade':'sum'}).reset_index()

# Combine both aggregations (row stack)
itpd_comb = pd.concat([itpd_agg,itpd_sect], axis = 0)

# Create logged trade values
itpd_comb['ln_trade'] = np.log(itpd_comb['trade'])
itpd_comb.loc[itpd_comb['trade']==0,'ln_trade'] = np.nan


# Idetify top traders
all_imports = itpd_agg.groupby('importer_iso3').agg({'trade':'sum'}).reset_index()
all_exports = itpd_agg.groupby('exporter_iso3').agg({'trade':'sum'}).reset_index()
all_trade = all_exports.merge(all_imports, right_on = 'importer_iso3', left_on = 'exporter_iso3',
                              how = 'outer', validate='1:1')
all_trade['total'] = all_trade['trade_x'] = all_trade['trade_y']
all_trade.sort_values(['total'], ascending=False, inplace = True)
top_traders = all_trade['exporter_iso3'].head(num_countries).to_list()

#  ----
#  Gravity Covariates
#  ----

# Load data and cobine (row stack)
dgd = pd.concat([dgd_raw_a, dgd_raw_b, dgd_raw_c, dgd_raw_d], axis = 0)
dgd = dgd[['iso3_o','iso3_d', 'year', 'agree_pta', 'member_eu_joint', 'member_wto_joint', 'distance', 'colony_ever',
           'contiguity', 'common_language', 'gdp_pwt_cur_d', 'gdp_pwt_cur_o']].copy()
# Rename some variables
dgd.rename(columns = {'iso3_o':'exporter_iso3','iso3_d':'importer_iso3', 'gdp_pwt_cur_d':'gdp_importer', 'gdp_pwt_cur_o':'gdp_exporter'},inplace = True)

# Produce logged versions of certain variables
for var in ['distance', 'gdp_exporter', 'gdp_importer']:
    dgd["ln_{}".format(var)] = np.log(dgd[var])
    dgd.drop(var, axis = 1, inplace = True)

# Create "foreign" indicator
dgd['foreign'] = 0
dgd.loc[(dgd['importer_iso3']!=dgd['exporter_iso3']), 'foreign'] = 1

# Eliminate some erroneously duplicated rows in current DGD version
dups = dgd.loc[dgd.duplicated(subset = ['exporter_iso3', 'importer_iso3', 'year'], keep=False),:]

# Drop European Union rows (no trade data)
dgd = dgd.loc[dgd['exporter_iso3']!='EUN',:]
dgd = dgd.loc[dgd['importer_iso3']!='EUN',:]



# ---
# Combine and prep for output
# ---
grav = itpd_comb.merge(dgd, how = 'left', on = ['exporter_iso3', 'importer_iso3', 'year'], validate = 'm:1')
# Retain only desired countries
grav = grav.loc[grav['exporter_iso3'].isin(top_traders) & grav['importer_iso3'].isin(top_traders),:]
grav.sort_values(['exporter_iso3', 'importer_iso3', 'year'], inplace = True)

# Relable some variables
grav.rename(columns = {'exporter_iso3':'exporter', 'importer_iso3':'importer', 'agree_pta':'pta',
                       'member_eu_joint':'eu', 'member_wto_joint':'wto', 'colony_ever':'colony',
                       'common_language':'language'}, inplace = True)

# Grab total aggregate trade rows
grav_total = grav.loc[grav['broad_sector']=='Total',:].copy()

# Seperate into foreign- and domestic-only dataframes
grav_frgn = grav_total.loc[(grav_total['exporter']!=grav_total['importer']),:]
grav_dom = grav_total.loc[(grav_total['exporter']==grav_total['importer']),:]

# Grab Broad sector-level rows
grav_sect = grav.loc[grav['broad_sector']!='Total',:].copy()
# Relable sector for Stata "no space" requirement
grav_sect['broad_sector'].replace({"Mining and Energy":'MiningEnergy'}, inplace = True)

# Define variable labels for .dta files
labels = {'exporter':'Exporter label',
          'importer':'Importer label',
          'year':"Year",
          'trade':"Bilateral trade value (current $M)",
          'broad_sector':"Sector label",
          'ln_trade':"Log of trade value",
          'pta':"Preferential trade agreement indicator",
          'eu':'Indicator for both being European Union members',
          'wto':'Indicator for both being WTO members',
          'colony':'Indicator for colonial ties',
          'contiguity':'Indicator for shared land border',
          'language':'Indicator for a shared common language',
          'ln_distance':'Log population weighted geographic distance',
          'ln_gdp_exporter':"Log GDP of exporter",
          'ln_gdp_importer':"Log GDP of importer",
          'foreign':'Indicator for international trade',
          'pair_id':'Identifier for country pair'}


grav_frgn.to_stata("{}//aggregate_foreign_trade.dta".format(save_loc), write_index=False, variable_labels=labels)
grav_dom.to_stata("{}//aggregate_domestic_trade.dta".format(save_loc), write_index=False, variable_labels=labels)
grav_sect.to_stata("{}//sectoral_trade.dta".format(save_loc), write_index=False, variable_labels=labels)

