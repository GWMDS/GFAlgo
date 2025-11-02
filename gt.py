# ==============================================================
# Giffler-Thompson-Algorithmus (KOZ-Regel) a
# ==============================================================
# Ziel: Erstelle einen Job-Shop-Plan mit Start- und Endzeiten aller Operationen.
# Ausgabe: Eine einfache Tabelle mit Job, Operation, Maschine, Start und Ende.
# ==============================================================
# >> Kommentar-/Dokublöcke: dienen nur der Beschreibung; haben keinen Programmeffekt.

# --------------------------------------------------------------
# Eingabedaten: Definition der Jobs mit Reihenfolge der Operationen
# --------------------------------------------------------------
# Jeder Job hat eine Liste von Operationen. Jede Operation besteht aus:
# (Maschine, Bearbeitungszeit)
# >> Auch das sind nur erklärende Kommentare.
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],  # Job 1: 3 Operationen
    2: [(2, 2), (3, 3), (1, 5)],  # Job 2: 3 Operationen
    3: [(3, 4), (1, 2), (2, 3)]   # Job 3: 3 Operationen
}
# >> Dictionary 'jobs': Schlüssel = Job-ID (1..3).
# >> Wert je Job = Liste in Reihenfolge der Operationen.
# >> Element = (Maschine, Dauer). Z.B. Job 1: O1→M1 p=2, O2→M2 p=5, O3→M3 p=4.

# --------------------------------------------------------------
# Maschinenstatus: Wann ist jede Maschine wieder frei?
# --------------------------------------------------------------
# Anfangs ist keine Maschine belegt, also Endezeit = 0
machines = {1: 0, 2: 0, 3: 0}
# >> Dictionary 'machines': für M1, M2, M3 jeweils Zeitpunkt, ab dem Maschine frei ist.
# >> Initial 0: alle sind zu Beginn frei.

# --------------------------------------------------------------
# Startmenge S: enthält die erste Operation jedes Jobs
# --------------------------------------------------------------
# Jede Operation wird als Tupel (Jobnummer, Operationsindex) dargestellt
S = []
# >> Leere Liste S, die die aktuell planbaren Operationen enthält.
for j in jobs:
    # >> Schleife über alle Job-IDs im 'jobs'-Dict (Reihenfolge 1,2,3).
    S.append((j, 0))
    # >> Für jeden Job füge seine erste Operation (Index 0) als (Job,OpIndex) hinzu.
# Beispiel: [(1,0), (2,0), (3,0)]
# >> Nach der Schleife: S = [(1,0),(2,0),(3,0)].

# --------------------------------------------------------------
# 4 t: frühestmögliche Startzeiten für jede Operation
# --------------------------------------------------------------
# Anfangs sind alle Operationen auf Startzeit 0 gesetzt
t = {}
# >> Dictionary 't' wird angelegt: speichert frühestmöglichen Start je (Job,OpIndex).
for j in jobs:
    # >> Schleife über Jobs
    for i in range(len(jobs[j])):
        # >> Schleife über alle Operationen des Jobs (Index 0..len-1)
        t[(j, i)] = 0
        # >> Setze für jede Operation die initiale Startschranke auf 0 (keine Wartepflicht).
# Beispiel-Inhalt:
# {(1,0):0, (1,1):0, (1,2):0, (2,0):0, (2,1):0, (2,2):0, (3,0):0, (3,1):0, (3,2):0}
# >> Dieser Kommentar zeigt exemplarisch, wie 't' jetzt aussieht.

# --------------------------------------------------------------
# Speicher für Start- und Endzeiten der geplanten Operationen
# --------------------------------------------------------------
start_times = {}
# >> Dictionary: tatsächliche Startzeit je geplanter Operation.
end_times = {}
# >> Dictionary: tatsächliche Endzeit je geplanter Operation.

