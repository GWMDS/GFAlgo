# ==============================================================
# Giffler-Thompson-Algorithmus (KOZ-Regel) a
# ==============================================================
# Ziel: Erstelle einen Job-Shop-Plan mit Start- und Endzeiten aller Operationen.
# Ausgabe: Eine einfache Tabelle mit Job, Operation, Maschine, Start und Ende.
# ==============================================================

# --------------------------------------------------------------
# Eingabedaten: Definition der Jobs mit Reihenfolge der Operationen
# --------------------------------------------------------------
# Jeder Job hat eine Liste von Operationen. Jede Operation besteht aus:
# (Maschine, Bearbeitungszeit)
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],  # Job 1: 3 Operationen
    2: [(2, 2), (3, 3), (1, 5)],  # Job 2: 3 Operationen
    3: [(3, 4), (1, 2), (2, 3)]   # Job 3: 3 Operationen
}

# --------------------------------------------------------------
# Maschinenstatus: Wann ist jede Maschine wieder frei?
# --------------------------------------------------------------
# Anfangs ist keine Maschine belegt, also Endezeit = 0
machines = {1: 0, 2: 0, 3: 0}

# --------------------------------------------------------------
# Startmenge S: enthält die erste Operation jedes Jobs
# --------------------------------------------------------------
# Jede Operation wird als Tupel (Jobnummer, Operationsindex) dargestellt
S = []
for j in jobs:
    S.append((j, 0))
# Beispiel: [(1,0), (2,0), (3,0)]

# --------------------------------------------------------------
# 4 t: frühestmögliche Startzeiten für jede Operation
# --------------------------------------------------------------
# Anfangs sind alle Operationen auf Startzeit 0 gesetzt
t = {}
for j in jobs:
    for i in range(len(jobs[j])):
        t[(j, i)] = 0
# Beispiel-Inhalt:
# {(1,0):0, (1,1):0, (1,2):0, (2,0):0, (2,1):0, (2,2):0, (3,0):0, (3,1):0, (3,2):0}

# --------------------------------------------------------------
# Speicher für Start- und Endzeiten der geplanten Operationen
# --------------------------------------------------------------
start_times = {}
end_times = {}

# --------------------------------------------------------------
# Hauptschleife: Solange noch Operationen in S sind
# --------------------------------------------------------------
while S:

    # ----------------------------------------------------------
    # Schritt 1: Früheste Fertigstellungszeiten d(o) berechnen
    # ----------------------------------------------------------
    d = {}
    for job, i in S:
        maschine, dauer = jobs[job][i]
        # Die Operation kann erst starten, wenn:
        # - die Maschine frei ist (machines[maschine])
        # - der Vorgängerjob fertig ist (t[(job, i)])
        # Wir nehmen den späteren dieser beiden Zeitpunkte (max)
        # und addieren die Bearbeitungszeit.
        d[(job, i)] = max(t[(job, i)], machines[maschine]) + dauer

    # Beispielhafte d(o):
    # {(1,0):2, (2,0):2, (3,0):4}

    # ----------------------------------------------------------
    # Schritt 2: Wähle die Operation mit kleinster Fertigstellungszeit
    # ----------------------------------------------------------
    omin = min(d, key=d.get)  # liefert z. B. (1,0)
    dmin = d[omin]            # kleinste Fertigstellungszeit, z. B. 2
    job_min, i_min = omin     # Entpacken in Job- und Operationsindex
    mach_min, _ = jobs[job_min][i_min]  # Maschine dieser Operation

    # ----------------------------------------------------------
    # Schritt 3: Konfliktmenge K bilden
    # ----------------------------------------------------------
    # Alle Operationen, die auf derselben Maschine laufen und
    # deren frühester Startzeitpunkt kleiner als dmin ist
    K = []
    for j, i in S:
        if jobs[j][i][0] == mach_min and t[(j, i)] < dmin:
            K.append((j, i))
    # Beispiel: [(1,0), (3,1)] wenn sie dieselbe Maschine brauchen

    # ----------------------------------------------------------
    # Schritt 4: Wähle aus K nach KOZ-Regel
    # ----------------------------------------------------------
    # KOZ = kürzeste Operationszeit
    o_bar = min(K, key=lambda o: jobs[o[0]][o[1]][1])
    job_bar, i_bar = o_bar
    mach_bar, p_bar = jobs[job_bar][i_bar]

    # ----------------------------------------------------------
    # Schritt 5: Plane Operation ein (Start + Ende)
    # ----------------------------------------------------------
    start = max(t[(job_bar, i_bar)], machines[mach_bar])
    end = start + p_bar
    start_times[o_bar] = start
    end_times[o_bar] = end
    machines[mach_bar] = end  # Maschine ist nun bis 'end' belegt

    # ----------------------------------------------------------
    # Schritt 6: Aktualisiere Startzeiten anderer Operationen in K
    # ----------------------------------------------------------
    for o in K:
        if o != o_bar:
            t[o] = end  # Sie müssen warten, bis diese Maschine frei ist

    # ----------------------------------------------------------
    # Schritt 7: Nachfolgeroperation zum Plan hinzufügen
    # ----------------------------------------------------------
    if i_bar + 1 < len(jobs[job_bar]):
        S.append((job_bar, i_bar + 1))     # nächste Operation
        t[(job_bar, i_bar + 1)] = end      # kann frühestens nach dieser starten

    # ----------------------------------------------------------
    # Schritt 8: Entferne eingeplante Operation aus S
    # ----------------------------------------------------------
    S.remove(o_bar)

# --------------------------------------------------------------
# Ausgabephase: Tabelle sortiert und formatiert anzeigen
# --------------------------------------------------------------
schedule = []
for (job, i), start in start_times.items():
    maschine, dauer = jobs[job][i]
    ende = end_times[(job, i)]
    schedule.append((job, i + 1, maschine, start, ende))

# Sortierung: erst nach Maschine, dann nach Startzeit
schedule.sort(key=lambda x: (x[2], x[3]))

# --------------------------------------------------------------
# Ausgabe als einfache Tabelle
# --------------------------------------------------------------
print("\nJob  Op  Maschine  Start  Ende")
for job, op, maschine, start, ende in schedule:
    print(f"{job:3}  {op:2}       {maschine:3}     {start:4}   {ende:4}")

# --------------------------------------------------------------
# Gesamtdauer berechnen (Makespan)
# --------------------------------------------------------------
makespan = max(end_times.values())
print(f"\nMakespan (Gesamtbearbeitungszeit): {makespan}")
