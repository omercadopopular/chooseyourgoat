"""Build the public six-player research dataset.

Sources:
  * Wikipedia career-statistics and international-goal tables (CC BY-SA)
  * RSSSF chronological international records (copyrighted reference source)
  * dcaribou/transfermarkt-datasets CC0 snapshot (modern match-level supplement)

The output never uses an `official` flag. Records are classified by team context,
geographic scope, competition family, format, seniority and source treatment.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("CHOOSEYOURGOAT_RAW_DIR", ROOT / "data" / "raw"))
OUT = ROOT / "data" / "curated"
OUT.mkdir(parents=True, exist_ok=True)
DATA_CUTOFF = date(2025, 12, 31)

PLAYERS = {
    "pele": {"name": "Pelé", "birth": "1940-10-23", "wiki": "pele", "club_table": 5, "national_table": 7},
    "messi": {"name": "Lionel Messi", "birth": "1987-06-24", "wiki": "messi", "club_table": 3, "national_table": 4},
    "cristiano": {"name": "Cristiano Ronaldo", "birth": "1985-02-05", "wiki": "cristiano", "club_table": 17, "national_table": 18},
    "ronaldo": {"name": "Ronaldo Nazário", "birth": "1976-09-18", "wiki": "ronaldo", "club_table": 2, "national_table": 3},
    "ronaldinho": {"name": "Ronaldinho", "birth": "1980-03-21", "wiki": "ronaldinho", "club_table": 3, "national_table": 4},
    "maradona": {"name": "Diego Maradona", "birth": "1960-10-30", "wiki": "maradona", "club_table": 3, "national_table": 4},
}

RSSSF_NATIONAL_LEDGERS = {
    "pele": ("pele_rsssf_intl.html", 92, 77, "Brazil"),
    "messi": ("messi_rsssf_intl.html", 196, 115, "Argentina"),
    "cristiano": ("cristiano_rsssf_intl.html", 226, 143, "Portugal"),
    "ronaldo": ("ronaldo_rsssf_intl.html", 98, 62, "Brazil"),
    "ronaldinho": ("ronaldinho_rsssf_intl.html", 97, 33, "Brazil"),
    "maradona": ("maradona_intl.html", 91, 34, "Argentina"),
}

# Ten RSSSF rows lost their venue/opponent delimiter in the rendered fixed-width
# text. Values below are direct transcriptions of those rows, keyed by cap.
LEDGER_LOCATION_FIXES = {
    ("messi",56):("East Rutherford","United States","1-1","Friendly"),
    ("messi",85):("Buenos Aires","Trinidad/Tobago","3-0","Friendly"),
    ("messi",126):("Nizhny Novgorod","Croatia","0-3","World Cup"),
    ("messi",127):("Sankt Peterburg","Nigeria","2-1","World Cup"),
    ("messi",174):("Stgo. d. Estero","Curacao","7-0","Friendly"),
    ("ronaldo",46):("Ciudad del Este","Venezuela","7-0","Copa America"),
    ("ronaldo",47):("Ciudad del Este","Mexico","2-1","Copa America"),
    ("ronaldo",48):("Ciudad del Este","Chile","1-0","Copa America"),
    ("ronaldo",49):("Ciudad del Este","Argentina","2-1","Copa America"),
    ("ronaldo",50):("Ciudad del Este","Mexico","2-0","Copa America"),
}

SOURCE_URLS = {
    "pele": "https://en.wikipedia.org/wiki/Pel%C3%A9",
    "messi": "https://en.wikipedia.org/wiki/Lionel_Messi",
    "cristiano": "https://en.wikipedia.org/wiki/List_of_career_achievements_by_Cristiano_Ronaldo",
    "ronaldo": "https://en.wikipedia.org/wiki/Ronaldo_(Brazilian_footballer)",
    "ronaldinho": "https://en.wikipedia.org/wiki/Ronaldinho",
    "maradona": "https://en.wikipedia.org/wiki/Diego_Maradona",
}

INTERNATIONAL_GOAL_URLS = {
    "pele": "https://en.wikipedia.org/wiki/List_of_international_goals_scored_by_Pel%C3%A9",
    "messi": "https://en.wikipedia.org/wiki/List_of_international_goals_scored_by_Lionel_Messi",
    "cristiano": "https://en.wikipedia.org/wiki/List_of_international_goals_scored_by_Cristiano_Ronaldo",
    "ronaldo": SOURCE_URLS["ronaldo"],
    "ronaldinho": SOURCE_URLS["ronaldinho"],
}

def clean(value):
    value = re.sub(r"\[[^]]*]", "", str(value)).strip()
    return value.replace("−", "-").replace("–", "-")

def number(value):
    value = clean(value)
    if value in {"-", "—", "–", "nan", ""}: return 0
    values = re.findall(r"\d+", value.replace(",", ""))
    if not values: return 0
    # A few historical source cells are additive, e.g. 14+15. Retain their
    # source text in the output and compute the explicitly stated sum.
    return sum(map(int, values)) if "+" in value else int(values[0])

def season_end_year(value):
    text=clean(value)
    years=re.findall(r"(?:19|20)\d{2}",text)
    if not years: return None
    start=int(years[0])
    short=re.search(r"(?:19|20)\d{2}\s*[-/]\s*(\d{2})(?!\d)",text)
    if short:
        end=(start//100)*100+int(short.group(1))
        if end<start: end+=100
        return end
    return int(years[-1])

def flatten_columns(df):
    if not isinstance(df.columns, pd.MultiIndex):
        df.columns = [clean(c) for c in df.columns]
        return df
    cols=[]
    for col in df.columns:
        parts=[]
        for p in col:
            p=clean(p)
            if p and not p.startswith("Unnamed") and p not in parts: parts.append(p)
        cols.append("|".join(parts))
    df.columns=cols
    return df

def bucket_family(bucket, division=""):
    raw=bucket.lower()
    b=f"{bucket} {division}".lower()
    if "intercontinental" in b or "club world" in b:
        return "intercontinental_federation_cup"
    if any(name in b for name in ["campeonato paulista", "campeonato carioca", "campeonato mineiro", "campeonato gaúcho", "regional", "state league", "rio-são paulo"]):
        return "regional_league"
    if "libertadores" in b or "continental" in b or "champions" in b or "uefa" in b or b=="europe":
        return "continental_federation_cup"
    if "cup" in b or "copa" in b or "coppa" in b or "taça" in b or "pokal" in b or "domestic" in b:
        return "domestic_cup"
    if raw=="league" or any(name in b for name in ["brasileiro", "liga", "serie a", "premier league", "eredivisie", "bundesliga", "ligue 1", "mls", "division"]):
        return "national_league"
    if "other" in b or "postseason" in b:
        return "all_other_club"
    return "unclassified_club"

def parse_club_stats(player_id, cfg):
    tables=pd.read_html(str(RAW/f"{cfg['wiki']}.html"), flavor='lxml')
    indices=[cfg["club_table"]]
    if player_id=="pele": indices.append(6)
    result=[]
    for ti in indices:
        raw=tables[ti].copy()
        if player_id=="pele" and ti==5:
            # The rendered table has a header-only spacer at column 10. Pandas
            # consequently shifts the final six data cells one column left.
            # Use the actual 16-cell row layout documented in the page.
            df=raw.iloc[:,:16].copy()
            df.columns=["Club","Season","Campeonato Paulista|Apps","Campeonato Paulista|Goals","Rio-São Paulo|Apps","Rio-São Paulo|Goals","Campeonato Brasileiro Série A|Apps","Campeonato Brasileiro Série A|Goals","Domestic competitions Sub-total|Apps","Domestic competitions Sub-total|Goals","Copa Libertadores|Apps","Copa Libertadores|Goals","Intercontinental Cup|Apps","Intercontinental Cup|Goals","Total|Apps","Total|Goals"]
        else:
            df=flatten_columns(raw)
        club_col=next(c for c in df if c.split("|")[0]=="Club")
        season_col=next(c for c in df if c.split("|")[0]=="Season")
        df[club_col]=df[club_col].replace("nan",pd.NA).ffill()
        for _,r in df.iterrows():
            club=clean(r[club_col]); season=clean(r[season_col])
            if not season or season.lower()=="total" or "total" in club.lower(): continue
            if season_end_year(season) and season_end_year(season)>DATA_CUTOFF.year: continue
            division=""
            for c in df.columns:
                if c.endswith("Division"): division=clean(r[c])
            if player_id=="pele" and ti==5 and season=="1956":
                apps_text=clean(r["Domestic competitions Sub-total|Apps"])
                goals_text=clean(r["Domestic competitions Sub-total|Goals"])
                result.append({"player_id":player_id,"player_name":cfg["name"],"team_context":"club","team":club,"season":season,"source_bucket":"Unallocated domestic competition","competition_name":"Unallocated domestic competition","competition_family":"all_other_club","seniority":"senior","appearances":number(apps_text),"goals":number(goals_text),"appearances_source_text":apps_text,"goals_source_text":goals_text,"source_id":f"wikipedia_{player_id}_career_stats","source_url":SOURCE_URLS[player_id],"source_granularity":"season_bucket"})
            # Every Apps/Goals pair other than Total becomes a source bucket.
            for c in df.columns:
                if not c.endswith("Apps") or c.startswith("Total") or "sub-total" in c.lower(): continue
                base=c.rsplit("|",1)[0] if "|" in c else c.replace("Apps","").strip()
                goal_candidates=[g for g in df.columns if g.endswith("Goals") and (g.rsplit("|",1)[0] if "|" in g else g.replace("Goals","").strip())==base]
                if not goal_candidates: continue
                apps_text=clean(r[c]); goals_text=clean(r[goal_candidates[0]])
                apps=number(apps_text); goals=number(goals_text)
                if apps==0 and goals==0: continue
                seniority="reserve" if re.search(r"\b(B|C|reserves?|youth)\b",club,re.I) else "senior"
                result.append({"player_id":player_id,"player_name":cfg["name"],"team_context":"club","team":club,"season":season,"source_bucket":base,"competition_name":division if base.lower()=="league" and division else base,"competition_family":bucket_family(base,division),"seniority":seniority,"appearances":apps,"goals":goals,"appearances_source_text":apps_text,"goals_source_text":goals_text,"source_id":f"wikipedia_{player_id}_career_stats","source_url":SOURCE_URLS[player_id],"source_granularity":"season_bucket"})
    return result

def parse_national_year_stats(player_id,cfg):
    df=flatten_columns(pd.read_html(str(RAW/f"{cfg['wiki']}.html"), flavor='lxml')[cfg["national_table"]].copy())
    team_col=next(c for c in df if c.split("|")[0] in {"Team","Season"})
    year_col=next(c for c in df if c.split("|")[0] in {"Year","Tournament"})
    df[team_col]=df[team_col].replace("nan",pd.NA).ffill()
    out=[]
    for _,r in df.iterrows():
        team=clean(r[team_col]); year=clean(r[year_col])
        if year.lower()=="total" or not re.search(r"\d{4}",year): continue
        if season_end_year(year)>DATA_CUTOFF.year: continue
        if any(c.startswith("Competitive") for c in df):
            contexts=[("Competitive","national_team_competitive_unallocated"),("Friendly","national_team_friendlies")]
        elif any(c.startswith("Tournament") for c in df):
            contexts=[("Tournament","national_team_tournament_finals_unallocated"),("Qualifiers","national_team_qualification_unallocated"),("Friendlies","national_team_friendlies")]
        else:
            contexts=[("","national_team_all_matches_unallocated")]
        for context,family in contexts:
            ac=next((c for c in df if (c.startswith(context) if context else c=="Apps") and c.endswith("Apps")),None)
            gc=next((c for c in df if (c.startswith(context) if context else c=="Goals") and c.endswith("Goals")),None)
            if not ac or not gc: continue
            apps_text,goals_text=clean(r[ac]),clean(r[gc])
            apps,goals=number(apps_text),number(goals_text)
            if apps==0 and goals==0: continue
            seniority="senior" if not re.search(r"U\d+|Olympic",team,re.I) else "youth_or_olympic"
            label=context or "All matches"
            out.append({"player_id":player_id,"player_name":cfg["name"],"team_context":"national_team","team":team,"season":year,"source_bucket":label.lower(),"competition_name":label,"competition_family":family,"seniority":seniority,"appearances":apps,"goals":goals,"appearances_source_text":apps_text,"goals_source_text":goals_text,"source_id":f"wikipedia_{player_id}_career_stats","source_url":SOURCE_URLS[player_id],"source_granularity":"calendar_year_bucket"})
    return out

def classify_national_competition(name):
    n=clean(name).lower()
    if "world cup qual" in n: return "national_team_world_cup_qualification"
    if "world cup" in n: return "national_team_world_cup_finals"
    if any(x in n for x in ["confederations cup","confederarions cup","finalissima","artemio franchi","copa de oro","panamerican championship","conmebol-uefa"]): return "national_team_intercontinental_championship_finals"
    if any(x in n for x in ["copa américa","copa america","uefa euro","european championship","european champ","european ch.","gold cup","asian cup","africa cup of nations","ofc nations"]):
        return "national_team_continental_championship_finals" if "qual" not in n else "national_team_continental_championship_qualification"
    if "nations league" in n: return "national_team_continental_nations_league"
    if any(x in n for x in ["olympic","pre-olympic"]): return "national_team_olympic"
    if n in {"friendly","nan",""} or any(x in n for x in ["friendly","anniversary"]): return "national_team_friendlies"
    return "national_team_other"

def parse_rsssf_national_ledger(player_id):
    """Parse RSSSF's chronological cap ledger into appearances and goal events."""
    from lxml import html
    filename,expected_caps,expected_goals,team=RSSSF_NATIONAL_LEDGERS[player_id]
    page=html.parse(RAW/filename)
    blocks=page.xpath('//pre')
    date_pattern=r"(\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{2})"
    candidates=[]
    for block in blocks:
        rows=[]
        for line in block.text_content().splitlines():
            match=re.match(r"^\s*(\d+)\s+(.*?)\s*"+date_pattern+r"\s{1,}(.+?)\s*$",line)
            if match and int(match.group(1))<=expected_caps: rows.append((line,match))
        candidates.append(rows)
    source_rows=max(candidates,key=len)
    appearances=[]; events=[]; last_cumulative=0; event_number=0
    for line,match in source_rows:
        cap=int(match.group(1)); prefix=match.group(2).strip()
        values=[int(value) for value in re.findall(r"\d+",prefix)]
        if len(values)>=2:
            match_goals,cumulative=values[-2],values[-1]
        elif len(values)==1:
            cumulative=values[0]; match_goals=max(0,cumulative-last_cumulative)
        else:
            cumulative=last_cumulative; match_goals=0
        last_cumulative=cumulative
        raw_date=re.sub(r"\s+","",match.group(3)).replace('/','-')
        day,month,yy=map(int,raw_date.split('-'))
        year=1900+yy if yy>=40 else 2000+yy
        iso=f"{year:04d}-{month:02d}-{day:02d}"
        if (player_id,cap) in LEDGER_LOCATION_FIXES:
            venue,opponent,result,competition=LEDGER_LOCATION_FIXES[(player_id,cap)]
        else:
            parts=[clean(part) for part in re.split(r"\t+|\s{2,}",match.group(4).strip()) if clean(part)]
            result_index=next((index for index,value in enumerate(parts) if re.match(r"^\d+\s*[-x]\s*\d+",value)),None)
            if result_index is None or result_index<2: continue
            venue=" ".join(parts[:result_index-1]); opponent=parts[result_index-1]
            result=parts[result_index]; competition=" ".join(parts[result_index+1:]) or "Friendly"
        family=classify_national_competition(competition)
        scores=[int(value) for value in re.findall(r"\d+",result)[:2]]
        outcome='W' if scores[0]>scores[1] else ('D' if scores[0]==scores[1] else 'L')
        slug={'pele':'pele-intlg','messi':'messi-intlg','cristiano':'cronaldo-intlg','ronaldo':'ronaldo-intlg','ronaldinho':'ronaldinho-intlg','maradona':'maradona-intl'}[player_id]
        base={"player_id":player_id,"player_name":PLAYERS[player_id]["name"],"team":team,"cap":cap,"date":raw_date,"date_iso":iso,"venue":venue,"opponent":opponent,"result":result,"outcome":outcome,"competition_name":competition,"competition_family":family,"source_id":f"rsssf_{player_id}_international_appearances","source_url":f"https://www.rsssf.org/miscellaneous/{slug}.html"}
        appearances.append({**base,"goals":match_goals,"cumulative_goals":cumulative,"source_granularity":"appearance"})
        for goal_in_match in range(1,match_goals+1):
            event_number+=1
            events.append({**base,"event_number":event_number,"goal_in_match":goal_in_match,"goals":1,"source_granularity":"goal_event_derived_from_appearance"})
    if len(appearances)!=expected_caps or sum(row['goals'] for row in appearances)!=expected_goals:
        raise ValueError(f"{player_id} RSSSF reconciliation failed: {len(appearances)} caps, {sum(row['goals'] for row in appearances)} goals")
    return appearances,events