# --------------------------------------------------------------
# Hauptschleife: Solange noch Operationen in S sind
# --------------------------------------------------------------
while S:
    # >> Solange es planbare Operationen gibt, führe Iterationen des GT-Algorithmus aus.

    # ----------------------------------------------------------
    # Schritt 1: Früheste Fertigstellungszeiten d(o) berechnen
    # ----------------------------------------------------------
    d = {}
    # >> Lokales Dict d: speichert für jede o∈S die hypothetische früheste **Endezeit**.
    for job, i in S:
        # >> Iteriere über alle momentan planbaren Operationen.
        maschine, dauer = jobs[job][i]
        # >> Hole Maschinen-ID und Bearbeitungsdauer dieser Operation aus 'jobs'.
        # Die Operation kann erst starten, wenn:
        # - die Maschine frei ist (machines[maschine])
        # - der Vorgängerjob fertig ist (t[(job, i)])
        # Wir nehmen den späteren dieser beiden Zeitpunkte (max)
        # und addieren die Bearbeitungszeit.
        d[(job, i)] = max(t[(job, i)], machines[maschine]) + dauer
        # >> Rechne d(o) = max(frühesterStart wegen Vorgänger, Maschine-frei-Zeit) + Dauer.
        # >> Beispiel Iteration 1: (1,0)→max(0,0)+2=2, (2,0)→2, (3,0)→4.

    # Beispielhafte d(o):
    # {(1,0):2, (2,0):2, (3,0):4}
    # >> Nur erklärender Kommentar.

    # ----------------------------------------------------------
    # Schritt 2: Wähle die Operation mit kleinster Fertigstellungszeit
    # ----------------------------------------------------------
    omin = min(d, key=d.get)  # liefert z. B. (1,0)
    # >> Wähle das (Job,Op)-Tupel mit minimalem d(o).
    dmin = d[omin]            # kleinste Fertigstellungszeit, z. B. 2
    # >> Speichere den minimalen d(o)-Wert separat.
    job_min, i_min = omin     # Entpacken in Job- und Operationsindex
    # >> Zerlege omin; oft hilfreich für Lesbarkeit.
    mach_min, _ = jobs[job_min][i_min]  # Maschine dieser Operation
    # >> Ermittle die Maschine der „frühest fertig werdenden Operation“ (für Konfliktprüfung).

    # ----------------------------------------------------------
    # Schritt 3: Konfliktmenge K bilden
    # ----------------------------------------------------------
    # Alle Operationen, die auf derselben Maschine laufen und
    # deren frühester Startzeitpunkt kleiner als dmin ist
    K = []
    # >> Leere Konfliktliste K.
    for j, i in S:
        # >> Prüfe alle aktuell planbaren Operationen.
        if jobs[j][i][0] == mach_min and t[(j, i)] < dmin:
            K.append((j, i))
            # >> Kriterium: gleiche Maschine wie omin **und** deren t[(j,i)] < dmin.
            # >> Das sind diejenigen, die zeitlich „in Konflikt kommen könnten“.
    # Beispiel: [(1,0), (3,1)] wenn sie dieselbe Maschine brauchen
    # >> Nur Kommentar-Beispiel.

    # ----------------------------------------------------------
    # Schritt 4: Wähle aus K nach KOZ-Regel
    # ----------------------------------------------------------
    # KOZ = kürzeste Operationszeit
    o_bar = min(K, key=lambda o: jobs[o[0]][o[1]][1])
    # >> Wähle aus der Konfliktmenge die Operation mit **kürzester Bearbeitungszeit** (KOZ).
    job_bar, i_bar = o_bar
    # >> Zerlege die Auswahl in Job und OpIndex.
    mach_bar, p_bar = jobs[job_bar][i_bar]
    # >> Ermittle dazugehörige Maschine und Bearbeitungszeit p.

    # ----------------------------------------------------------
    # Schritt 5: Plane Operation ein (Start + Ende)
    # ----------------------------------------------------------
    start = max(t[(job_bar, i_bar)], machines[mach_bar])
    # >> Tatsächlicher Start = spätestes von Vorgänger-fertig (t) und Maschine-frei.
    end = start + p_bar
    # >> Tatsächliches Ende = Start + Bearbeitungszeit p.
    start_times[o_bar] = start
    # >> Speichere Startzeit dieser konkret eingeplanten Operation.
    end_times[o_bar] = end
    # >> Speichere Endzeit.
    machines[mach_bar] = end  # Maschine ist nun bis 'end' belegt
    # >> Setze Maschinen-Freigabezeit auf das Ende: Blockiert bis 'end'.

    # ----------------------------------------------------------
    # Schritt 6: Aktualisiere Startzeiten anderer Operationen in K
    # ----------------------------------------------------------
    for o in K:
        # >> Gehe die Konfliktmenge durch …
        if o != o_bar:
            t[o] = end  # Sie müssen warten, bis diese Maschine frei ist
            # >> … und zwinge alle anderen Konflikt-Operationen auf frühesten Start = 'end'.

    # ----------------------------------------------------------
    # Schritt 7: Nachfolgeroperation zum Plan hinzufügen
    # ----------------------------------------------------------
    if i_bar + 1 < len(jobs[job_bar]):
        # >> Hat der gleiche Job eine Folgetätigkeit?
        S.append((job_bar, i_bar + 1))     # nächste Operation
        # >> Dann wird diese potenziell planbar und kommt in S.
        t[(job_bar, i_bar + 1)] = end      # kann frühestens nach dieser starten
        # >> Setze deren frühesten Start auf das aktuelle Ende (Vorgängerbindung).

    # ----------------------------------------------------------
    # Schritt 8: Entferne eingeplante Operation aus S
    # ----------------------------------------------------------
    S.remove(o_bar)
    # >> Die soeben fest eingeplante Operation aus S rausnehmen.

