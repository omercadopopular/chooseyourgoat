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

PLAYERS = {
    "pele": {"name": "Pelé", "birth": "1940-10-23", "wiki": "pele", "club_table": 5, "national_table": 7},
    "messi": {"name": "Lionel Messi", "birth": "1987-06-24", "wiki": "messi", "club_table": 3, "national_table": 4},
    "cristiano": {"name": "Cristiano Ronaldo", "birth": "1985-02-05", "wiki": "cristiano", "club_table": 17, "national_table": 18},
    "ronaldo": {"name": "Ronaldo Nazário", "birth": "1976-09-18", "wiki": "ronaldo", "club_table": 2, "national_table": 3},
    "ronaldinho": {"name": "Ronaldinho", "birth": "1980-03-21", "wiki": "ronaldinho", "club_table": 3, "national_table": 4},
    "maradona": {"name": "Diego Maradona", "birth": "1960-10-30", "wiki": "maradona", "club_table": 3, "national_table": 4},
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
    b=(bucket+" "+division).lower()
    if "campeonato paulista" in b or "regional" in b or "state league" in b or "rio-são paulo" in b:
        return "regional_league"
    if "league" in b or "brasileiro" in b or "liga" in b or "serie a" in b:
        return "national_league"
    if "libertadores" in b or "continental" in b or "champions" in b or "uefa" in b:
        return "continental_federation_cup"
    if "intercontinental" in b or "club world" in b:
        return "intercontinental_federation_cup"
    if "cup" in b or "domestic" in b:
        return "domestic_cup"
    if "other" in b or "postseason" in b:
        return "all_other_club"
    return "unclassified_club"

def parse_club_stats(player_id, cfg):
    tables=pd.read_html(RAW/f"{cfg['wiki']}.html")
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
                result.append({"player_id":player_id,"player_name":cfg["name"],"team_context":"club","team":club,"season":season,"source_bucket":base,"competition_name":division if "league" in base.lower() and division else base,"competition_family":bucket_family(base,division),"seniority":seniority,"appearances":apps,"goals":goals,"appearances_source_text":apps_text,"goals_source_text":goals_text,"source_id":f"wikipedia_{player_id}_career_stats","source_url":SOURCE_URLS[player_id],"source_granularity":"season_bucket"})
    return result

def parse_national_year_stats(player_id,cfg):
    df=flatten_columns(pd.read_html(RAW/f"{cfg['wiki']}.html")[cfg["national_table"]].copy())
    team_col=next(c for c in df if c.split("|")[0] in {"Team","Season"})
    year_col=next(c for c in df if c.split("|")[0] in {"Year","Tournament"})
    df[team_col]=df[team_col].replace("nan",pd.NA).ffill()
    out=[]
    for _,r in df.iterrows():
        team=clean(r[team_col]); year=clean(r[year_col])
        if year.lower()=="total" or not re.search(r"\d{4}",year): continue
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
    if any(x in n for x in ["confederations cup","finalissima","artemio franchi","copa de oro","panamerican championship"]): return "national_team_intercontinental_championship_finals"
    if any(x in n for x in ["copa américa","copa america","uefa euro","european championship","gold cup","asian cup","africa cup of nations","ofc nations"]):
        return "national_team_continental_championship_finals" if "qual" not in n else "national_team_continental_championship_qualification"
    if "nations league" in n: return "national_team_continental_nations_league"
    if any(x in n for x in ["olympic","pre-olympic"]): return "national_team_olympic"
    if n in {"friendly","nan",""} or any(x in n for x in ["friendly","anniversary"]): return "national_team_friendlies"
    return "national_team_other"

def parse_wiki_international_goals(player_id,path,table_index):
    df=pd.read_html(path)[table_index].copy()
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
"ronaldo": [("Cruzeiro","Campeonato Mineiro",1994),("PSV","KNVB Cup","1995-96"),("Barcelona","Copa del Rey","1996-97"),("Barcelona","Supercopa de España",1996),("Barcelona","UEFA Cup Winners' Cup","1996-97"),("Inter Milan","UEFA Cup","1997-98"),("Real Madrid","La Liga","2002-03"),("Real Madrid","La Liga","2006-07"),("Real Madrid","Supercopa de España",2003),("Real Madrid","Intercontinental Cup",2002),("Corinthians","Campeonato Paulista",2009),("Corinthians","Copa do Brasil",2009),("Brazil","FIFA World Cup",1994),("Brazil","FIFA World Cup",2002),("Brazil","Copa América",1997),("Brazil","Copa América",1999),("Brazil","FIFA Confederations Cup",1997)],
"ronaldinho": [("Grêmio","Copa Sul",1999),("Grêmio","Campeonato Gaúcho",1999),("PSG","UEFA Intertoto Cup",2001),("Barcelona","La Liga","2004-05"),("Barcelona","La Liga","2005-06"),("Barcelona","Supercopa de España",2005),("Barcelona","Supercopa de España",2006),("Barcelona","UEFA Champions League","2005-06"),("AC Milan","Serie A","2010-11"),("Flamengo","Campeonato Carioca",2011),("Atlético Mineiro","Campeonato Mineiro",2013),("Atlético Mineiro","Copa Libertadores",2013),("Atlético Mineiro","Recopa Sudamericana",2014),("Brazil","FIFA World Cup",2002),("Brazil","Copa América",1999),("Brazil","FIFA Confederations Cup",2005)],
"maradona": [("Boca Juniors","Argentine Primera División","1981 Metropolitano"),("Barcelona","Copa del Rey","1982-83"),("Barcelona","Copa de la Liga",1983),("Napoli","Serie A","1986-87"),("Napoli","Serie A","1989-90"),("Napoli","Coppa Italia","1986-87"),("Napoli","Supercoppa Italiana",1990),("Napoli","UEFA Cup","1988-89"),("Argentina U20","FIFA World Youth Championship",1979),("Argentina","FIFA World Cup",1986),("Argentina","Artemio Franchi Cup",1993)],
}

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

