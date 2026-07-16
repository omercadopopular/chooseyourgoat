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
    "copadelgeneralisimo": "copadelrey",
    "seriea": "campeonatobrasileiro", "iiiligagroupi": "iiiliga",
    "centraleuropeaninternationalcup": "internationalcup", "internationalcup": "internationalcup",
}


def canonical_name(value):
    key = slug(value)
    return ALIASES.get(key, key)


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
    "messi": [("Argentina U20", "South American U-20 Championship", "2005", "national_team_other", 9), ("Argentina U20", "FIFA World Youth Championship", "2005", "national_team_other", 7), ("Argentina U23", "Olympic Games", "2008", "national_team_olympic", 5)],
    "ronaldinho": [("Brazil U17", "South American U-17 Championship", "1997", "national_team_other", 7), ("Brazil U17", "FIFA U-17 World Championship", "1997", "national_team_other", 6), ("Brazil U20", "South American U-20 Championship", "1999", "national_team_other", 9), ("Brazil U20", "FIFA World Youth Championship", "1999", "national_team_other", 5), ("Brazil U23", "CONMEBOL Pre-Olympic Tournament", "2000", "national_team_olympic", 7), ("Brazil U23", "Olympic Games", "2000", "national_team_olympic", 4), ("Brazil U23", "Olympic Games", "2008", "national_team_olympic", 6)],
    "maradona": [("Argentina U20", "South American U-20 Championship", "1977", "national_team_other", 3), ("Argentina U20", "South American U-20 Championship", "1979", "national_team_other", 5), ("Argentina U20", "FIFA World Youth Championship", "1979", "national_team_other", 6)],
}

BENCH = {
    "cristiano": [("Sporting CP", "Supertaça Cândido de Oliveira", "2002", "all_other_club", "https://en.wikipedia.org/wiki/2002_Superta%C3%A7a_C%C3%A2ndido_de_Oliveira")],
    "ronaldo": [("Brazil", "World Cup", "1994", "national_team_world_cup_finals", "https://pt.wikipedia.org/wiki/Final_da_Copa_do_Mundo_FIFA_de_1994")],
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
    year = end_year(edition)
    date = f"{year}-12-31"
    return {
        "edition_id": "|".join((context, team, name, str(edition))), "edition": str(edition), "year": year,
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
        player["coverage"]["titles"] = f"{len(player['titles'])} listed championship editions" + ("; participation reconciliation partial" if pid not in {"pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"} else "")
        entries = {}
        unresolved = []

        def add(entry):
            key = entry["edition_id"]
            if key in entries:
                entries[key]["appearances"] += entry["appearances"]
                entries[key]["bench_listings"] += entry["bench_listings"]
                entries[key]["participation_evidence"] += "; " + entry["participation_evidence"]
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
        expansion_groups = defaultdict(list)
        for observation in player["observations"]:
            if observation.get("source_granularity") != "calendar_year_from_match_ledger":
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
        unmatched = []
        for title in player["titles"]:
            title_name = canonical_name(title["competition_name"])
            candidates = [entry for entry in entries.values() if entry["team"] == title["team"] and canonical_name(entry["competition_name"]) == title_name and end_year(entry["edition"]) == end_year(title["edition"])]
            if candidates:
                candidates[0]["won"] = True
                candidates[0]["title_name"] = title["competition_name"]
                candidates[0]["honours_source_url"] = title.get("source_url", "")
            else:
                unmatched.append({"team": title["team"], "competition_name": title["competition_name"], "edition": title["edition"], "reason": "no documented appearance or bench listing in the named edition"})

        player["competitions"] = sorted(entries.values(), key=lambda entry: (entry["last_date"], entry["competition_name"]))
        player["competitionCoverage"] = {
            "appearanceConfirmed": sum(entry["appearances"] > 0 for entry in entries.values()),
            "benchConfirmed": sum(entry["bench_listings"] > 0 for entry in entries.values()),
            "otherParticipationConfirmed": sum(entry["participation_confirmed"] and not entry["appearances"] and not entry["bench_listings"] for entry in entries.values()),
            "winsMatched": sum(entry["won"] for entry in entries.values()),
            "honoursUnmatched": len(unmatched), "unmatchedHonours": unmatched,
            "unresolvedAggregateRows": unresolved,
            "reconciliationStatus": "partial" if pid not in {"pele", "messi", "cristiano", "ronaldo", "ronaldinho", "maradona"} else "complete",
        }

    data["meta"]["competitionNotice"] = "Competition editions are named and require a documented appearance or bench listing. Generic aggregate columns are resolved from cited footnotes or excluded; reported honours without participation evidence are not counted as wins."
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
