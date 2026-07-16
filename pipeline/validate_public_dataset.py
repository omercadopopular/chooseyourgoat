"""Fail fast when a source parser or taxonomy change corrupts the release."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'curated'
EXPECTED_PLAYERS={'pele','messi','cristiano','ronaldo','ronaldinho','maradona'}
EXPECTED_NATIONAL_GOALS={'pele':77,'messi':115,'cristiano':143,'ronaldo':62,'ronaldinho':33,'maradona':34}
EXPECTED_NATIONAL_APPS={'pele':92,'messi':196,'cristiano':226,'ronaldo':98,'ronaldinho':97,'maradona':91}

def require(condition,message):
    if not condition: raise AssertionError(message)

def main():
    season=pd.read_csv(DATA/'season_competition.csv')
    goals=pd.read_csv(DATA/'national_team_goal_events.csv')
    national=pd.read_csv(DATA/'national_team_appearances.csv')
    maradona=pd.read_csv(DATA/'national_team_appearances_rsssf.csv')
    modern=pd.read_csv(DATA/'modern_match_appearances.csv')
    titles=pd.read_csv(DATA/'titles.csv')
    historical=pd.read_csv(DATA/'historical_aggregate_assertions.csv')
    taxonomy=pd.read_csv(DATA/'competition_taxonomy.csv')
    web=json.loads((ROOT/'data'/'web_dataset.json').read_text())
    tables=[season,goals,national,modern,titles,historical]
    require(all(not any('official' in str(c).lower() for c in table.columns) for table in tables),'official must not be a data primitive')
    for name,table in [('season',season),('goals',goals),('maradona',maradona),('modern',modern),('titles',titles)]:
        require(set(table.player_id).issubset(EXPECTED_PLAYERS),f'{name}: unknown player')
        require(table.source_url.fillna('').str.startswith('http').all(),f'{name}: missing source URL')
    require(set(season.player_id)==EXPECTED_PLAYERS,'season table must contain all six players')
    require((season[['appearances','goals']]>=0).all().all(),'negative season value')
    require((season.goals<=season.appearances*6).all(),'implausible season-bucket goal ratio')
    actual=goals.groupby('player_id').goals.sum().astype(int).to_dict()
    require(actual==EXPECTED_NATIONAL_GOALS,f'international goal reconciliation failed: {actual}')
    actual_apps=national.groupby('player_id').size().to_dict()
    require(actual_apps==EXPECTED_NATIONAL_APPS,f'international appearance reconciliation failed: {actual_apps}')
    require(national.groupby('player_id').goals.sum().astype(int).to_dict()==EXPECTED_NATIONAL_GOALS,'appearance ledgers do not reconcile to goal events')
    require((pd.to_datetime(national.date_iso)<=pd.Timestamp('2025-12-31')).all(),'national ledger exceeds data cutoff')
    require(len(maradona)==91 and maradona.cap.tolist()==list(range(1,92)),'Maradona ledger must contain caps 1–91')
    require(int(maradona.goals.sum())==34,'Maradona ledger must reconcile to 34 goals')
    require(int(historical.appearances.sum())==1413 and int(historical.goals.sum())==1324,'Pelé RSSSF all-matches components must reconcile to 1,413/1,324')
    require((historical.supports_exact_age_curve==0).all(),'multi-year aggregates cannot support exact-age curves')
    require(web['meta']['dataCutoff']=='2025-12-31' and web['meta']['isFixture'] is False,'invalid web release metadata')
    require({player['id'] for player in web['players']}==EXPECTED_PLAYERS,'web bundle must contain all six players')
    pele=next(player for player in web['players'] if player['id']=='pele')
    require(sum(row['appearances'] for row in pele['observations'])==1413 and sum(row['goals'] for row in pele['observations'])==1324,'Pelé web bridge does not reconcile')
    required_buckets={'national_league','continental_federation_cup','intercontinental_federation_cup','regional_league','all_other_club','national_team_world_cup_finals','national_team_world_cup_qualification','national_team_continental_championship_finals','national_team_continental_championship_qualification','national_team_intercontinental_championship_finals','national_team_continental_nations_league','national_team_olympic','national_team_friendlies','national_team_other'}
    web_buckets={child['id'] for group in web['taxonomy'] for child in group['children']}
    require(web_buckets==required_buckets,'web hierarchy differs from the product taxonomy')
    require(not modern.duplicated(['player_id','game_id']).any(),'duplicate modern appearance')
    require(modern.outcome.isin(['W','D','L']).all(),'invalid match outcome')
    require(not titles.duplicated(['player_id','team','competition_name','edition']).any(),'duplicate title edition')
    require((titles.won==1).all(),'titles table may contain only wins')
    require(not titles.competition_name.str.lower().str.contains('runner-up|third place|bronze').any(),'placement leaked into titles')
    allowed=set(taxonomy.competition_family)
    for name,table in [('season',season),('goals',goals),('maradona',maradona),('modern',modern)]:
        unknown=set(table.competition_family)-allowed
        require(not unknown,f'{name}: taxonomy missing {sorted(unknown)}')
    print(f'Validated {sum(len(t) for t in tables):,} rows across six canonical research tables.')

if __name__=='__main__': main()
