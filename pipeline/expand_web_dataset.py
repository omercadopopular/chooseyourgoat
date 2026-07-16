"""Append the first nine-player expansion from cached public career pages.

Club records are season/competition tables. National records without a complete
match ledger are deliberately placed in national_team_other rather than being
invented into finer competition families.
"""
from pathlib import Path
import json,re
import pandas as pd
from lxml import html
from build_public_dataset import clean,number,flatten_columns,bucket_family,season_end_year,user_bucket,title_family,DATA_CUTOFF

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
    if norm(team).startswith(norm(PLAYERS[pid]['country'])):
        if 'olympic' in competition.lower(): return 'national_team_olympic'
        return family if family.startswith('national_team_') else 'national_team_other'
    if family.startswith('national_team_'): return family
    return user_bucket(family)

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
            out.append(dict(period=period,period_end=end.date().isoformat(),age=round((end-birth).days/365.2425,3),team_context='club',bucket=user_bucket(fam),competition_family=fam,team=team,competition_name=competition,appearances=apps,goals=goals,wins=None,source_granularity='season_bucket',source_url=source(pid)))
    nd=find_table(pid,['national team','year','apps','goals']); team=next(c for c in nd if c.split('|')[0]=='National team'); year=next(c for c in nd if c.split('|')[0]=='Year'); ac=next(c for c in nd if c.split('|')[-1]=='Apps'); gc=next(c for c in nd if c.split('|')[-1]=='Goals')
    nd[team]=nd[team].replace('nan',pd.NA).ffill()
    for _,r in nd.iterrows():
        y=season_end_year(clean(r[year])); apps,goals=number(r[ac]),number(r[gc])
        if not y or y>DATA_CUTOFF.year or (not apps and not goals): continue
        end=pd.Timestamp(f'{y}-12-31')
        out.append(dict(period=str(y),period_end=end.date().isoformat(),age=round((end-birth).days/365.2425,3),team_context='national_team',bucket='national_team_other',competition_family='national_team_all_matches_unallocated',team=clean(r[team]),competition_name='All senior national-team matches',appearances=apps,goals=goals,wins=None,source_granularity='calendar_year_total_unallocated',source_url=source(pid)))
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
    p=ROOT/'data/web_dataset.json'; data=json.loads(p.read_text()); existing={x['id'] for x in data['players']}
    for pid,cfg in PLAYERS.items():
        if pid in existing: continue
        obs=observations(pid); titles=honours(pid,obs); years=[int(x['period_end'][:4]) for x in obs]
        data['players'].append(dict(id=pid,**{k:cfg[k] for k in ['name','shortName','country','color','era','role']},born=cfg['birth'],years=f'{min(years)}–{max(years)}',observations=obs,titles=titles,competitions=[],competitionCoverage={'appearanceConfirmed':0,'winsMatched':0,'honoursUnmatched':len(titles),'benchConfirmed':0,'reconciliationStatus':'partial'},coverage={'club':'Career-spanning season/competition aggregates','national':'Calendar-year totals; competition allocation pending','titles':f'{len(titles)} listed championship editions; participation reconciliation partial'}))
    data['meta']['expansionNotice']='Nine-player expansion uses career-spanning club tables. Fine national-team competition allocation and honours reconciliation remain explicitly pending where complete ledgers are unavailable.'
    p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
if __name__=='__main__': main()