def parse_wiki_international_goals(player_id,path,table_index):
    df=pd.read_html(str(path), flavor='lxml')[table_index].copy()
    out=[]
    for event_number,(_,r) in enumerate(df.iterrows(),1):
        comp=clean(r.get("Competition","")); dt=clean(r.get("Date",""));
        parsed=pd.to_datetime(dt,errors="coerce")
        out.append({"player_id":player_id,"player_name":PLAYERS[player_id]["name"],"event_number":event_number,"date":dt,"date_iso":parsed.date().isoformat() if not pd.isna(parsed) else "","opponent":clean(r.get("Opponent","")),"score":clean(r.get("Score","")),"result":clean(r.get("Result","")),"competition_name":comp or "Friendly","competition_family":classify_national_competition(comp),"goals":1,"source_id":f"wikipedia_{player_id}_international_goals","source_url":INTERNATIONAL_GOAL_URLS[player_id],"source_granularity":"goal_event"})
    return out

def parse_maradona_rsssf():
    from lxml import html
    block=html.parse(RAW/'maradona_intl.html').xpath('//pre')[0].text_content()
    appearances=[]; goals=[]; event_number=0
    pat=re.compile(r"^\s*(\d+)\s+(.*?)\s*(\d{1,2}-\s*\d{1,2}-\d{2})\s{2,}(.+)$")
    for line in block.splitlines():
        m=pat.match(line)
        if not m or int(m.group(1))>91: continue
        cap=int(m.group(1)); prefix=[int(x) for x in re.findall(r"\d+",m.group(2))]
        match_goals=prefix[0] if len(prefix)>1 else 0
        cumulative=prefix[-1] if prefix else 0
        rest=re.split(r"\s{2,}",m.group(4).strip())
        if len(rest)<3: continue
        venue,opponent,result=map(clean,rest[:3]); comp=clean(rest[3]) if len(rest)>3 else "Friendly"
        dt=re.sub(r"\s+","",m.group(3))
        day,month,yy=map(int,dt.split('-')); year=1900+yy
        iso=f"{year:04d}-{month:02d}-{day:02d}"
        base={"player_id":"maradona","player_name":"Diego Maradona","cap":cap,"date":dt,"date_iso":iso,"venue":venue,"opponent":opponent,"result":result,"competition_name":comp,"competition_family":classify_national_competition(comp),"source_id":"rsssf_maradona_international_appearances","source_url":"https://www.rsssf.org/miscellaneous/maradona-intl.html"}
        appearances.append({**base,"goals":match_goals,"cumulative_goals":cumulative,"source_granularity":"appearance"})
        for goal_in_match in range(1,match_goals+1):
            event_number+=1
            goals.append({**base,"event_number":event_number,"goal_in_match":goal_in_match,"goals":1,"source_granularity":"goal_event_derived_from_appearance"})
    return appearances,goals

