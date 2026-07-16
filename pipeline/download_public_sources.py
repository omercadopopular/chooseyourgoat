"""Download the public input snapshots used by the six-player build."""
from pathlib import Path
from urllib.request import Request, urlopen
import argparse

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data'/'raw'
WIKI='https://en.wikipedia.org/wiki/'
SOURCES={
    'pele.html':WIKI+'Pel%C3%A9',
    'messi.html':WIKI+'Lionel_Messi',
    'cristiano.html':WIKI+'List_of_career_achievements_by_Cristiano_Ronaldo',
    'ronaldo.html':WIKI+'Ronaldo_(Brazilian_footballer)',
    'ronaldinho.html':WIKI+'Ronaldinho',
    'maradona.html':WIKI+'Diego_Maradona',
    'pele_intl.html':WIKI+'List_of_international_goals_scored_by_Pel%C3%A9',
    'messi_intl.html':WIKI+'List_of_international_goals_scored_by_Lionel_Messi',
    'cristiano_intl.html':WIKI+'List_of_international_goals_scored_by_Cristiano_Ronaldo',
    'maradona_intl.html':'https://www.rsssf.org/miscellaneous/maradona-intl.html',
    'messi_rsssf_intl.html':'https://www.rsssf.org/miscellaneous/messi-intlg.html',
    'cristiano_rsssf_intl.html':'https://www.rsssf.org/miscellaneous/cronaldo-intlg.html',
    'ronaldo_rsssf_intl.html':'https://www.rsssf.org/miscellaneous/ronaldo-intlg.html',
    'ronaldinho_rsssf_intl.html':'https://www.rsssf.org/miscellaneous/ronaldinho-intlg.html',
    'pele_rsssf_intl.html':'https://www.rsssf.org/miscellaneous/pele-intlg.html',
    'pele_rsssf_data.html':'https://www.rsssf.org/players/ppeledata.html',
    'appearances.csv.gz':'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/appearances.csv.gz',
    'games.csv.gz':'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz',
    'competitions.csv.gz':'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/competitions.csv.gz',
}

def download(name,url,force=False):
    target=RAW/name
    if target.exists() and not force:
        print(f'cached  {name}')
        return
    request=Request(url,headers={'User-Agent':'ChooseYourGOAT research prototype (GitHub: omercadopopular/chooseyourgoat)'})
    with urlopen(request,timeout=120) as response, target.open('wb') as output:
        while chunk:=response.read(1024*1024): output.write(chunk)
    print(f'fetched {name} ({target.stat().st_size:,} bytes)')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--force',action='store_true',help='replace cached files')
    args=parser.parse_args()
    RAW.mkdir(parents=True,exist_ok=True)
    for name,url in SOURCES.items(): download(name,url,args.force)

if __name__=='__main__': main()
