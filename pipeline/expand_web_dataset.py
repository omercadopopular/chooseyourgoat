"""Append the first nine-player expansion from cached public career pages.

Club records are season/competition tables. Senior national-team records come
from complete match ledgers and are allocated to the selectable competition
families before being grouped into calendar-year chart observations.
"""
from pathlib import Path
import json,re
import pandas as pd
from lxml import html
from build_public_dataset import clean,number,flatten_columns,bucket_family,season_end_year,user_bucket,title_family,classify_national_competition,is_lower_division_club,cristiano_partial_2025_club,WEB_TAXONOMY,DATA_CUTOFF

ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw'
PLAYERS={
'mbappe':dict(name='Kylian Mbappé',shortName='Mbappé',birth='1998-12-20',country='France',color='#4976d1',era='current',role='forward',wiki='mbappe'),
'haaland':dict(name='Erling Haaland',shortName='Haaland',birth='2000-07-21',country='Norway',color='#70b7c8',era='current',role='forward',wiki='haaland'),
'cruyff':dict(name='Johan Cruyff',shortName='Cruyff',birth='1947-04-25',country='Netherlands',color='#e88932',era='historical',role='attacking_midfielder',wiki='cruyff'),
'baggio':dict(name='Roberto Baggio',shortName='Baggio',birth='1967-02-18',country='Italy',color='#4771b2',era='modern',role='attacking_midfielder',wiki='baggio'),
'neymar':dict(name='Neymar',shortName='Neymar',birth='1992-02-05',country='Brazil',color='#d6b329',era='modern',role='forward',wiki='neymar'),
'lewandowski':dict(name='Robert Lewandowski',shortName='Lewandowski',birth='1988-08-21',country='Poland',color='#c94b55',era='modern',role='forward',wiki='lewandowski'),
'suarez':dict(name='Luis Suárez',shortName='Suárez',birth='1987-01-24',country='Uruguay',color='#65a6d9',era='modern',role='forward',wiki='suarez'),
'puskas':dict(name='Ferenc Puskás',shortName='Puskás',birth='1927-04-01',country='Hungary',color='#b23a48',era='historical',role='forward',wiki='puskas'),
'romario':dict(name='Romário',shortName='Romário',birth='1966-01-29',country='Brazil',color='#4a9d68',era='modern',role='forward',wiki='romario'),
}

SOURCE_URLS={
'mbappe':'https://en.wikipedia.org/wiki/Kylian_Mbapp%C3%A9','haaland':'https://en.wikipedia.org/wiki/Erling_Haaland','cruyff':'https://en.wikipedia.org/wiki/Johan_Cruyff','baggio':'https://en.wikipedia.org/wiki/Roberto_Baggio','neymar':'https://en.wikipedia.org/wiki/Neymar','lewandowski':'https://en.wikipedia.org/wiki/Robert_Lewandowski','suarez':'https://en.wikipedia.org/wiki/Luis_Su%C3%A1rez','puskas':'https://en.wikipedia.org/wiki/Ferenc_Pusk%C3%A1s','romario':'https://en.wikipedia.org/wiki/Rom%C3%A1rio'}
TEAM_ALIASES={
('mbappe','Paris Saint-Germain (loan)'):'Paris Saint-Germain',
('puskas','Budapest Honvéd'):'Kispest/Budapesti Honvéd SE',
('romario','PSV Eindhoven'):'PSV',
('romario','Al-Sadd'):'Al-Sadd (loan)',
('romario','América-RJ'):'America-RJ',
}
RSSSF_NATIONAL={
'cruyff':('cruyff_rsssf_intl.html',48,33,'Netherlands','https://www.rsssf.org/miscellaneous/cruijff-intlg.html'),
'baggio':('baggio_rsssf_intl.html',56,27,'Italy','https://www.rsssf.org/miscellaneous/rbaggio-intlg.html'),
'neymar':('neymar_rsssf_intl.html',128,79,'Brazil','https://www.rsssf.org/miscellaneous/neymar-intlg.html'),
'lewandowski':('lewandowski_rsssf_intl.html',163,88,'Poland','https://www.rsssf.org/miscellaneous/lewandowski-intlg.html'),
'suarez':('suarez_rsssf_intl.html',143,69,'Uruguay','https://www.rsssf.org/miscellaneous/bijtertje-intlg.html'),
'puskas':('puskas_rsssf_intl.html',89,84,'Hungary','https://www.rsssf.org/miscellaneous/puskas-intlg.html'),
'romario':('romario_rsssf_intl.html',70,55,'Brazil','https://www.rsssf.org/miscellaneous/romario-intlg.html'),
}
TM_NATIONAL={
'mbappe':('mbappe_tm_performance.json','3377',94,55,'France'),
'haaland':('haaland_tm_performance.json','3440',48,55,'Norway'),
}
TM_FAMILY={
'FIWC':'national_team_world_cup_finals','EURO':'national_team_continental_championship_finals',
'EMQ':'national_team_continental_championship_qualification','POEM':'national_team_continental_championship_qualification',
'UNFI':'national_team_continental_nations_league','UNLA':'national_team_continental_nations_league','UNLB':'national_team_continental_nations_league',
'FS':'national_team_friendlies',
}
def source(pid): return SOURCE_URLS[pid]
def canonical_team(pid,team): return TEAM_ALIASES.get((pid,team),team)
def tables(pid): return pd.read_html(str(RAW/f'{pid}.html'),flavor='lxml')
def find_table(pid,required):
    for raw in tables(pid):
        df=flatten_columns(raw.copy()); heads=' '.join(df.columns).lower()
        if all(x.lower() in heads for x in required): return df
    raise ValueError(f'{pid}: table with {required} not found')