def modern_transfermarkt():
    pids={8198:"cristiano",28003:"messi"}
    apps=pd.read_csv(RAW/'appearances.csv.gz')
    games=pd.read_csv(RAW/'games.csv.gz',low_memory=False)
    comps=pd.read_csv(RAW/'competitions.csv.gz')
    x=apps[apps.player_id.isin(pids)].merge(games,on='game_id',suffixes=('','_game')).merge(comps,on='competition_id',suffixes=('','_competition'))
    x=x[pd.to_datetime(x.date).dt.date<=DATA_CUTOFF]
    def family(r):
        st=str(r.sub_type).lower(); typ=str(r.type).lower(); name=str(r['name']).lower()
        if st=='world_cup': return 'national_team_world_cup_finals'
        if st in {'copa_america','uefa_euro','afc_asian_cup','africa_cup_of_nations'}: return 'national_team_continental_championship_finals'
        if typ=='domestic_league': return 'national_league'
        if typ=='domestic_cup': return 'domestic_cup'
        if 'champions_league' in st or 'europa_league' in st or typ=='international_cup': return 'continental_federation_cup'
        if 'super_cup' in st: return 'domestic_super_cup'
        return 'all_other_club'
    x['player_id']=x.player_id.map(pids); x['competition_family']=x.apply(family,axis=1)
    x['is_home']=x.player_club_id==x.home_club_id
    x['team_goals']=x.apply(lambda r:r.home_club_goals if r.is_home else r.away_club_goals,axis=1)
    x['opponent_goals']=x.apply(lambda r:r.away_club_goals if r.is_home else r.home_club_goals,axis=1)
    x['outcome']=x.apply(lambda r:'W' if r.team_goals>r.opponent_goals else ('D' if r.team_goals==r.opponent_goals else 'L'),axis=1)
    cols=['player_id','player_name','game_id','date','competition_id','name','competition_family','season','round','goals','minutes_played','team_goals','opponent_goals','outcome','home_club_name','away_club_name']
    y=x[cols].rename(columns={'name':'competition_name'})
    y['source_id']='dcaribou_transfermarkt_dataset'; y['source_url']='https://github.com/dcaribou/transfermarkt-datasets'; y['source_granularity']='appearance'
    return y

