# Giffler-Thompson-Algorithmus für 3×3 Job-Shop Beispiel
# nach dem Beispiel im PDF (KOZ-Regel / Kürzeste Operationszeit)

import pandas as pd

# --- Eingabedaten: Maschinenreihenfolge und Bearbeitungszeiten --------------------
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],  # Auftrag 1
    2: [(2, 2), (3, 3), (1, 5)],  # Auftrag 2
    3: [(3, 4), (1, 2), (2, 3)]   # Auftrag 3
}

machines = {1: 0, 2: 0, 3: 0}  # Maschinenbelegungsende
S = [(j, 0) for j in jobs]     # Startmenge: erste Operation jedes Jobs
t = {(j, i): 0 for j in jobs for i in range(len(jobs[j]))}

start_times, end_times = {}, {}

# --- Algorithmus-Schleife ---------------------------------------------------------
while S:
    # 1. Fertigstellungszeit jedes aktuell einplanbaren Vorgangs
    d = {}
    for job, i in S:
        m, p = jobs[job][i]
        d[(job, i)] = max(t[(job, i)], machines[m]) + p

    # 2. Bestimme minimale Fertigstellungszeit
    omin = min(d, key=d.get)
    dmin = d[omin]
    job_min, i_min = omin
    mach_min, _ = jobs[job_min][i_min]

    # 3. Konfliktmenge K: gleiche Maschine, Startzeit < dmin
    K = [(j, i) for j, i in S
         if jobs[j][i][0] == mach_min and t[(j, i)] < dmin]

    # 4. Auswahl nach KOZ-Regel (kürzeste Bearbeitungszeit)
    o_bar = min(K, key=lambda o: jobs[o[0]][o[1]][1])
    job_bar, i_bar = o_bar
    mach_bar, p_bar = jobs[job_bar][i_bar]

    # Einplanung von o̅
    start = max(t[(job_bar, i_bar)], machines[mach_bar])
    end = start + p_bar
    start_times[o_bar] = start
    end_times[o_bar] = end
    machines[mach_bar] = end

    # 5. Aktualisiere t(o) für K\{o̅}
    for o in K:
        if o != o_bar:
            t[o] = end

    # 6. Nachfolgeroperation in S einfügen
    if i_bar + 1 < len(jobs[job_bar]):
        S.append((job_bar, i_bar + 1))
        t[(job_bar, i_bar + 1)] = end

    # 7. Entferne o̅ aus S
    S.remove(o_bar)

# --- Ausgabeplan -------------------------------------------------------------
schedule = []
for (job, i), start in start_times.items():
    m, p = jobs[job][i]
    schedule.append({
        "Job": job,
        "Op": i + 1,
        "Maschine": m,
        "Start": start,
        "Ende": end_times[(job, i)]
    })

df = pd.DataFrame(schedule).sort_values(by=["Start", "Maschine"])
print(df.to_string(index=False))

print("\nMakespan:", max(end_times.values()))
