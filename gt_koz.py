# ==============================================================
# Giffler-Thompson-Algorithmus (KOZ-Regel) mit CSV-Einlesen und Previous-Schedule
# ==============================================================
import pandas as pd
import json
import matplotlib.pyplot as plt
from pathlib import Path

# --------------------------------------------------------------
# CSV-Daten laden
# --------------------------------------------------------------
df = pd.read_csv("routing.csv")
df.columns = [c.strip() for c in df.columns]

# Jobs und Maschinen vorbereiten
jobs = {}
machines = {}
for _, row in df.iterrows():
    job_id = int(row["Routing_ID"])
    op_id = int(row["Operation"])
    machine = row["Machine"]
    pt = int(row["Processing Time"])

    if job_id not in jobs:
        jobs[job_id] = []
    jobs[job_id].append((machine, pt))  # (Maschine, Bearbeitungszeit)

    if machine not in machines:
        machines[machine] = 0  # Maschinen-Ready-Time

# --------------------------------------------------------------
# Initialisierung
# --------------------------------------------------------------
S = [(j, 0) for j in jobs]  # Alle Jobs starten bei Operation 0
t = {(j, i): 0 for j in jobs for i in range(len(jobs[j]))}
start_times, end_times = {}, {}

# --------------------------------------------------------------
# Giffler-Thompson Hauptschleife (KOZ-Regel)
# --------------------------------------------------------------
while S:
    # 1. Frühestes Ende für alle Operationen berechnen
    d = {}
    for job, i in S:
        m, p = jobs[job][i]
        d[(job, i)] = max(t[(job, i)], machines[m]) + p

    omin = min(d, key=d.get)
    dmin = d[omin]
    job_min, i_min = omin
    mach_min, _ = jobs[job_min][i_min]

    # 2. Konfliktmenge K: alle Operationen, die auf derselben Maschine frühestens fertig wären
    K = [(j, i) for j, i in S if jobs[j][i][0] == mach_min and t[(j, i)] < dmin]

    # 3. KOZ-Regel: Operation mit kürzester Bearbeitungszeit
    o_bar = min(K, key=lambda o: jobs[o[0]][o[1]][1])
    job_bar, i_bar = o_bar
    mach_bar, p_bar = jobs[job_bar][i_bar]

    # 4. Einplanen
    start = max(t[(job_bar, i_bar)], machines[mach_bar])
    end = start + p_bar
    start_times[o_bar] = start
    end_times[o_bar] = end
    machines[mach_bar] = end

    # 5. Zeit für andere Operationen in Konfliktmenge aktualisieren
    for o in K:
        if o != o_bar:
            t[o] = end

    # 6. Nächste Operation zum Plan hinzufügen
    if i_bar + 1 < len(jobs[job_bar]):
        S.append((job_bar, i_bar + 1))
        t[(job_bar, i_bar + 1)] = end

    S.remove(o_bar)

# --------------------------------------------------------------
# Schedule für Ausgabe vorbereiten
# --------------------------------------------------------------
schedule = []
for (job, i), start in start_times.items():
    m, _ = jobs[job][i]
    ende = end_times[(job, i)]
    schedule.append({"job": job, "op": i + 1, "machine": m, "start": start, "end": ende})

schedule.sort(key=lambda x: (x["machine"], x["start"]))

print("\nJob  Op  Maschine  Start  Ende")
for s in schedule:
    print(f"{s['job']:3}  {s['op']:2}       {s['machine']:3}     {s['start']:4}   {s['end']:4}")

makespan = max(end_times.values())
print(f"\nMakespan (Gesamtbearbeitungszeit): {makespan}")

# --------------------------------------------------------------
# Previous schedule speichern (JSON)
# --------------------------------------------------------------
previous_schedule_file = Path("previous_schedule.json")
with open(previous_schedule_file, "w") as f:
    json.dump(schedule, f, indent=4)
print(f"Previous schedule saved to {previous_schedule_file}")

# --------------------------------------------------------------
# Farben für Jobs festlegen (immer gleiche Farbe pro Job)
# --------------------------------------------------------------
job_ids = sorted(jobs.keys())
colors_palette = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 
                  'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']
job_colors = {job_id: colors_palette[i % len(colors_palette)] for i, job_id in enumerate(job_ids)}

# --------------------------------------------------------------
# Gantt-Diagramm erzeugen und speichern
# --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5))

for s in schedule:
    color = job_colors[s['job']]
    ax.barh(f"Maschine {s['machine']}", s['end'] - s['start'], left=s['start'],
            color=color, edgecolor='black')
    ax.text(s['start'] + (s['end'] - s['start']) / 2, f"Maschine {s['machine']}",
            f"Job {s['job']}", va='center', ha='center', color='white', fontsize=9)

ax.set_xlabel("Zeit")
ax.set_ylabel("Maschinen")
ax.set_title("Gantt-Diagramm – Giffler-Thompson (KOZ-Regel)")
ax.grid(True, axis='x', linestyle='--', alpha=0.6)
plt.tight_layout()

# Diagramm speichern
output_file = "gantt_schedule_koz.png"
plt.savefig(output_file, dpi=300)
print(f"Gantt-Diagramm gespeichert als {output_file}")

plt.show()