# Manually curated championship editions from public honours lists. Runner-up and
# individual awards are deliberately excluded. Youth titles remain tagged.
TITLES = {
"pele": [("Santos","Campeonato Paulista",y) for y in [1958,1960,1961,1962,1964,1965,1967,1968,1969,1973]]+[("Santos","Torneio Rio-São Paulo",y) for y in [1959,1963,1964,1966]]+[("Santos","Campeonato Brasileiro",y) for y in [1961,1962,1963,1964,1965,1968]]+[("Santos","Copa Libertadores",y) for y in [1962,1963]]+[("Santos","Intercontinental Cup",y) for y in [1962,1963]]+[("Santos","Intercontinental Supercup",1968),("New York Cosmos","NASL Championship",1977)]+[("Brazil","FIFA World Cup",y) for y in [1958,1962,1970]],
"messi": [("Barcelona","La Liga",y) for y in ["2004-05","2005-06","2008-09","2009-10","2010-11","2012-13","2014-15","2015-16","2017-18","2018-19"]]+[("Barcelona","Copa del Rey",y) for y in ["2008-09","2011-12","2014-15","2015-16","2016-17","2017-18","2020-21"]]+[("Barcelona","Supercopa de España",y) for y in [2006,2009,2010,2011,2013,2016,2018]]+[("Barcelona","UEFA Champions League",y) for y in ["2005-06","2008-09","2010-11","2014-15"]]+[("Barcelona","UEFA Super Cup",y) for y in [2009,2011,2015]]+[("Barcelona","FIFA Club World Cup",y) for y in [2009,2011,2015]]+[("Paris Saint-Germain","Ligue 1",y) for y in ["2021-22","2022-23"]]+[("Paris Saint-Germain","Trophée des Champions",2022),("Inter Miami","MLS Cup",2025),("Inter Miami","Supporters' Shield",2024),("Inter Miami","Leagues Cup",2023),("Argentina U20","FIFA World Youth Championship",2005),("Argentina U23","Olympic Games",2008),("Argentina","FIFA World Cup",2022),("Argentina","Copa América",2021),("Argentina","Copa América",2024),("Argentina","Finalissima",2022)],
"ronaldo": [("Cruzeiro","Copa do Brasil",1993),("Cruzeiro","Campeonato Mineiro",1994),("PSV","KNVB Cup","1995-96"),("Barcelona","Copa del Rey","1996-97"),("Barcelona","Supercopa de España",1996),("Barcelona","UEFA Cup Winners' Cup","1996-97"),("Inter Milan","UEFA Cup","1997-98"),("Real Madrid","La Liga","2002-03"),("Real Madrid","La Liga","2006-07"),("Real Madrid","Supercopa de España",2003),("Real Madrid","Intercontinental Cup",2002),("Corinthians","Campeonato Paulista",2009),("Corinthians","Copa do Brasil",2009),("Brazil","FIFA World Cup",1994),("Brazil","FIFA World Cup",2002),("Brazil","Copa América",1997),("Brazil","Copa América",1999),("Brazil","FIFA Confederations Cup",1997)],
"ronaldinho": [("Grêmio","Copa Sul",1999),("Grêmio","Campeonato Gaúcho",1999),("PSG","UEFA Intertoto Cup",2001),("Barcelona","La Liga","2004-05"),("Barcelona","La Liga","2005-06"),("Barcelona","Supercopa de España",2005),("Barcelona","Supercopa de España",2006),("Barcelona","UEFA Champions League","2005-06"),("AC Milan","Serie A","2010-11"),("Flamengo","Campeonato Carioca",2011),("Atlético Mineiro","Campeonato Mineiro",2013),("Atlético Mineiro","Copa Libertadores",2013),("Atlético Mineiro","Recopa Sudamericana",2014),("Brazil","FIFA World Cup",2002),("Brazil","Copa América",1999),("Brazil","FIFA Confederations Cup",2005)],
"maradona": [("Boca Juniors","Argentine Primera División","1981 Metropolitano"),("Barcelona","Copa del Rey","1982-83"),("Barcelona","Copa de la Liga",1983),("Napoli","Serie A","1986-87"),("Napoli","Serie A","1989-90"),("Napoli","Coppa Italia","1986-87"),("Napoli","Supercoppa Italiana",1990),("Napoli","UEFA Cup","1988-89"),("Argentina U20","FIFA World Youth Championship",1979),("Argentina","FIFA World Cup",1986),("Argentina","Artemio Franchi Cup",1993)],
}

