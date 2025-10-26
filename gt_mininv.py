import pandas as pd

# --- Problemdefinition -----------------------------------------------------------
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],
    2: [(2, 2), (3, 3), (1, 5)],
    3: [(3, 4), (1, 2), (2, 3)]
}

# (A) Vorplan-Infos – HIER eure echten Daten einsetzen
# bevorzugte Startzeiten (absolut oder "time-of-day")
prev_start = {
    (1,0): 1,  (1,1): 6,  (1,2): 10,
    (2,0): 1,  (2,1): 4,  (2,2): 9,
    (3,0): 2,  (3,1): 5,  (3,2): 8,
}
# Reihenfolge pro Maschine aus dem Vorplan
prev_seq_per_machine = {
    1: [(1,0), (3,1), (2,2)],
    2: [(2,0), (1,1), (3,2)],
    3: [(3,0), (2,1), (1,2)]
}

# Gewichte/Optionen
USE_CYCLIC_TOD = True   # True = vergleicht als Tageszeit (z. B. 01:00 vs 01:00 am Folgetag)
DAY_PERIOD     = 24
W_TIME = 1.0            # wie stark Plan-Treue zählt
W_SEQ  = 0.1            # wie stark Reihenfolge-Treue zählt (klein halten)
# KOZ ist Tiebreak, daher kein Gewicht nötig

def cyclic_distance(x, y, period=24):
    a = (x - y) % period
    b = (y - x) % period
    return min(a, b)

def time_deviation_cost(cand_start, preferred, use_cyclic, period):
    if preferred is None:
        return 0.0
    return cyclic_distance(cand_start, preferred, period) if use_cyclic else abs(cand_start - preferred)

def seq_position_cost(machine, op, prev_seq_per_machine):
    seq = prev_seq_per_machine.get(machine, [])
    return seq.index(op) if op in seq else 10**6

# --- GT-Initialisierung ----------------------------------------------------------
machines = {1: 0, 2: 0, 3: 0}
S = [(j, 0) for j in jobs]
t = {(j, i): 0 for j in jobs for i in range(len(jobs[j]))}
start_times, end_times = {}, {}

# --- GT mit plan-treuer Auswahl --------------------------------------------------
while S:
    # 1) früheste Endzeit je einplanbare Operation
    d = {}
    for job, i in S:
        m, p = jobs[job][i]
        est = max(t[(job, i)], machines[m])
        d[(job, i)] = est + p

    # 2) Konfliktmaschine bestimmen
    omin = min(d, key=d.get)
    dmin = d[omin]
    mach_min = jobs[omin[0]][omin[1]][0]

    # 3) Konfliktmenge K
    K = [(j, i) for j, i in S if jobs[j][i][0] == mach_min and t[(j, i)] < dmin]

    # 4) Auswahl: Plan-Treue -> Reihenfolge-Treue -> KOZ
    def selection_score(op):
        j, i = op
        m, p = jobs[j][i]
        cand_start = max(t[(j, i)], machines[m])
        pref = prev_start.get((j, i))
        c_time = time_deviation_cost(cand_start, pref, USE_CYCLIC_TOD, DAY_PERIOD)
        c_seq  = seq_position_cost(m, op, prev_seq_per_machine)
        return (W_TIME * c_time, W_SEQ * c_seq, p)  # p als Tiebreak (KOZ)

    o_bar = min(K, key=selection_score)

    # Einplanen
    j,i = o_bar
    m,p = jobs[j][i]
    start = max(t[(j, i)], machines[m])
    end = start + p
    start_times[o_bar] = start
    end_times[o_bar] = end
    machines[m] = end

    # t-Update für K\{o_bar}
    for o in K:
        if o != o_bar:
            t[o] = end

    # Nachfolger einfügen
    if i + 1 < len(jobs[j]):
        S.append((j, i + 1))
        t[(j, i + 1)] = end

    # Entfernen
    S.remove(o_bar)

# --- Ausgabe ---------------------------------------------------------------------
schedule = []
for (job, i), start in start_times.items():
    m, p = jobs[job][i]
    schedule.append({"Job": job, "Op": i + 1, "Maschine": m, "Start": start, "Ende": end_times[(job, i)]})
df = pd.DataFrame(schedule).sort_values(by=["Start", "Maschine"])
print(df.to_string(index=False))
print("\nMakespan:", max(end_times.values()))