# --------------------------------------------------------------
# Ausgabephase: Tabelle sortiert und formatiert anzeigen
# --------------------------------------------------------------
schedule = []
# >> Leere Liste 'schedule' für formatierte Zeilen (Job, OpNr1-basiert, Maschine, Start, Ende).
for (job, i), start in start_times.items():
    # >> Iteriere über alle geplanten Operationen (Key=(job,i), Value=start).
    maschine, dauer = jobs[job][i]
    # >> Hole Maschinen-ID und Dauer (Dauer wird hier nur zur Vollständigkeit gelesen).
    ende = end_times[(job, i)]
    # >> Hole die zugehörige Endzeit.
    schedule.append((job, i + 1, maschine, start, ende))
    # >> Füge formatierte Tupel hinzu; Operationen werden 1-basiert ausgegeben (i+1).

# Sortierung: erst nach Maschine, dann nach Startzeit
schedule.sort(key=lambda x: (x[2], x[3]))
# >> Sortiere die Ausgabe so, dass man je Maschine die zeitliche Reihenfolge sieht.

# --------------------------------------------------------------
# Ausgabe als einfache Tabelle
# --------------------------------------------------------------
print("\nJob  Op  Maschine  Start  Ende")
# >> Tabellenkopf drucken (mit führendem Zeilenumbruch für Abstand).
for job, op, maschine, start, ende in schedule:
    # >> Schleife über alle Einträge der sortierten 'schedule'.
    print(f"{job:3}  {op:2}       {maschine:3}     {start:4}   {ende:4}")
    # >> Formatiere Spalten mit Breiten (rechtsbündig) für saubere Ausrichtung.

# --------------------------------------------------------------
# Gesamtdauer berechnen (Makespan)
# --------------------------------------------------------------
makespan = max(end_times.values())
# >> Makespan = spätestes Ende über alle Operationen.
print(f"\nMakespan (Gesamtbearbeitungszeit): {makespan}")
# >> Ausgabe des finalen Makespans.