# RSSSF's current Pelé page reports a broader all-matches universe by team and
# by the source's own treatment. These component rows sum to 1,413 matches and
# 1,324 goals. They are deliberately kept as a parallel aggregate assertion:
# they overlap the season table and cannot support an exact age curve.
PELE_RSSSF_AGGREGATES = [
    ("Santos","1956-1974","rsssf_core_set",666,644,"club_competition_aggregate_unallocated"),
    ("Santos","1956-1974","friendlies",451,449,"all_other_club"),
    ("Combined Santos/Vasco","1957","all_listed",4,6,"all_other_club"),
    ("Brazil","1957-1971","senior_national_team",92,77,"national_team_all_matches_unallocated"),
    ("Brazil — other matches","1957-1976","rsssf_core_set",4,2,"national_team_other"),
    ("Brazil — other matches","1957-1976","friendlies",45,42,"national_team_friendlies"),
    ("Army teams","1959","rsssf_core_set",4,4,"representative_team_other"),
    ("Army teams","1959","friendlies",10,12,"representative_team_other"),
    ("São Paulo selection","1959-1969","all_listed",15,12,"representative_team_other"),
    ("New York Cosmos","1975-1977","rsssf_core_set",65,37,"club_competition_aggregate_unallocated"),
    ("New York Cosmos","1975-1977","friendlies",43,29,"all_other_club"),
    ("Other selects","1973-1987","all_listed",5,2,"representative_team_other"),
    ("Other teams","1974-1990","all_listed",6,8,"representative_team_other"),
    ("Fluminense","1978","guest_appearance",2,0,"all_other_club"),
    ("Flamengo","1979","guest_appearance",1,0,"all_other_club"),
]

