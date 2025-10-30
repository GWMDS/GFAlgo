# Giffler-Thompson-Algorithmus (super einfach & vollständig erklärt)
# Regel: KOZ = Kürzeste Operationszeit

import pandas as pd  # Für die tabellarische Ausgabe am Ende


# ---------------------------------------------------------------
# 1️⃣ Eingabedaten
# ---------------------------------------------------------------

# Jeder Job besteht aus einer Liste von Operationen (Maschine, Bearbeitungszeit)
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],
    2: [(2, 2), (3, 3), (1, 5)],
    3: [(3, 4), (1, 2), (2, 3)]
}

# Maschinenbelegung: wann ist jede Maschine wieder frei?
maschinen_ende = {1: 0, 2: 0, 3: 0}

# Startmenge S: enthält die erste Operation jedes Jobs
S = []
for job in jobs:
    # Die erste Operation jedes Jobs hat den Index 0
    S.append((job, 0))

# Startzeit für jede Operation (t(o)) → alle beginnen mit 0
t = {}
for job in jobs:
    anzahl_ops = len(jobs[job])  # z. B. 3 Operationen
    for i in range(anzahl_ops):
        t[(job, i)] = 0

# Speichere Start- und Endzeiten
startzeiten = {}
endzeiten = {}


# ---------------------------------------------------------------
# 2️⃣ Hauptschleife des Algorithmus
# ---------------------------------------------------------------
while len(S) > 0:  # Solange es noch einplanbare Operationen gibt

    # -------------------------------------
    # Schritt 1: Berechne Fertigstellungszeiten d(o)
    # -------------------------------------
    d = {}  # Leeres Dictionary für d(o)

    # Für jede Operation in der aktuellen Menge S:
    for job, i in S:
        maschine, dauer = jobs[job][i]  # Hole Maschine und Bearbeitungszeit
        # Startzeit hängt davon ab, wann der Job oder die Maschine frei ist
        startzeit = max(t[(job, i)], maschinen_ende[maschine])
        # Fertigstellungszeit = Start + Bearbeitungszeit
        d[(job, i)] = startzeit + dauer

    # -------------------------------------
    # Schritt 2: Finde die Operation mit der kleinsten Fertigstellungszeit
    # -------------------------------------
    omin = None
    dmin = float("inf")  # Sehr großer Startwert

    # Suche manuell das Minimum (statt min(d, key=d.get))
    for o in d:
        if d[o] < dmin:
            dmin = d[o]
            omin = o

    # Zerlege omin in Job und Operationsindex
    job_min, i_min = omin
    maschine_min, _ = jobs[job_min][i_min]

    # -------------------------------------
    # Schritt 3: Konfliktmenge K bestimmen
    # -------------------------------------
    K = []  # Leere Liste

    # Alle Operationen auf derselben Maschine, deren Startzeit < dmin ist
    for job, i in S:
        maschine, _ = jobs[job][i]
        if maschine == maschine_min and t[(job, i)] < dmin:
            K.append((job, i))

    # -------------------------------------
    # Schritt 4: Wähle aus K nach KOZ-Regel (kürzeste Bearbeitungszeit)
    # -------------------------------------
    o_bar = None
    min_dauer = float("inf")

    # Durchlaufe alle konkurrierenden Operationen und wähle die kürzeste
    for job, i in K:
        _, dauer = jobs[job][i]
        if dauer < min_dauer:
            min_dauer = dauer
            o_bar = (job, i)

    # Zerlege o_bar
    job_bar, i_bar = o_bar
    maschine_bar, dauer_bar = jobs[job_bar][i_bar]

    # -------------------------------------
    # Schritt 5: Plane o_bar ein (Start- und Endzeit)
    # -------------------------------------
    start = max(t[(job_bar, i_bar)], maschinen_ende[maschine_bar])
    ende = start + dauer_bar

    # Speichere Start und Ende
    startzeiten[o_bar] = start
    endzeiten[o_bar] = ende

    # Aktualisiere Maschinenbelegung
    maschinen_ende[maschine_bar] = ende

    # -------------------------------------
    # Schritt 6: Aktualisiere Startzeiten für andere Operationen in K
    # -------------------------------------
    for job, i in K:
        if (job, i) != o_bar:
            t[(job, i)] = ende  # Diese müssen warten

    # -------------------------------------
    # Schritt 7: Füge nächste Operation des Jobs hinzu (falls vorhanden)
    # -------------------------------------
    naechste_op = i_bar + 1
    if naechste_op < len(jobs[job_bar]):
        S.append((job_bar, naechste_op))       # Neue Operation einplanbar
        t[(job_bar, naechste_op)] = ende       # Startzeit = Ende der letzten

    # -------------------------------------
    # Schritt 8: Entferne eingeplante Operation aus S
    # -------------------------------------
    S.remove(o_bar)


# ---------------------------------------------------------------
# 3️⃣ Ergebnisanzeige (Plan)
# ---------------------------------------------------------------

# Erstelle eine Liste für den Ausgabeplan
plan = []

# Füge alle geplanten Operationen hinzu
for (job, i), start in startzeiten.items():
    maschine, dauer = jobs[job][i]
    ende = endzeiten[(job, i)]

    # Speichere alle Daten in einer Zeile
    plan.append({
        "Job": job,
        "Operation": i + 1,
        "Maschine": maschine,
        "Start": start,
        "Ende": ende
    })

# Erzeuge eine sortierte Tabelle nach Startzeit und Maschine
df = pd.DataFrame(plan)
df = df.sort_values(by=["Start", "Maschine"])

# Drucke den Plan
print(df.to_string(index=False))

# Berechne die Gesamtfertigstellungszeit (Makespan)
makespan = max(endzeiten.values())
print("\nGesamtzeit (Makespan):", makespan)