def main():
    season=[]
    for pid,cfg in PLAYERS.items():
        season += parse_club_stats(pid,cfg)
        season += parse_national_year_stats(pid,cfg)
    pd.DataFrame(season).to_csv(OUT/'season_competition.csv',index=False)

    intl=[]
    intl += parse_wiki_international_goals('messi',RAW/'messi_intl.html',1)
    intl += parse_wiki_international_goals('cristiano',RAW/'cristiano_intl.html',2)
    intl += parse_wiki_international_goals('pele',RAW/'pele_intl.html',1)
    intl += parse_wiki_international_goals('ronaldo',RAW/'ronaldo.html',5)
    intl += parse_wiki_international_goals('ronaldinho',RAW/'ronaldinho.html',5)
    maradona_appearances,maradona_goals=parse_maradona_rsssf()
    intl += maradona_goals
    pd.DataFrame(intl).to_csv(OUT/'national_team_goal_events.csv',index=False)
    pd.DataFrame(maradona_appearances).to_csv(OUT/'national_team_appearances_rsssf.csv',index=False)

    modern=modern_transfermarkt()
    modern.to_csv(OUT/'modern_match_appearances.csv',index=False)

    title_rows=[]
    # Cristiano table is uniquely structured and already includes every team result.
    cr=pd.read_html(RAW/'cristiano.html')[2]
    TITLES['cristiano']=[]
    for _,r in cr.iterrows():
        comp=clean(r['Competition'])
        if any(x in comp.lower() for x in ['runner-up','third place','fourth place','bronze']): continue
        TITLES['cristiano'].append((clean(r['Club / national team']),comp,clean(r['Season / year'])))
    for pid,items in TITLES.items():
        for team,comp,edition in items:
            title_rows.append({'player_id':pid,'player_name':PLAYERS[pid]['name'],'team':team,'competition_name':comp,'edition':edition,'competition_family':title_family(comp),'won':1,'participation_status':'listed_in_player_honours','source_id':f'wikipedia_{pid}_honours','source_url':SOURCE_URLS[pid]})
    pd.DataFrame(title_rows).to_csv(OUT/'titles.csv',index=False)

    cov=[]
    s=pd.DataFrame(season); i=pd.DataFrame(intl)
    for pid,cfg in PLAYERS.items():
        m=modern[modern.player_id==pid]
        player_seasons=s.loc[s.player_id==pid,'season'].astype(str).tolist()
        season_key=lambda value:int(re.search(r'\d{4}',value).group())
        cov.append({'player_id':pid,'player_name':cfg['name'],'season_rows':int((s.player_id==pid).sum()),'season_first':min(player_seasons,key=season_key) if player_seasons else None,'season_last':max(player_seasons,key=season_key) if player_seasons else None,'national_goal_events':int(i.loc[i.player_id==pid,'goals'].sum()),'national_goal_source_granularity':'goal_event','national_appearance_rows':91 if pid=='maradona' else 0,'modern_match_appearances':len(m),'modern_first':str(m.date.min()) if len(m) else None,'modern_last':str(m.date.max()) if len(m) else None,'titles':sum(1 for x in title_rows if x['player_id']==pid)})
    (OUT/'coverage.json').write_text(json.dumps({'generated':date.today().isoformat(),'scope_note':'No official/unofficial primitive. Users select competition families.','players':cov},indent=2,ensure_ascii=False))
    print(json.dumps(cov,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