def pele_rsssf_aggregates():
    source=(RAW/'pele_rsssf_data.html').read_bytes().decode('cp1252',errors='replace')
    normalized=re.sub(r'\s+',' ',source)
    if '1413 -1324' not in normalized.replace('–','-').replace('—','-'):
        raise ValueError('RSSSF Pelé aggregate total changed; review the source')
    rows=[]
    for team,period,treatment,apps,goals,family in PELE_RSSSF_AGGREGATES:
        rows.append({'player_id':'pele','player_name':'Pelé','team':team,'period':period,'source_treatment':treatment,'appearances':apps,'goals':goals,'competition_family':family,'variant_id':'rsssf_pele_all_listed_matches_2025','component_role':'additive_component','overlaps_season_competition':1,'supports_exact_age_curve':0,'source_id':'rsssf_pele_additional_data','source_url':'https://www.rsssf.org/players/ppeledata.html','source_granularity':'multi_year_aggregate'})
    return pd.DataFrame(rows)

def title_family(name):
    n=name.lower()
    if 'world cup' in n and 'club' not in n: return 'national_team_world_cup_finals'
    if any(x in n for x in ['confederations','finalissima','artemio franchi']): return 'national_team_intercontinental_championship_finals'
    if any(x in n for x in ['copa américa','european championship']): return 'national_team_continental_championship_finals'
    if 'nations league' in n: return 'national_team_continental_nations_league'
    if any(x in n for x in ['intercontinental cup','club world']): return 'intercontinental_federation_cup'
    if any(x in n for x in ['libertadores','champions league','uefa cup','cup winners','intertoto','recopa sudamericana','uefa super cup','arab club champions']): return 'continental_federation_cup'
    if any(x in n for x in ['paulista','carioca','mineiro','gaúcho','rio-são','copa sul']): return 'regional_league_or_cup'
    if any(x in n for x in ['la liga','serie a','brasileiro','primera','nasl','mls cup','premier league','saudi pro league','ligue 1']): return 'national_league'
    if any(x in n for x in ['supercopa','supercoppa','supertaça','trophée','shield']): return 'domestic_super_cup_or_shield'
    if any(x in n for x in ['copa del rey','coppa italia','knvb','copa do brasil','copa de la liga','fa cup','league cup']): return 'domestic_cup'
    return 'other_championship'

WEB_TAXONOMY = [
    {"id":"club","label":"Club goals","children":[
        {"id":"national_league","label":"National league"},
        {"id":"continental_federation_cup","label":"Continental federation cup"},
        {"id":"intercontinental_federation_cup","label":"Intercontinental federation cup"},
        {"id":"regional_league","label":"Regional league"},
        {"id":"all_other_club","label":"All other club goals"},
    ]},
    {"id":"national_team","label":"National-team goals","children":[
        {"id":"national_team_world_cup_finals","label":"World Cup finals"},
        {"id":"national_team_world_cup_qualification","label":"World Cup qualification"},
        {"id":"national_team_continental_championship_finals","label":"Continental championship finals"},
        {"id":"national_team_continental_championship_qualification","label":"Continental championship qualification"},
        {"id":"national_team_intercontinental_championship_finals","label":"Intercontinental championship finals"},
        {"id":"national_team_continental_nations_league","label":"Continental Nations League"},
        {"id":"national_team_olympic","label":"Olympic"},
        {"id":"national_team_friendlies","label":"Friendlies"},
        {"id":"national_team_other","label":"All other national-team goals"},
    ]},
]

WEB_PLAYERS = {
    "pele":{"shortName":"Pelé","country":"Brazil","color":"#ef6f4d","era":"historical","role":"forward"},
    "messi":{"shortName":"Messi","country":"Argentina","color":"#7c9cff","era":"modern","role":"forward"},
    "cristiano":{"shortName":"Cristiano","country":"Portugal","color":"#d8b650","era":"modern","role":"forward"},
    "ronaldo":{"shortName":"R9","country":"Brazil","color":"#53b98f","era":"modern","role":"forward"},
    "ronaldinho":{"shortName":"Ronaldinho","country":"Brazil","color":"#ba78d1","era":"modern","role":"attacking_midfielder"},
    "maradona":{"shortName":"Maradona","country":"Argentina","color":"#e45475","era":"historical","role":"attacking_midfielder"},
}

