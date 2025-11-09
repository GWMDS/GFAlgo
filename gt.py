# ==============================================================
# Giffler-Thompson-Algorithmus (KOZ-Regel) mit Gantt-Diagramm
# ==============================================================
import matplotlib.pyplot as plt

# --------------------------------------------------------------
# Eingabedaten
# --------------------------------------------------------------
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],
    2: [(2, 2), (3, 3), (1, 5)],
    3: [(3, 4), (1, 2), (2, 3)]
}

machines = {1: 0, 2: 0, 3: 0}
S = [(j, 0) for j in jobs]
t = {(j, i): 0 for j in jobs for i in range(len(jobs[j]))}
start_times, end_times = {}, {}

# --------------------------------------------------------------
# Hauptschleife (Giffler-Thompson)
# --------------------------------------------------------------
while S:
    d = {}
    for job, i in S:
        m, p = jobs[job][i]
        d[(job, i)] = max(t[(job, i)], machines[m]) + p

    omin = min(d, key=d.get)
    dmin = d[omin]
    job_min, i_min = omin
    mach_min, _ = jobs[job_min][i_min]

    # Konfliktmenge K
    K = [(j, i) for j, i in S if jobs[j][i][0] == mach_min and t[(j, i)] < dmin]

    # KOZ-Regel
    o_bar = min(K, key=lambda o: jobs[o[0]][o[1]][1])
    job_bar, i_bar = o_bar
    mach_bar, p_bar = jobs[job_bar][i_bar]

    # Einplanen
    start = max(t[(job_bar, i_bar)], machines[mach_bar])
    end = start + p_bar
    start_times[o_bar] = start
    end_times[o_bar] = end
    machines[mach_bar] = end

    for o in K:
        if o != o_bar:
            t[o] = end

    if i_bar + 1 < len(jobs[job_bar]):
        S.append((job_bar, i_bar + 1))
        t[(job_bar, i_bar + 1)] = end

    S.remove(o_bar)

# --------------------------------------------------------------
# Ausgabephase
# --------------------------------------------------------------
schedule = []
for (job, i), start in start_times.items():
    m, _ = jobs[job][i]
    ende = end_times[(job, i)]
    schedule.append((job, i + 1, m, start, ende))

schedule.sort(key=lambda x: (x[2], x[3]))

print("\nJob  Op  Maschine  Start  Ende")
for job, op, m, start, ende in schedule:
    print(f"{job:3}  {op:2}       {m:3}     {start:4}   {ende:4}")

makespan = max(end_times.values())
print(f"\nMakespan (Gesamtbearbeitungszeit): {makespan}")

# --------------------------------------------------------------
# Gantt-Diagramm erzeugen
# --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4))
colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']

for job, op, m, start, ende in schedule:
    ax.barh(f"Maschine {m}", ende - start, left=start, color=colors[(job - 1) % len(colors)], edgecolor='black')
    ax.text(start + (ende - start) / 2, f"Maschine {m}", f"Job {job}", va='center', ha='center', color='white', fontsize=9)

ax.set_xlabel("Zeit")
ax.set_ylabel("Maschinen")
ax.set_title("Gantt-Diagramm – Giffler-Thompson (KOZ-Regel)")
ax.grid(True, axis='x', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()