def pair_columns(df,base):
    a=next((c for c in df if c.endswith('Apps') and c.rsplit('|',1)[0]==base),None)
    g=next((c for c in df if c.endswith('Goals') and c.rsplit('|',1)[0]==base),None)
    return a,g

def norm(value):
    import unicodedata
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',value)

def title_bucket_for(pid,team,competition):
    family=title_family(competition)
    if re.search(r'\bU\s*-?\s*\d{2}\b|\byouth\b',team,re.I):
        return 'national_team_olympic' if 'olympic' in competition.lower() else 'national_team_youth'
    if norm(team).startswith(norm(PLAYERS[pid]['country'])):
        if 'olympic' in competition.lower(): return 'national_team_olympic'
        return family if family.startswith('national_team_') else 'national_team_other'
    if family.startswith('national_team_'): return family
    return user_bucket(family)

def national_label(family):
    return {
        'national_team_world_cup_finals':'World Cup',
        'national_team_world_cup_qualification':'World Cup qualifier',
        'national_team_continental_championship_finals':'Continental championship',
        'national_team_continental_championship_qualification':'Continental championship qualifier',
        'national_team_intercontinental_championship_finals':'Intercontinental championship',
        'national_team_continental_nations_league':'Continental Nations League',
        'national_team_olympic':'Olympic Games',
        'national_team_friendlies':'Friendly',
        'national_team_other':'Other national-team match',
    }[family]

def national_competition_name(pid,family,raw_name=''):
    european={'mbappe','haaland','cruyff','baggio','lewandowski','puskas'}
    if family=='national_team_world_cup_finals': return 'FIFA World Cup'
    if family=='national_team_world_cup_qualification': return 'FIFA World Cup qualification'
    if family=='national_team_continental_championship_finals': return 'UEFA European Championship' if pid in european else 'Copa América'
    if family=='national_team_continental_championship_qualification': return 'UEFA European Championship qualification'
    if family=='national_team_intercontinental_championship_finals': return 'FIFA Confederations Cup'
    if family=='national_team_continental_nations_league': return 'UEFA Nations League'
    if family=='national_team_olympic': return 'Olympic Games'
    if family=='national_team_friendlies': return 'Friendly'
    return clean(raw_name) or national_label(family)

def grouped_national(pid,rows,source_url):
    birth=pd.Timestamp(PLAYERS[pid]['birth']); grouped={}
    for row in rows:
        year=int(row['date_iso'][:4]); family=row['competition_family']; name=row['competition_name']
        key=(year,family,row['team'],name); item=grouped.setdefault(key,{'appearances':0,'goals':0,'wins':0,'dates':[]})
        item['appearances']+=1; item['goals']+=row['goals']; item['wins']+=row.get('outcome')=='W'
        item['dates'].append(row['date_iso'])
    out=[]
    for (year,family,team,name),item in grouped.items():
        end=pd.Timestamp(f'{year}-12-31')
        out.append(dict(period=str(year),period_end=end.date().isoformat(),age=round((end-birth).days/365.2425,3),team_context='national_team',bucket=family,competition_family=family,team=team,competition_name=name,appearances=item['appearances'],goals=item['goals'],wins=item['wins'],first_date=min(item['dates']),last_date=max(item['dates']),source_granularity='calendar_year_from_match_ledger',source_url=source_url))
    return out

