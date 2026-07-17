"""Build a named, participation-confirmed competition-edition ledger.

Generic career-table columns (``National cup``, ``Continental`` and ``Other``)
are never emitted as editions.  They are resolved to named competitions using
the competition definitions and row footnotes on each player's cited career
statistics page.  A reported honour is counted only when that named edition
also has an appearance or an independently documented bench listing.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PLAYERS = {"pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"}


def end_year(value):
    years = re.findall(r"\d{4}", str(value))
    if not years:
        return None
    if len(years) > 1:
        return int(years[-1])
    match = re.search(r"(\d{4})\s*[-/]\s*(\d{2})", str(value))
    return int(str(int(match.group(1)) // 100 * 100 + int(match.group(2)))) if match else int(years[0])


def edition_for(name, iso):
    year, month = int(iso[:4]), int(iso[5:7])
    low = name.lower()
    if "world cup qualifier" in low:
        target = year
        while target % 4 != 2 or target <= year:
            target += 1
        return str(target)
    if ("european ch" in low or "continental championship" in low) and "qual" in low:
        target = year
        while target % 4 != 0 or target <= year:
            target += 1
        return str(target)
    if "nations league" in low:
        start = year if month >= 7 else year - 1
        return f"{start}-{str(start + 1)[-2:]}"
    return str(year)


def slug(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)


ALIASES = {
    "fifaworldcup": "worldcup", "worldcup": "worldcup",
    "uefaeuropeanchampionship": "europeanchampionship", "europeanchamp": "europeanchampionship",
    "europeanchampionshipfinals": "europeanchampionship",
    "europeanchampionship": "europeanchampionship",
    "uefanationsleague": "nationsleague", "nationsleague": "nationsleague",
    "fifaconfederationscup": "confederationscup", "confederationscup": "confederationscup",
    "confederationcup": "confederationscup",
    "confederarionscup": "confederationscup",
    "torneiroriosaopaulo": "riosaopaulo", "torneioriosaopaulo": "riosaopaulo", "riosaopaulo": "riosaopaulo",
    "campeonatobrasileiro": "campeonatobrasileiro", "campeonatobrasileiroseriea": "campeonatobrasileiro",
    "naslchampionship": "nasl", "northamericansoccerleague": "nasl",
    "footballleaguecup": "leaguecup", "eflcup": "leaguecup", "leaguecup": "leaguecup",
    "mlscup": "mlscup", "mlscupplayoffs": "mlscup",
    "olympicgames": "olympics", "summerolympics": "olympics",
    "finalissima": "conmeboluefa", "conmeboluefa": "conmeboluefa",
    "fifaworldyouthchampionship": "worldyouthchampionship",
    "summerolympicsgoldmedal": "olympics",
    "uefaeuropeanunder19championship": "europeanunder19championship",
    "u20southamericanchampionship": "southamericanunder20championship",
    "southamericanu20championship": "southamericanunder20championship",
    "copadelgeneralisimo": "copadelrey",
    "seriea": "campeonatobrasileiro", "iiiligagroupi": "iiiliga",
    "centraleuropeaninternationalcup": "internationalcup", "internationalcup": "internationalcup",
}


def canonical_name(value):
    key = slug(value)
    return ALIASES.get(key, key)


CANONICAL_DISPLAY = {
    "worldcup": "FIFA World Cup", "europeanchampionship": "UEFA European Championship",
    "nationsleague": "UEFA Nations League", "confederationscup": "FIFA Confederations Cup",
    "olympics": "Olympic Games", "worldyouthchampionship": "FIFA World Youth Championship",
    "europeanunder19championship": "UEFA European Under-19 Championship",
    "southamericanunder20championship": "South American U-20 Championship",
    "riosaopaulo": "Torneio Rio-São Paulo", "campeonatobrasileiro": "Campeonato Brasileiro Série A",
    "nasl": "North American Soccer League", "leaguecup": "Football League Cup",
    "mlscup": "MLS Cup", "conmeboluefa": "Finalissima", "copadelrey": "Copa del Rey",
    "internationalcup": "Central European International Cup",
}


def canonical_display_name(value):
    return CANONICAL_DISPLAY.get(canonical_name(value), str(value).strip())


TEAM_ALIASES = {
    "psg": "Paris Saint-Germain", "parissaintgermain": "Paris Saint-Germain",
    "psveindhoven": "PSV", "psv": "PSV", "americarj": "America-RJ",
    "americafootballclubrj": "America-RJ", "alsadd": "Al-Sadd (loan)",
}


def canonical_team_name(value):
    return TEAM_ALIASES.get(slug(value), str(value).strip())


PRIMARY_CUP = {
    "Barcelona": "Copa del Rey", "Paris Saint-Germain": "Coupe de France",
    "Inter Miami": "U.S. Open Cup", "Sporting CP": "Taça de Portugal",
    "Manchester United": "FA Cup", "Real Madrid": "Copa del Rey",
    "Juventus": "Coppa Italia", "Al-Nassr": "King Cup",
    "PSV": "KNVB Cup", "Inter Milan": "Coppa Italia",
    "Corinthians": "Copa do Brasil", "Napoli": "Coppa Italia",
    "Sevilla": "Copa del Rey",
    "Monaco": "Coupe de France", "Borussia Dortmund": "DFB-Pokal",
    "Manchester City": "FA Cup", "Liverpool": "FA Cup",
    "Ajax": "KNVB Cup", "Feyenoord": "KNVB Cup",
    "Vicenza": "Coppa Italia", "Fiorentina": "Coppa Italia",
    "Bologna": "Coppa Italia", "Brescia": "Coppa Italia",
    "Bayern Munich": "DFB-Pokal", "Lech Poznań": "Polish Cup",
    "Znicz Pruszków": "Polish Cup", "Legia Warsaw II": "Polish Cup",
    "Groningen": "KNVB Cup", "Nacional": "Copa AUF Uruguay",
    "Vasco da Gama": "Copa do Brasil", "Flamengo": "Copa do Brasil",
    "Fluminense": "Copa do Brasil", "Valencia": "Copa del Rey",
    "Milan": "Coppa Italia",
    "Santos": "Copa do Brasil", "Red Bull Salzburg": "Austrian Cup",
    "Molde": "Norwegian Cup", "Atlético Madrid": "Copa del Rey",
    "Grêmio": "Copa do Brasil", "Kispest/Budapesti Honvéd SE": "Hungarian Cup",
    "Miami FC": "U.S. Open Cup",
}

RONALDINHO_CUP = {
    "Grêmio": "Copa do Brasil", "Barcelona": "Copa del Rey",
    "AC Milan": "Coppa Italia", "Flamengo": "Copa do Brasil",
    "Atlético Mineiro": "Copa do Brasil", "Querétaro": "Copa MX",
    "Fluminense": "Copa do Brasil",
}


def continental(player, team, season, apps):
    """Return (name, edition, bucket, appearances, evidence note) rows."""
    standard = "continental_federation_cup"
    if player == "messi":
        name = "CONCACAF Champions Cup" if team == "Inter Miami" else "UEFA Champions League"
    elif player == "cristiano":
        if team == "Sporting CP":
            return [("UEFA Champions League", season, standard, 1, "one qualifying-round appearance"),
                    ("UEFA Cup", season, standard, 2, "two appearances")]
        if team == "Al-Nassr":
            name = "AFC Champions League" if season == "2023-24" else "AFC Champions League Elite"
        else:
            name = "UEFA Champions League"
    elif player == "ronaldo":
        if team == "Cruzeiro": name = "Supercopa Libertadores" if season == "1993" else "Copa Libertadores"
        elif team == "PSV": name = "UEFA Cup"
        elif team == "Barcelona": name = "UEFA Cup Winners' Cup"
        elif team == "Inter Milan": name = "UEFA Cup" if season in {"1997-98", "2001-02"} else "UEFA Champions League"
        elif team == "Real Madrid": name = "UEFA Champions League"
        elif team == "Corinthians": name = "Copa Libertadores"
        else: return []
    elif player == "ronaldinho":
        if team == "Grêmio" and season == "1998":
            return [("Copa Libertadores", season, standard, 10, "ten appearances"),
                    ("Copa Mercosur", season, standard, 5, "five appearances")]
        if team == "Grêmio": name = "Copa Mercosur"
        elif team == "Paris Saint-Germain": name = "UEFA Cup"
        elif team == "Barcelona": name = "UEFA Cup" if season == "2003-04" else "UEFA Champions League"
        elif team == "AC Milan": name = "UEFA Cup" if season == "2008-09" else "UEFA Champions League"
        elif team == "Flamengo": name = "Copa Sudamericana" if season == "2011" else "Copa Libertadores"
        elif team == "Atlético Mineiro": name = "Copa Libertadores"
        else: return []
    elif player == "maradona":
        if team == "Barcelona": name = "European Cup Winners' Cup"
        elif team == "Napoli": name = "European Cup" if season in {"1987-88", "1990-91"} else "UEFA Cup"
        else: return []
    elif player == "mbappe":
        name = "UEFA Champions League"
    elif player == "haaland":
        name = "UEFA Europa League" if team == "Molde" else "UEFA Champions League"
    elif player == "cruyff":
        if team in {"Ajax", "Feyenoord"}: name = "European Cup"
        elif team == "Barcelona": name = "UEFA Cup"
        else: return []
    elif player == "baggio":
        name = "UEFA Cup" if team in {"Fiorentina", "Juventus", "Inter Milan"} else "UEFA Champions League"
    elif player == "neymar":
        name = "Copa Libertadores" if team == "Santos" else "UEFA Champions League"
    elif player == "lewandowski":
        name = "UEFA Europa League" if team in {"Lech Poznań", "Borussia Dortmund"} and season in {"2008-09", "2010-11"} else "UEFA Champions League"
    elif player == "suarez":
        name = "UEFA Europa League" if team in {"Ajax", "Liverpool"} and season in {"2009-10", "2010-11", "2012-13"} else "UEFA Champions League"
    elif player == "puskas":
        name = "European Cup"
    elif player == "romario":
        if team == "Flamengo" and season == "1999": name = "Copa Mercosur"
        elif team == "Vasco da Gama" and season == "2000": name = "Copa Mercosur"
        elif team in {"Vasco da Gama", "Flamengo", "Fluminense"}: name = "Copa Libertadores"
        elif team == "PSV": name = "European Cup"
        elif team == "Barcelona": name = "UEFA Champions League"
        else: return []
    else:
        return []
    return [(name, season, standard, apps, "career-statistics competition column/footnote")]


# Exact decompositions of aggregate ``Other`` cells.  The appearance counts and
# competition names are transcribed from the cited row footnotes.
OTHER = {
    ("messi", "Barcelona", "2006-07"): [("UEFA Super Cup", "2006", "continental_federation_cup", 1), ("Supercopa de España", "2006", "all_other_club", 2)],
    ("messi", "Barcelona", "2009-10"): [("UEFA Super Cup", "2009", "continental_federation_cup", 1), ("Supercopa de España", "2009", "all_other_club", 1), ("FIFA Club World Cup", "2009", "intercontinental_federation_cup", 2)],
    ("messi", "Barcelona", "2010-11"): [("Supercopa de España", "2010", "all_other_club", 2)],
    ("messi", "Barcelona", "2011-12"): [("UEFA Super Cup", "2011", "continental_federation_cup", 1), ("Supercopa de España", "2011", "all_other_club", 2), ("FIFA Club World Cup", "2011", "intercontinental_federation_cup", 2)],
    ("messi", "Barcelona", "2012-13"): [("Supercopa de España", "2012", "all_other_club", 2)],
    ("messi", "Barcelona", "2013-14"): [("Supercopa de España", "2013", "all_other_club", 2)],
    ("messi", "Barcelona", "2015-16"): [("UEFA Super Cup", "2015", "continental_federation_cup", 1), ("Supercopa de España", "2015", "all_other_club", 2), ("FIFA Club World Cup", "2015", "intercontinental_federation_cup", 1)],
    ("messi", "Barcelona", "2016-17"): [("Supercopa de España", "2016", "all_other_club", 2)],
    ("messi", "Barcelona", "2017-18"): [("Supercopa de España", "2017", "all_other_club", 2)],
    ("messi", "Barcelona", "2018-19"): [("Supercopa de España", "2018", "all_other_club", 1)],
    ("messi", "Barcelona", "2019-20"): [("Supercopa de España", "2020", "all_other_club", 1)],
    ("messi", "Barcelona", "2020-21"): [("Supercopa de España", "2021", "all_other_club", 1)],
    ("messi", "Paris Saint-Germain", "2022-23"): [("Trophée des Champions", "2022", "all_other_club", 1)],
    ("messi", "Inter Miami", "2023"): [("Leagues Cup", "2023", "all_other_club", 7)],
    ("messi", "Inter Miami", "2024"): [("MLS Cup playoffs", "2024", "national_league", 3)],
    ("messi", "Inter Miami", "2025"): [("FIFA Club World Cup", "2025", "intercontinental_federation_cup", 4), ("Leagues Cup", "2025", "all_other_club", 4), ("MLS Cup playoffs", "2025", "national_league", 6)],
    ("cristiano", "Manchester United", "2007-08"): [("FA Community Shield", "2007", "all_other_club", 1)],
    ("cristiano", "Manchester United", "2008-09"): [("FIFA Club World Cup", "2008", "intercontinental_federation_cup", 2)],
    ("cristiano", "Real Madrid", "2011-12"): [("Supercopa de España", "2011", "all_other_club", 2)],
    ("cristiano", "Real Madrid", "2012-13"): [("Supercopa de España", "2012", "all_other_club", 2)],
    ("cristiano", "Real Madrid", "2014-15"): [("UEFA Super Cup", "2014", "continental_federation_cup", 1), ("Supercopa de España", "2014", "all_other_club", 2), ("FIFA Club World Cup", "2014", "intercontinental_federation_cup", 2)],
    ("cristiano", "Real Madrid", "2016-17"): [("FIFA Club World Cup", "2016", "intercontinental_federation_cup", 2)],
    ("cristiano", "Real Madrid", "2017-18"): [("UEFA Super Cup", "2017", "continental_federation_cup", 1), ("Supercopa de España", "2017", "all_other_club", 1), ("FIFA Club World Cup", "2017", "intercontinental_federation_cup", 2)],
    ("cristiano", "Juventus", "2018-19"): [("Supercoppa Italiana", "2018", "all_other_club", 1)],
    ("cristiano", "Juventus", "2019-20"): [("Supercoppa Italiana", "2019", "all_other_club", 1)],
    ("cristiano", "Juventus", "2020-21"): [("Supercoppa Italiana", "2020", "all_other_club", 1)],
    ("cristiano", "Al-Nassr", "2022-23"): [("Saudi Super Cup", "2023", "all_other_club", 1)],
    ("cristiano", "Al-Nassr", "2023-24"): [("Arab Club Champions Cup", "2023", "continental_federation_cup", 6), ("Saudi Super Cup", "2024", "all_other_club", 1)],
    ("cristiano", "Al-Nassr", "2024-25"): [("Saudi Super Cup", "2024", "all_other_club", 2)],
    ("ronaldo", "Cruzeiro", "1993"): [("Copa do Brasil", "1993", "all_other_club", 1)],
    ("ronaldo", "Barcelona", "1996-97"): [("Supercopa de España", "1996", "all_other_club", 1)],
    ("ronaldo", "Inter Milan", "1998-99"): [("Serie A UEFA Cup qualification", "1999", "all_other_club", 1)],
    ("ronaldo", "Real Madrid", "2002-03"): [("Intercontinental Cup", "2002", "intercontinental_federation_cup", 1)],
    ("ronaldo", "Real Madrid", "2003-04"): [("Supercopa de España", "2003", "all_other_club", 2)],
    ("ronaldinho", "Grêmio", "1999"): [("Copa Sul", "1999", "regional_league", 4), ("Seletiva Libertadores", "1999", "all_other_club", 2)],
    ("ronaldinho", "Grêmio", "2001"): [("Copa Sul-Minas", "2001", "regional_league", 3)],
    ("ronaldinho", "Barcelona", "2005-06"): [("Supercopa de España", "2005", "all_other_club", 2)],
    ("ronaldinho", "Barcelona", "2006-07"): [("Supercopa de España", "2006", "all_other_club", 2), ("UEFA Super Cup", "2006", "continental_federation_cup", 1), ("FIFA Club World Cup", "2006", "intercontinental_federation_cup", 2)],
    ("ronaldinho", "Atlético Mineiro", "2013"): [("FIFA Club World Cup", "2013", "intercontinental_federation_cup", 2)],
    ("ronaldinho", "Atlético Mineiro", "2014"): [("Recopa Sudamericana", "2014", "continental_federation_cup", 2)],
    ("maradona", "Barcelona", "1982-83"): [("Copa de la Liga", "1983", "all_other_club", 6)],
    ("maradona", "Napoli", "1990-91"): [("Supercoppa Italiana", "1990", "all_other_club", 1)],
    ("maradona", "Boca Juniors", "1996-97"): [("Supercopa Libertadores", "1997", "continental_federation_cup", 1)],
}

YOUTH = {
    "messi": [("Argentina U20", "South American U-20 Championship", "2005", "national_team_youth", 9), ("Argentina U20", "FIFA World Youth Championship", "2005", "national_team_youth", 7), ("Argentina U23", "Olympic Games", "2008", "national_team_olympic", 5)],
    "ronaldinho": [("Brazil U17", "South American U-17 Championship", "1997", "national_team_youth", 7), ("Brazil U17", "FIFA U-17 World Championship", "1997", "national_team_youth", 6), ("Brazil U20", "South American U-20 Championship", "1999", "national_team_youth", 9), ("Brazil U20", "FIFA World Youth Championship", "1999", "national_team_youth", 5), ("Brazil U23", "CONMEBOL Pre-Olympic Tournament", "2000", "national_team_olympic", 7), ("Brazil U23", "Olympic Games", "2000", "national_team_olympic", 4), ("Brazil U23", "Olympic Games", "2008", "national_team_olympic", 6)],
    "maradona": [("Argentina U20", "South American U-20 Championship", "1977", "national_team_youth", 3), ("Argentina U20", "South American U-20 Championship", "1979", "national_team_youth", 5), ("Argentina U20", "FIFA World Youth Championship", "1979", "national_team_youth", 6)],
}

BENCH = {
    "cristiano": [("Sporting CP", "Supertaça Cândido de Oliveira", "2002", "all_other_club", "https://en.wikipedia.org/wiki/2002_Superta%C3%A7a_C%C3%A2ndido_de_Oliveira")],
    "ronaldo": [("Brazil", "World Cup", "1994", "national_team_world_cup_finals", "https://pt.wikipedia.org/wiki/Final_da_Copa_do_Mundo_FIFA_de_1994")],
}

# Participation evidence that is more granular than the cached career-table
# columns. Modern entries are transcribed from the cached public Transfermarkt
# match ledgers; historical entries cite a public match/tournament record and
# use the minimum documented appearance when a full ledger is unavailable.
HONOUR_PARTICIPATION = {
    "ronaldinho": [("club", "Paris Saint-Germain", "UEFA Intertoto Cup", "2001", "continental_federation_cup", 1, "https://en.wikipedia.org/wiki/2001_UEFA_Intertoto_Cup", "documented appearance and two goals in PSG's first leg against Rapid Wien")],
    "mbappe": [
        ("national", "France U19", "UEFA European Under-19 Championship", "2016", "national_team_youth", 5, "https://tmapi.transfermarkt.technology/player/342229/performance-game", "five match-ledger appearances"),
        ("club", "Paris Saint-Germain", "Trophée des Champions", "2019", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/342229/performance-game", "match-ledger appearance"),
        ("club", "Paris Saint-Germain", "Trophée des Champions", "2020", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/342229/performance-game", "played 13 January 2021 in the 2020 edition"),
        ("club", "Paris Saint-Germain", "Trophée des Champions", "2023", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/342229/performance-game", "played 3 January 2024 in the 2023 edition"),
        ("club", "Real Madrid", "FIFA Intercontinental Cup", "2024", "intercontinental_federation_cup", 1, "https://tmapi.transfermarkt.technology/player/342229/performance-game", "match-ledger appearance"),
        ("club", "Real Madrid", "UEFA Super Cup", "2024", "continental_federation_cup", 1, "https://tmapi.transfermarkt.technology/player/342229/performance-game", "match-ledger appearance"),
    ],
    "haaland": [
        ("club", "Manchester City", "UEFA Super Cup", "2023", "continental_federation_cup", 1, "https://tmapi.transfermarkt.technology/player/418560/performance-game", "match-ledger appearance"),
        ("club", "Manchester City", "FA Community Shield", "2024", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/418560/performance-game", "match-ledger appearance"),
    ],
    "cruyff": [
        ("club", "Ajax", "European Super Cup", "1972", "continental_federation_cup", 1, "https://en.wikipedia.org/wiki/1972_European_Super_Cup", "documented appearance in the two-legged edition"),
        ("club", "Ajax", "Intercontinental Cup", "1972", "intercontinental_federation_cup", 1, "https://en.wikipedia.org/wiki/1972_Intercontinental_Cup", "documented appearance in the two-legged edition"),
    ],
    "neymar": [
        ("national", "Brazil U20", "South American U-20 Championship", "2011", "national_team_youth", 7, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "seven match-ledger appearances"),
        ("club", "Santos", "Recopa Sudamericana", "2012", "continental_federation_cup", 2, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "two match-ledger appearances"),
        ("club", "Barcelona", "Supercopa de España", "2013", "all_other_club", 2, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "two match-ledger appearances"),
        ("club", "Barcelona", "FIFA Club World Cup", "2015", "intercontinental_federation_cup", 1, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "match-ledger appearance"),
        ("national", "Brazil U23", "Olympic Games", "2016", "national_team_olympic", 6, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "six match-ledger appearances"),
        ("club", "Paris Saint-Germain", "Trophée des Champions", "2018", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "match-ledger appearance"),
        ("club", "Paris Saint-Germain", "Trophée des Champions", "2020", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "played 13 January 2021 in the 2020 edition"),
        ("club", "Paris Saint-Germain", "Trophée des Champions", "2022", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/68290/performance-game", "match-ledger appearance"),
    ],
    "lewandowski": [
        ("club", "Lech Poznań", "Polish Super Cup", "2009", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/38253/performance-game", "match-ledger appearance"),
        *[("club", team, "DFL-Supercup", str(year), "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/38253/performance-game", "match-ledger appearance") for team, year in [("Borussia Dortmund", 2013), ("Bayern Munich", 2016), ("Bayern Munich", 2017), ("Bayern Munich", 2018), ("Bayern Munich", 2020), ("Bayern Munich", 2021)]],
        ("club", "Bayern Munich", "FIFA Club World Cup", "2020", "intercontinental_federation_cup", 2, "https://tmapi.transfermarkt.technology/player/38253/performance-game", "two February 2021 match-ledger appearances in the 2020 edition"),
        ("club", "Bayern Munich", "UEFA Super Cup", "2020", "continental_federation_cup", 1, "https://tmapi.transfermarkt.technology/player/38253/performance-game", "match-ledger appearance"),
        ("club", "Barcelona", "Supercopa de España", "2023", "all_other_club", 2, "https://tmapi.transfermarkt.technology/player/38253/performance-game", "two match-ledger appearances"),
        ("club", "Barcelona", "Supercopa de España", "2025", "all_other_club", 2, "https://tmapi.transfermarkt.technology/player/38253/performance-game", "two match-ledger appearances"),
    ],
    "suarez": [
        ("club", "Barcelona", "FIFA Club World Cup", "2015", "intercontinental_federation_cup", 2, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "two match-ledger appearances"),
        ("club", "Barcelona", "UEFA Super Cup", "2015", "continental_federation_cup", 1, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "match-ledger appearance"),
        ("club", "Barcelona", "Supercopa de España", "2016", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "match-ledger appearance"),
        ("club", "Barcelona", "Supercopa de España", "2018", "all_other_club", 1, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "match-ledger appearance"),
        ("club", "Grêmio", "Campeonato Gaúcho", "2023", "regional_league", 12, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "twelve state-championship match-ledger appearances"),
        ("club", "Grêmio", "Recopa Gaúcha", "2023", "regional_league", 1, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "match-ledger appearance"),
        ("club", "Inter Miami", "Supporters' Shield", "2024", "national_league", 27, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "27 regular-season match-ledger appearances"),
        ("club", "Inter Miami", "MLS Cup", "2025", "national_league", 4, "https://tmapi.transfermarkt.technology/player/44352/performance-game", "four playoff match-ledger appearances"),
    ],
    "puskas": [("club", "Real Madrid", "Intercontinental Cup", "1960", "intercontinental_federation_cup", 1, "https://en.wikipedia.org/wiki/1960_Intercontinental_Cup", "documented appearance and two goals in the second leg")],
    "romario": [
        ("national", "Brazil Youth", "U-20 South American Championship", "1985", "national_team_youth", 1, "https://en.wikipedia.org/wiki/Rom%C3%A1rio", "tournament top-scorer record confirms participation"),
        ("club", "PSV", "Dutch Super Cup", "1992", "all_other_club", 1, "https://en.wikipedia.org/wiki/Rom%C3%A1rio", "career-table Other appearance allocated to the named edition"),
        ("club", "Barcelona", "Supercopa de España", "1994", "all_other_club", 2, "https://en.wikipedia.org/wiki/Rom%C3%A1rio", "two career-table Other appearances allocated to the named edition"),
    ],
}

EXCLUDED_HONOURS = {
    ("pele", "Santos", "Torneio Rio-São Paulo", "1966"): "source ledger shows no participation; retained out of the win count",
    ("cruyff", "Netherlands", "Tournoi de Paris", "1978"): "friendly invitational, not a qualifying competition edition",
    ("romario", "Al-Sadd (loan)", "Qatar Crown Prince Cup", "2003"): "no documented appearance or bench listing located",
}


def resolve_club(player_id, observation):
    team, season, name, apps = observation["team"], str(observation["period"]), observation["competition_name"], int(observation["appearances"])
    low = name.lower()
    if low == "unallocated domestic competition":
        return None
    if low == "other":
        rows = OTHER.get((player_id, team, season), [])
        if player_id == "pele" and team == "New York Cosmos":
            return None  # the source identifies these as exhibition/friendly matches
        return [(n, e, b, a, "career-statistics Other-cell footnote") for n, e, b, a in rows]
    if low == "postseason":
        return [("North American Soccer League", season, "national_league", apps, "NASL postseason appearances")]
    if low == "league":
        return [("North American Soccer League", season, "national_league", apps, "NASL regular-season appearances")]
    if low in {"national cup", "national cup[a]"}:
        resolved = PRIMARY_CUP.get(team)
        return [(resolved, season, "all_other_club", apps, "career-statistics national-cup definition")] if resolved else []
    if low == "league cup":
        resolved = "Coupe de la Ligue" if team in {"Monaco", "Paris Saint-Germain"} else "Football League Cup" if team in {"Manchester City", "Liverpool", "Manchester United"} else None
        return [(resolved, season, "all_other_club", apps, "career-statistics league-cup definition")] if resolved else []
    if low == "cup":
        if team == "Paris Saint-Germain":
            splits = {"2001-02": [("Coupe de la Ligue", 4), ("Coupe de France", 2)], "2002-03": [("Coupe de la Ligue", 1), ("Coupe de France", 5)]}
            return [(n, season, "all_other_club", a, "career-statistics cup-cell footnote") for n, a in splits.get(season, [])]
        resolved = RONALDINHO_CUP.get(team) or PRIMARY_CUP.get(team)
        return [(resolved, season, "all_other_club", apps, "career-statistics cup definition")] if resolved else []
    if low in {"continental", "europe"}:
        return continental(player_id, team, season, apps)
    if low == "state league":
        if player_id == "romario" and team == "America-RJ" and season == "2009":
            return [("Campeonato Carioca Second Division", season, "lower_division_club", apps, "career-statistics state-league row identifies the lower-division edition")]
        resolved = ({"Cruzeiro": "Campeonato Mineiro", "Atlético Mineiro": "Campeonato Mineiro",
                     "Santos": "Campeonato Paulista", "Corinthians": "Campeonato Paulista",
                     "Vasco da Gama": "Campeonato Carioca", "Flamengo": "Campeonato Carioca",
                     "Fluminense": "Campeonato Carioca", "America-RJ": "Campeonato Carioca"}).get(team)
        return [(resolved, season, "regional_league", apps, "career-statistics state-league definition")] if resolved else []
    if low == "regional league":
        resolved = {"Grêmio": "Campeonato Gaúcho", "Flamengo": "Campeonato Carioca", "Atlético Mineiro": "Campeonato Mineiro"}.get(team)
        return [(resolved, season, "regional_league", apps, "career-statistics regional-league footnote")] if resolved else []
    if player_id == "pele" and name == "Intercontinental Cup" and season == "1968":
        return [("Intercontinental Supercup", season, "intercontinental_federation_cup", apps, "1968 competition edition")]
    if player_id == "messi" and name == "MLS":
        return [("Supporters' Shield", season, "national_league", apps, "MLS regular-season participation")]
    return [(name, season, observation["bucket"], apps, "named career-statistics column")]


def make_entry(context, team, name, edition, bucket, appearances, bench, source_url, basis, note):
    team = canonical_team_name(team)
    name = canonical_display_name(name)
    year = end_year(edition)
    date = f"{year}-12-31"
    return {
        "edition_id": "|".join((context, slug(team), canonical_name(name), str(edition))), "edition": str(edition), "year": year,
        "team": team, "competition_name": name, "bucket": bucket, "appearances": appearances,
        "bench_listings": bench, "first_date": date, "last_date": date,
        "participation_confirmed": bool(appearances or bench),
        "participation_basis": basis, "participation_source_url": source_url,
        "participation_evidence": note, "won": False,
    }


def main():
    path = ROOT / "data/web_dataset.json"
    data = json.loads(path.read_text())
    national = list(csv.DictReader((ROOT / "data/curated/national_team_appearances.csv").open()))
    source_urls = {row["player_id"]: row["source_url"] for row in csv.DictReader((ROOT / "data/curated/season_competition.csv").open())}

    for player in data["players"]:
        pid = player["id"]
        if pid == "ronaldo" and not any(title["team"] == "Cruzeiro" and title["competition_name"] == "Copa do Brasil" and str(title["edition"]) == "1993" for title in player["titles"]):
            player["titles"].append({"year": 1993, "date": "1993-12-31", "age": 17.285, "bucket": "all_other_club", "competition_name": "Copa do Brasil", "team": "Cruzeiro", "edition": "1993"})
            player["titles"].sort(key=lambda title: title["date"])
        excluded_honours=[]
        retained_titles=[]
        for title in player["titles"]:
            key=(pid,title["team"],title["competition_name"],str(title["edition"]))
            if key in EXCLUDED_HONOURS:
                excluded_honours.append({**title,"reason":EXCLUDED_HONOURS[key]})
            else:
                retained_titles.append(title)
        player["titles"]=retained_titles
        entries = {}
        unresolved = []

        def add(entry):
            key = entry["edition_id"]
            if key in entries:
                entries[key]["appearances"] += entry["appearances"]
                entries[key]["bench_listings"] += entry["bench_listings"]
                entries[key]["participation_evidence"] += "; " + entry["participation_evidence"]
                entries[key]["first_date"] = min(entries[key]["first_date"], entry["first_date"])
                entries[key]["last_date"] = max(entries[key]["last_date"], entry["last_date"])
                entries[key]["participation_confirmed"] = bool(entries[key]["appearances"] or entries[key]["bench_listings"])
            else:
                entries[key] = entry

        for observation in player["observations"]:
            if observation.get("aggregate_only") or not observation.get("appearances") or observation["team_context"] != "club":
                continue
            if observation.get("competition_family") == "club_friendly":
                continue
            resolved = resolve_club(pid, observation)
            if resolved is None:
                continue
            if not resolved:
                unresolved.append({"team": observation["team"], "edition": observation["period"], "source_label": observation["competition_name"], "appearances": observation["appearances"]})
            for name, edition, bucket, appearances, note in resolved:
                if observation.get("bucket") == "lower_division_club": bucket = "lower_division_club"
                add(make_entry("club", observation["team"], name, edition, bucket, appearances, 0, observation.get("source_url") or source_urls.get(pid, ""), "appearance", note))

        groups = defaultdict(list)
        for row in national:
            if row["player_id"] != pid or row["competition_name"].lower() == "friendly" or row["competition_family"] == "national_team_friendlies":
                continue
            edition = edition_for(row["competition_name"], row["date_iso"])
            groups[(row["team"], row["competition_name"], edition, row["competition_family"])].append(row)
        for (team, name, edition, bucket), rows in groups.items():
            entry = make_entry("national", team, name, edition, bucket, len(rows), 0, rows[0]["source_url"], "appearance", "RSSSF match-level appearance ledger")
            entry["first_date"] = min(row["date_iso"] for row in rows)
            entry["last_date"] = max(row["date_iso"] for row in rows)
            add(entry)

        # The expansion's chart observations are generated from complete
        # match ledgers and retain each group's first/last match date. Convert
        # those non-friendly groups into the same named edition ledger used by
        # the canonical six.
        # The canonical six already have exact RSSSF rows above. Re-reading
        # their chart aggregates here duplicates national editions, and the
        # previous unconstrained loop also admitted Pelé's club friendly/tour
        # calendar rows as competition editions. This path belongs only to the
        # expansion's national-team match ledgers.
        if pid not in CANONICAL_PLAYERS:
            expansion_groups = defaultdict(list)
            for observation in player["observations"]:
                if observation.get("source_granularity") != "calendar_year_from_match_ledger":
                    continue
                if observation.get("team_context") != "national_team":
                    continue
                if observation["bucket"] == "national_team_friendlies":
                    continue
                edition = edition_for(observation["competition_name"], observation.get("first_date", observation["period_end"]))
                expansion_groups[(observation["team"], observation["competition_name"], edition, observation["bucket"])].append(observation)
            for (team, name, edition, bucket), rows in expansion_groups.items():
                entry = make_entry("national", team, name, edition, bucket, sum(int(row["appearances"]) for row in rows), 0, rows[0].get("source_url", ""), "appearance", "complete public match ledger")
                entry["first_date"] = min(row.get("first_date", row["period_end"]) for row in rows)
                entry["last_date"] = max(row.get("last_date", row["period_end"]) for row in rows)
                add(entry)

        for team, name, edition, bucket, apps in YOUTH.get(pid, []):
            add(make_entry("national", team, name, edition, bucket, apps, 0, source_urls.get(pid, ""), "appearance", "career-statistics youth competition footnote"))
        for team, name, edition, bucket, url in BENCH.get(pid, []):
            add(make_entry("national" if team in {"Brazil", "Argentina", "Portugal"} else "club", team, name, edition, bucket, 0, 1, url, "bench", "documented match-day substitute/squad listing"))
        for context, team, name, edition, bucket, apps, url, note in HONOUR_PARTICIPATION.get(pid, []):
            add(make_entry(context, team, name, edition, bucket, apps, 0, url, "appearance", note))
        unmatched = []
        for title in player["titles"]:
            title_name = canonical_name(title["competition_name"])
            title_team = canonical_team_name(title["team"])
            candidates = [entry for entry in entries.values() if entry["team"] == title_team and canonical_name(entry["competition_name"]) == title_name and end_year(entry["edition"]) == end_year(title["edition"])]
            if candidates:
                candidates[0]["won"] = True
                candidates[0]["title_name"] = title["competition_name"]
                candidates[0]["honours_source_url"] = title.get("source_url", "")
            else:
                unmatched.append({"team": title["team"], "competition_name": title["competition_name"], "edition": title["edition"], "reason": "no documented appearance or bench listing in the named edition"})

        status = "complete" if not unmatched and not unresolved else "partial"
        player["competitions"] = sorted(entries.values(), key=lambda entry: (entry["last_date"], entry["competition_name"]))
        player["competitionCoverage"] = {
            "appearanceConfirmed": sum(entry["appearances"] > 0 for entry in entries.values()),
            "benchConfirmed": sum(entry["bench_listings"] > 0 for entry in entries.values()),
            "otherParticipationConfirmed": sum(entry["participation_confirmed"] and not entry["appearances"] and not entry["bench_listings"] for entry in entries.values()),
            "winsMatched": sum(entry["won"] for entry in entries.values()),
            "honoursUnmatched": len(unmatched), "unmatchedHonours": unmatched,
            "excludedHonours": excluded_honours,
            "unresolvedAggregateRows": unresolved,
            "reconciliationStatus": status,
        }
        player["coverage"]["titles"] = f"{len(player['titles'])} listed championship editions; participation reconciliation {status}"

    data["meta"]["competitionNotice"] = "Competition editions are named and require a documented appearance or bench listing. Generic aggregate columns are resolved from cited footnotes or excluded; reported honours without participation evidence are not counted as wins."
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