# Aggregate assertions that reconcile the fine Pelé season table to RSSSF's
# broader 1,413-match/1,324-goal universe. Their dates are storage keys only;
# aggregate_only rows are deliberately excluded from timeline curves.
PELE_WEB_BRIDGES = [
    (1957,"Combined Santos/Vasco",4,6,"all_other_club"),
    (1959,"Army teams",14,16,"all_other_club"),
    (1969,"São Paulo selection",15,12,"all_other_club"),
    (1974,"Santos friendlies and tours",451,449,"all_other_club"),
    (1974,"RSSSF Santos appearance reconciliation",6,0,"all_other_club"),
    (1976,"Brazil other matches",4,2,"national_team_other"),
    (1976,"Brazil other friendlies",45,42,"national_team_friendlies"),
    (1977,"RSSSF Cosmos canceled-match reconciliation",1,0,"all_other_club"),
    (1978,"Fluminense guest matches",2,0,"all_other_club"),
    (1979,"Flamengo guest match",1,0,"all_other_club"),
    (1987,"Other representative selections",5,2,"all_other_club"),
    (1990,"Other teams",6,8,"all_other_club"),
]

# Santos friendly/tour matches allocated by calendar year from the public
# match-by-match Pelé ledger. The ledger totals 450 matches and 449 goals for
# Santos friendlies in 1956–1974. One 1956 match/goal is already present in the
# season table, so the 1956 additive row below is the remaining 1/1.
# Source: https://pt.wikipedia.org/wiki/Estat%C3%ADsticas_de_Pel%C3%A9
PELE_SANTOS_FRIENDLIES_BY_YEAR = [
    (1956,1,1), (1957,29,16), (1958,14,14), (1959,42,48),
    (1960,30,28), (1961,36,48), (1962,17,17), (1963,15,22),
    (1964,12,6), (1965,21,33), (1966,19,16), (1967,33,31),
    (1968,32,24), (1969,18,18), (1970,25,37), (1971,32,22),
    (1972,38,36), (1973,26,27), (1974,9,4),
]

def user_bucket(family):
    if family in {child['id'] for group in WEB_TAXONOMY for child in group['children']}: return family
    if family in {'domestic_cup','domestic_super_cup','domestic_super_cup_or_shield','all_other_club','unclassified_club','club_competition_aggregate_unallocated'}: return 'all_other_club'
    if family in {'regional_league_or_cup','regional_competition'}: return 'regional_league'
    if family.startswith('national_team_'): return 'national_team_other'
    return 'all_other_club'

def title_bucket(row):
    family=row['competition_family']; name=row['competition_name'].lower(); team=row['team'].lower()
    if 'olympic' in name: return 'national_team_olympic'
    if family.startswith('national_team_'): return user_bucket(family)
    if any(token in team for token in ['argentina','brazil','portugal']): return 'national_team_other'
    return user_bucket(family)

def build_web_bundle(season,national_appearances,title_rows,coverage):
    season=pd.DataFrame(season); national=pd.DataFrame(national_appearances); titles=pd.DataFrame(title_rows)
    players=[]
    for pid,cfg in PLAYERS.items():
        birth=pd.Timestamp(cfg['birth'])
        observations=[]
        club=season[(season.player_id==pid)&(season.team_context=='club')]
        for _,row in club.iterrows():
            end_year=season_end_year(row.season)
            end_date=pd.Timestamp(f'{end_year}-06-30' if re.search(r'\d{4}\s*[-/]\s*\d{2}',str(row.season)) else f'{end_year}-12-31')
            observations.append({'period':str(row.season),'period_end':end_date.date().isoformat(),'age':round((end_date-birth).days/365.2425,3),'team_context':'club','bucket':user_bucket(row.competition_family),'competition_family':row.competition_family,'team':row.team,'competition_name':row.competition_name,'appearances':int(row.appearances),'goals':int(row.goals),'wins':None,'source_granularity':row.source_granularity})
        country=national[national.player_id==pid].copy()
        country['year']=pd.to_datetime(country.date_iso).dt.year
        for (year,family),rows in country.groupby(['year','competition_family']):
            end_date=pd.Timestamp(f'{year}-12-31')
            observations.append({'period':str(year),'period_end':end_date.date().isoformat(),'age':round((end_date-birth).days/365.2425,3),'team_context':'national_team','bucket':user_bucket(family),'competition_family':family,'team':rows.team.iloc[0],'competition_name':family,'appearances':int(len(rows)),'goals':int(rows.goals.sum()),'wins':int((rows.outcome=='W').sum()),'source_granularity':'calendar_year_from_match_ledger'})
        youth=season[(season.player_id==pid)&(season.team_context=='national_team')&(season.seniority!='senior')]
        for _,row in youth.iterrows():
            year=season_end_year(row.season); end_date=pd.Timestamp(f'{year}-12-31')
            bucket='national_team_olympic' if re.search(r'U23|Olympic',row.team,re.I) else 'national_team_other'
            observations.append({'period':str(row.season),'period_end':end_date.date().isoformat(),'age':round((end_date-birth).days/365.2425,3),'team_context':'national_team','bucket':bucket,'competition_family':bucket,'team':row.team,'competition_name':row.competition_name,'appearances':int(row.appearances),'goals':int(row.goals),'wins':None,'source_granularity':row.source_granularity})
        if pid=='pele':
            for year,apps,goals in PELE_SANTOS_FRIENDLIES_BY_YEAR:
                end_date=pd.Timestamp(f'{year}-12-31')
                observations.append({'period':str(year),'period_end':end_date.date().isoformat(),'age':round((end_date-birth).days/365.2425,3),'team_context':'club','bucket':'all_other_club','competition_family':'club_friendly','team':'Santos','competition_name':'Friendly and tour matches','appearances':apps,'goals':goals,'wins':None,'source_granularity':'calendar_year_from_match_ledger','source_url':'https://pt.wikipedia.org/wiki/Estat%C3%ADsticas_de_Pel%C3%A9'})
            for year,label,apps,goals,bucket in PELE_WEB_BRIDGES:
                end_date=pd.Timestamp(f'{year}-12-31')
                observations.append({'period':str(year),'period_end':end_date.date().isoformat(),'age':round((end_date-birth).days/365.2425,3),'team_context':'national_team' if bucket.startswith('national_team_') else 'club','bucket':bucket,'competition_family':bucket,'team':label,'competition_name':label,'appearances':apps,'goals':goals,'wins':None,'source_granularity':'rsssf_multi_year_aggregate_bridge','aggregate_only':True})
        title_events=[]
        for _,row in titles[titles.player_id==pid].iterrows():
            year=season_end_year(row.edition)
            end_date=pd.Timestamp(f'{year}-12-31')
            title_events.append({'year':year,'date':end_date.date().isoformat(),'age':round((end_date-birth).days/365.2425,3),'bucket':title_bucket(row),'competition_name':row.competition_name,'team':row.team,'edition':str(row.edition)})
        player_coverage=next(item for item in coverage if item['player_id']==pid)
        info=WEB_PLAYERS[pid]
        players.append({'id':pid,'name':cfg['name'],**info,'born':cfg['birth'],'years':f"{player_coverage['season_first']}–{player_coverage['season_last']}",'observations':sorted(observations,key=lambda row:(row['period_end'],row['team_context'],row['bucket'])),'titles':sorted(title_events,key=lambda row:row['date']),'coverage':{'club':'Career-spanning season/competition aggregates','national':f"{player_coverage['national_appearance_rows']} complete senior caps",'titles':f"{player_coverage['titles']} listed championship editions"}})
    bundle={'meta':{'dataCutoff':DATA_CUTOFF.isoformat(),'isFixture':False,'notice':'Timeline curves use dated or season-allocated records only. Multi-year aggregate assertions are retained for provenance but are not plotted at an arbitrary endpoint.'},'taxonomy':WEB_TAXONOMY,'players':players}
    (ROOT/'data'/'web_dataset.json').write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':')))