def rsssf_national(pid):
    filename,expected_caps,expected_goals,default_team,url=RSSSF_NATIONAL[pid]
    page=html.parse(str(RAW/filename)); date_pattern=r'(\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*\d{2})'
    source_rows=[]
    for block in page.xpath('//pre'):
        for line in block.text_content().splitlines():
            match=re.match(r'^\s*(\d+)\s+(.*?)\s*'+date_pattern+r'\s{1,}(.+?)\s*$',line)
            if match: source_rows.append((line,match))
    rows=[]; last_cumulative=0; previous_cap=0; team=default_team
    for line,match in source_rows:
        local_cap=int(match.group(1))
        if local_cap<=previous_cap:
            last_cumulative=0
            if pid=='puskas': team='Spain'
        previous_cap=local_cap
        values=[int(value) for value in re.findall(r'\d+',match.group(2).strip())]
        if len(values)>=2: match_goals,cumulative=values[-2],values[-1]
        elif len(values)==1: cumulative=values[0]; match_goals=max(0,cumulative-last_cumulative)
        else: cumulative=last_cumulative; match_goals=0
        last_cumulative=cumulative
        raw_date=re.sub(r'\s+','',match.group(3)).replace('/','-').replace('.','-')
        day,month,yy=map(int,raw_date.split('-')); year=1900+yy if yy>=40 else 2000+yy
        iso=f'{year:04d}-{month:02d}-{day:02d}'
        remainder=match.group(4).strip()
        result_match=re.search(r'\d+\s*[-x]\s*\d+',remainder)
        if result_match is None: raise ValueError(f'{pid}: cannot parse RSSSF row {line!r}')
        result=result_match.group(0)
        competition=clean(re.sub(r'^(?:\s*[\[(]\d+[\])])?\s*','',remainder[result_match.end():])) or 'Friendly'
        scores=[int(value) for value in re.findall(r'\d+',result)[:2]]
        outcome='W' if scores[0]>scores[1] else ('D' if scores[0]==scores[1] else 'L')
        family=classify_national_competition(competition)
        rows.append({'date_iso':iso,'team':team,'goals':match_goals,'outcome':outcome,'competition_family':family,'competition_name':national_competition_name(pid,family,competition)})
    if len(rows)!=expected_caps or sum(row['goals'] for row in rows)!=expected_goals:
        raise ValueError(f'{pid}: RSSSF ledger reconciled to {len(rows)} caps/{sum(row["goals"] for row in rows)} goals, expected {expected_caps}/{expected_goals}')
    return grouped_national(pid,rows,url)

def tm_national(pid):
    filename,team_id,expected_caps,expected_goals,team=TM_NATIONAL[pid]
    payload=json.loads((RAW/filename).read_text()); rows=[]
    for item in payload['data']['performance']:
        game=item['gameInformation']; general=item['statistics']['generalStatistics']
        if not game['isNationalGame'] or game['date']['dateTimeUTC'][:10]>DATA_CUTOFF.isoformat(): continue
        if str(item['clubsInformation']['club']['clubId'])!=team_id or general['participationState']!='played': continue
        code=game['competitionId']; family=TM_FAMILY.get(code)
        if family is None: family='national_team_world_cup_qualification' if code.startswith('WMQ') else 'national_team_other'
        scored=item['statistics']['goalStatistics']['goalsScoredTotal'] or 0
        club=item['clubsInformation']['club']; home=club['goalsTotal']; away=club['opponentGoalsTotal']
        rows.append({'date_iso':game['date']['dateTimeUTC'][:10],'team':team,'goals':int(scored),'outcome':'W' if home>away else ('D' if home==away else 'L'),'competition_family':family,'competition_name':national_competition_name(pid,family)})
    if len(rows)!=expected_caps or sum(row['goals'] for row in rows)!=expected_goals:
        raise ValueError(f'{pid}: Transfermarkt ledger reconciled to {len(rows)} caps/{sum(row["goals"] for row in rows)} goals, expected {expected_caps}/{expected_goals}')
    return grouped_national(pid,rows,f'https://tmapi.transfermarkt.technology/player/{payload["data"]["playerId"]}/performance-game')

PARTIAL_2025 = {
    'mbappe': dict(file='mbappe_tm_performance.json', club='418', team='Real Madrid', after='2025-07-09', expected=(24,29), definitions={
        'ES1':('La Liga','national_league'), 'CL':('UEFA Champions League','continental_federation_cup'), 'CDR':('Copa del Rey','all_other_club')}),
    'haaland': dict(file='haaland_tm_performance.json', club='281', team='Manchester City', after='2025-07-01', expected=(24,25), definitions={
        'GB1':('Premier League','national_league'), 'CL':('UEFA Champions League','continental_federation_cup')}),
    'lewandowski': dict(file='lewandowski_tm_performance.json', club='131', team='Barcelona', after='2025-06-30', expected=(18,8), definitions={
        'ES1':('La Liga','national_league'), 'CL':('UEFA Champions League','continental_federation_cup')}),
}

