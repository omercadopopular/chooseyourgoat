"""Add appearance-confirmed competition editions to the browser bundle."""
import csv, json, re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def end_year(value):
    years=re.findall(r'\d{4}',str(value))
    if not years: return None
    if len(years)>1: return int(years[-1])
    m=re.search(r'(\d{4})\s*[-/]\s*(\d{2})',str(value))
    return int(str(int(m.group(1))//100*100+int(m.group(2)))) if m else int(years[0])

def edition_for(name, iso):
    y=int(iso[:4]); month=int(iso[5:7]); low=name.lower()
    if 'world cup qualifier' in low:
        z=y
        while z%4!=2 or z<=y: z+=1
        return str(z)
    if 'european ch' in low and 'qual' in low:
        z=y
        while z%4!=0 or z<=y: z+=1
        return str(z)
    if 'nations league' in low:
        start=y if month>=7 else y-1
        return f'{start}-{str(start+1)[-2:]}'
    return str(y)

def norm(s): return re.sub(r'[^a-z0-9]','',s.lower())

def main():
    path=ROOT/'data/web_dataset.json'; data=json.loads(path.read_text())
    national=list(csv.DictReader((ROOT/'data/curated/national_team_appearances.csv').open()))
    for player in data['players']:
        entries={}
        def add(key, row):
            if key not in entries: entries[key]=row
            else:
                entries[key]['appearances']+=row['appearances']
                entries[key]['first_date']=min(entries[key]['first_date'],row['first_date'])
                entries[key]['last_date']=max(entries[key]['last_date'],row['last_date'])
        for o in player['observations']:
            if o.get('aggregate_only') or not o.get('appearances') or o['bucket']=='national_team_friendlies': continue
            if o['team_context']=='club':
                if o.get('competition_family')=='club_friendly' or o['competition_name'].lower() in {'other','unallocated domestic competition'}: continue
                edition=str(o['period']); key=('club',o['team'],o['competition_name'],edition)
                add(key,{'edition_id':'|'.join(key),'edition':edition,'year':end_year(edition),'team':o['team'],'competition_name':o['competition_name'],'bucket':o['bucket'],'appearances':o['appearances'],'bench_listings':0,'first_date':o['period_end'],'last_date':o['period_end'],'participation_basis':'appearance','won':False})
            elif o.get('source_granularity')=='calendar_year_bucket':
                edition=str(o['period']); key=('national',o['team'],o['competition_name'],edition)
                add(key,{'edition_id':'|'.join(key),'edition':edition,'year':end_year(edition),'team':o['team'],'competition_name':o['competition_name'],'bucket':o['bucket'],'appearances':o['appearances'],'bench_listings':0,'first_date':o['period_end'],'last_date':o['period_end'],'participation_basis':'appearance','won':False})
        groups=defaultdict(list)
        for r in national:
            if r['player_id']!=player['id'] or r['competition_name'].lower()=='friendly' or r['competition_family']=='national_team_friendlies': continue
            ed=edition_for(r['competition_name'],r['date_iso']); groups[(r['team'],r['competition_name'],ed,r['competition_family'])].append(r)
        for (team,name,edition,bucket),rows in groups.items():
            key=('national',team,name,edition)
            add(key,{'edition_id':'|'.join(key),'edition':edition,'year':end_year(edition),'team':team,'competition_name':name,'bucket':bucket,'appearances':len(rows),'bench_listings':0,'first_date':min(r['date_iso'] for r in rows),'last_date':max(r['date_iso'] for r in rows),'participation_basis':'appearance','won':False})
        unmatched=[]
        for title in player['titles']:
            ty=end_year(title['edition']); candidates=[e for e in entries.values() if e['bucket']==title['bucket'] and e['team']==title['team'] and e['year']==ty and not e['won']]
            exact=[e for e in candidates if norm(e['competition_name']) in norm(title['competition_name']) or norm(title['competition_name']) in norm(e['competition_name'])]
            choice=(exact or candidates)
            if choice:
                choice[0]['won']=True; choice[0]['title_name']=title['competition_name']
            else: unmatched.append(title)
        player['competitions']=sorted(entries.values(),key=lambda e:(e['last_date'],e['competition_name']))
        player['competitionCoverage']={'appearanceConfirmed':len(entries),'winsMatched':sum(e['won'] for e in entries.values()),'honoursUnmatched':len(unmatched),'benchConfirmed':0}
    data['meta']['competitionNotice']='Competition editions require a documented appearance or bench listing. Current edition denominators are appearance-confirmed; unmatched honours are excluded.'
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))

if __name__=='__main__': main()