def main():
    season=[]
    for pid,cfg in PLAYERS.items():
        season += parse_club_stats(pid,cfg)
        season += parse_national_year_stats(pid,cfg)
    pd.DataFrame(season).to_csv(OUT/'season_competition.csv',index=False)

    national_appearances=[]; intl=[]
    for pid in PLAYERS:
        appearances,events=parse_rsssf_national_ledger(pid)
        national_appearances+=appearances; intl+=events
    pd.DataFrame(intl).to_csv(OUT/'national_team_goal_events.csv',index=False)
    pd.DataFrame(national_appearances).to_csv(OUT/'national_team_appearances.csv',index=False)
    pd.DataFrame([row for row in national_appearances if row['player_id']=='maradona']).to_csv(OUT/'national_team_appearances_rsssf.csv',index=False)

    modern=modern_transfermarkt()
    modern.to_csv(OUT/'modern_match_appearances.csv',index=False)
    pele_rsssf_aggregates().to_csv(OUT/'historical_aggregate_assertions.csv',index=False)

    title_rows=[]
    # Cristiano table is uniquely structured and already includes every team result.
    cr=pd.read_html(str(RAW/'cristiano.html'), flavor='lxml')[2]
    TITLES['cristiano']=[]
    for _,r in cr.iterrows():
        comp=clean(r['Competition'])
        if any(x in comp.lower() for x in ['runner-up','third place','fourth place','bronze']): continue
        TITLES['cristiano'].append((clean(r['Club / national team']),comp,clean(r['Season / year'])))
    for pid,items in TITLES.items():
        for team,comp,edition in items:
            if season_end_year(edition) and season_end_year(edition)>DATA_CUTOFF.year: continue
            title_rows.append({'player_id':pid,'player_name':PLAYERS[pid]['name'],'team':team,'competition_name':comp,'edition':edition,'competition_family':title_family(comp),'won':1,'participation_status':'listed_in_player_honours','source_id':f'wikipedia_{pid}_honours','source_url':SOURCE_URLS[pid]})
    pd.DataFrame(title_rows).to_csv(OUT/'titles.csv',index=False)

    cov=[]
    s=pd.DataFrame(season); i=pd.DataFrame(intl)
    for pid,cfg in PLAYERS.items():
        m=modern[modern.player_id==pid]
        player_seasons=s.loc[s.player_id==pid,'season'].astype(str).tolist()
        season_key=lambda value:int(re.search(r'\d{4}',value).group())
        cov.append({'player_id':pid,'player_name':cfg['name'],'season_rows':int((s.player_id==pid).sum()),'season_first':min(player_seasons,key=season_key) if player_seasons else None,'season_last':max(player_seasons,key=season_key) if player_seasons else None,'national_goal_events':int(i.loc[i.player_id==pid,'goals'].sum()),'national_goal_source_granularity':'goal_event','national_appearance_rows':sum(1 for row in national_appearances if row['player_id']==pid),'modern_match_appearances':len(m),'modern_first':str(m.date.min()) if len(m) else None,'modern_last':str(m.date.max()) if len(m) else None,'titles':sum(1 for x in title_rows if x['player_id']==pid)})
    (OUT/'coverage.json').write_text(json.dumps({'generated':date.today().isoformat(),'data_cutoff':DATA_CUTOFF.isoformat(),'scope_note':'Users select named competition families; source treatments remain metadata.','players':cov},indent=2,ensure_ascii=False))
    build_web_bundle(season,national_appearances,title_rows,cov)
    print(json.dumps(cov,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