def partial_2025_club(pid):
    """Add only the dated post-table part of 2025 through the fixed cutoff."""
    cfg=PARTIAL_2025[pid]
    payload=json.loads((RAW/cfg['file']).read_text()); birth=pd.Timestamp(PLAYERS[pid]['birth'])
    definitions=cfg['definitions']
    grouped={}
    for item in payload['data']['performance']:
        game=item['gameInformation']; general=item['statistics']['generalStatistics']; club=item['clubsInformation']['club']
        date=game['date']['dateTimeUTC'][:10]
        if game['isNationalGame'] or str(club['clubId'])!=cfg['club'] or general['participationState']!='played': continue
        if not (cfg['after']<date<=DATA_CUTOFF.isoformat()): continue
        if game['competitionId'] not in definitions: raise ValueError(f'{pid}: unmapped 2025 club competition {game["competitionId"]}')
        name,bucket=definitions[game['competitionId']]; item_group=grouped.setdefault((name,bucket),{'appearances':0,'goals':0,'wins':0,'dates':[]})
        item_group['appearances']+=1
        item_group['goals']+=int(item['statistics']['goalStatistics']['goalsScoredTotal'] or 0)
        item_group['wins']+=club['goalsTotal']>club['opponentGoalsTotal']
        item_group['dates'].append(date)
    out=[]; end=pd.Timestamp(DATA_CUTOFF)
    for (name,bucket),item in grouped.items():
        out.append(dict(period='2025-26',period_end=DATA_CUTOFF.isoformat(),age=round((end-birth).days/365.2425,3),team_context='club',bucket=bucket,competition_family=bucket,team=cfg['team'],competition_name=name,appearances=item['appearances'],goals=item['goals'],wins=item['wins'],first_date=min(item['dates']),last_date=max(item['dates']),source_granularity='partial_season_from_match_ledger',source_url=f'https://tmapi.transfermarkt.technology/player/{payload["data"]["playerId"]}/performance-game'))
    actual=(sum(row['appearances'] for row in out),sum(row['goals'] for row in out))
    if actual!=cfg['expected']:
        raise ValueError(f'{pid}: partial 2025 club ledger reconciled to {actual}, expected {cfg["expected"]}')
    return out

def observations(pid):
    cfg=PLAYERS[pid]; birth=pd.Timestamp(cfg['birth']); out=[]
    df=find_table(pid,['club','season','total'])
    identity=[c for c in df if c.split('|')[0] in {'Club','Season Club','Season'}]
    def year_score(column):
        values=df[column].astype(str).head(20)
        return sum(bool(re.search(r'\b(?:19|20)\d{2}\b',value)) for value in values)
    season=max(identity,key=year_score); club=next(c for c in identity if c!=season)
    df[club]=df[club].replace('nan',pd.NA).ffill()
    for _,r in df.iterrows():
        team=canonical_team(pid,clean(r[club])); period=clean(r[season]); ey=season_end_year(period)
        if not ey or ey>DATA_CUTOFF.year or period.lower()=='total' or 'total' in team.lower(): continue
        end=pd.Timestamp(f'{ey}-06-30' if re.search(r'\d{4}\s*[-/]\s*\d{2}',period) else f'{ey}-12-31')
        for c in df.columns:
            if not c.endswith('Apps') or c.startswith('Total'): continue
            base=c.rsplit('|',1)[0]; a,g=pair_columns(df,base)
            if not a or not g: continue
            apps,goals=number(r[a]),number(r[g])
            if not apps and not goals: continue
            division=next((d for d in df if d.endswith('Division') and d.rsplit('|',1)[0]==base),None)
            competition=clean(r[division]) if division and clean(r[division]).lower() not in {'nan','total',''} else base
            fam=bucket_family(base,competition)
            bucket='lower_division_club' if is_lower_division_club(team,competition) else user_bucket(fam)
            out.append(dict(period=period,period_end=end.date().isoformat(),age=round((end-birth).days/365.2425,3),team_context='club',bucket=bucket,competition_family=fam,team=team,competition_name=competition,appearances=apps,goals=goals,wins=None,source_granularity='season_bucket',source_url=source(pid)))
    if pid in PARTIAL_2025: out.extend(partial_2025_club(pid))
    out.extend(tm_national(pid) if pid in TM_NATIONAL else rsssf_national(pid))
    return sorted(out,key=lambda x:(x['period_end'],x['team_context'],x['bucket']))

def honours(pid,observations):
    cfg=PLAYERS[pid]; birth=pd.Timestamp(cfg['birth']); root=html.parse(str(RAW/f'{pid}.html'))
    headings=root.xpath('//h2[.//*[@id="Honours"] or @id="Honours" or .//*[@id="Achievements_and_honours"] or @id="Achievements_and_honours"]')
    if not headings: return []
    known={norm(x['team']):x['team'] for x in observations}
    known[norm(cfg['country'])]=cfg['country']
    wrapper=headings[0].getparent(); current=wrapper.getnext(); nodes=[]
    while current is not None and not (current.tag=='div' and 'mw-heading2' in current.get('class','')):
        nodes.extend(current.iter()); current=current.getnext()
    active=None; result=[]; seen=set()
    for node in nodes:
        if node.tag in {'p','h3','h4'}:
            label=clean(' '.join(node.itertext()))
            key=norm(label)
            label=canonical_team(pid,label); key=norm(label)
            if key in known: active=known[key]
            elif key.startswith(norm(cfg['country'])) and len(label)<35: active=label
            elif key in {'individual','manager','managers','orders','ordersandfurtherhonours','awards'}: active=None
        if node.tag!='li' or not active: continue
        text=clean(' '.join(node.itertext()))
        if ':' not in text: continue
        competition,editions=text.split(':',1); low=competition.lower()
        if any(word in low for word in ['runner-up','third place','silver medal','top scorer','team of the','player of the','ballon','award','golden','record']): continue
        editions=re.split(r'runner-up|third place|second place',editions,flags=re.I)[0]
        for edition in re.findall(r'\b(?:19|20)\d{2}(?:[–-]\d{2,4})?',editions):
            edition=edition.replace('–','-'); year=season_end_year(edition)
            if not year or year>DATA_CUTOFF.year: continue
            key=(active,competition.strip(),edition)
            if key in seen: continue
            seen.add(key); end=pd.Timestamp(f'{year}-12-31')
            result.append(dict(year=year,date=end.date().isoformat(),age=round((end-birth).days/365.2425,3),bucket=title_bucket_for(pid,active,competition),competition_name=competition.strip(),team=active,edition=edition,source_url=source(pid)))
    return sorted(result,key=lambda x:(x['date'],x['team'],x['competition_name']))

def main():
    p=ROOT/'data/web_dataset.json'; data=json.loads(p.read_text()); existing={x['id']:x for x in data['players']}
    data['taxonomy']=WEB_TAXONOMY
    for base_player in data['players']:
        for row in base_player['observations']:
            if row['team_context']=='club' and is_lower_division_club(row['team'],row.get('competition_name','')):
                row['bucket']='lower_division_club'
            elif row['team_context']=='national_team' and re.search(r'\bU\s*-?\s*(?:17|19|20)\b|\byouth\b',row['team'],re.I):
                row['bucket']='national_team_youth'
    cristiano=existing['cristiano']
    cristiano['observations']=[row for row in cristiano['observations'] if row.get('source_granularity')!='partial_season_from_match_ledger']
    cristiano['observations'].extend(cristiano_partial_2025_club())
    cristiano['observations'].sort(key=lambda x:(x['period_end'],x['team_context'],x['bucket']))
    cristiano['years']=cristiano['years'].split('–')[0]+'–2025'
    for pid,cfg in PLAYERS.items():
        obs=observations(pid); titles=honours(pid,obs); years=[int(x['period_end'][:4]) for x in obs]
        player=dict(id=pid,**{k:cfg[k] for k in ['name','shortName','country','color','era','role']},born=cfg['birth'],years=f'{min(years)}–{max(years)}',observations=obs,titles=titles,competitions=[],competitionCoverage={'appearanceConfirmed':0,'winsMatched':0,'honoursUnmatched':len(titles),'benchConfirmed':0,'reconciliationStatus':'partial'},coverage={'club':'Career-spanning season/competition aggregates','national':f'{sum(x["appearances"] for x in obs if x["team_context"]=="national_team")} senior caps allocated by competition family','titles':f'{len(titles)} listed championship editions; participation reconciliation partial'})
        if pid in existing: existing[pid].update(player)
        else: data['players'].append(player)
    data['meta']['expansionNotice']='Nine-player expansion uses career-spanning club tables and complete senior national-team match ledgers allocated to selectable competition families. Competition-edition honours reconciliation remains partial where club aggregate rows cannot identify a named edition.'
    p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
if __name__=='__main__': main()
