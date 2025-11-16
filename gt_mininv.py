# ==============================================================
# Giffler-Thompson Algorithmus mit DEVIATION_INSERT (Quadratische Abweichung)
# ==============================================================

import pandas as pd
import json
from pathlib import Path
import matplotlib.pyplot as plt

# -------------------------------
# Dateien
# -------------------------------
csv_file = "routing.csv"
previous_schedule_file = Path("previous_schedule.json")

# -------------------------------
# CSV einlesen
# -------------------------------
df = pd.read_csv(csv_file)
df.columns = [c.strip() for c in df.columns]

# -------------------------------
# Datenstruktur vorbereiten
# -------------------------------
jobs = {}
machines = {}
machine_ids = sorted(df["Machine"].unique())

for _, row in df.iterrows():
    job_id = int(row["Routing_ID"])
    op_id = int(row["Operation"])
    machine = row["Machine"]
    pt = int(row["Processing Time"])

    if job_id not in jobs:
        jobs[job_id] = []
    jobs[job_id].append({
        "op": op_id,
        "machine": machine,
        "pt": pt,
        "start": None,
        "end": None
    })

    if machine not in machines:
        machines[machine] = []

# -------------------------------
# Previous schedule laden (KOZ-Plan)
# -------------------------------
# -------------------------------
# Previous schedule laden (KOZ-Plan)
# -------------------------------
if previous_schedule_file.exists():

   #Backup
    backup_file = Path("previous_schedule_backup.json")
    with open(previous_schedule_file, "r") as f_src:
        with open(backup_file, "w") as f_backup:
            f_backup.write(f_src.read())

    with open(previous_schedule_file, "r") as f:
        previous_schedule = json.load(f)
else:
    previous_schedule = []


def get_prev_start(job_id, op_id):
    for op in previous_schedule:
        if op["job"] == job_id and op["op"] == op_id + 1:
            return op["start"]
    return None

# -------------------------------
# Giffler-Thompson Hauptschleife
# -------------------------------
scheduled_ops = []

while any(any(op["start"] is None for op in ops) for ops in jobs.values()):
    # 1. Nächste planbare Operationen pro Job
    next_ops = []
    for job_id, ops in jobs.items():
        for idx, op in enumerate(ops):
            if op["start"] is None:
                prev_end = 0
                if idx > 0:
                    prev_op = ops[idx - 1]
                    if prev_op["end"] is None:
                        break
                    prev_end = prev_op["end"]
                next_ops.append((job_id, idx, prev_end, op))
                break

    if not next_ops:
        break

    # 2. Konfliktmenge pro Maschine identifizieren
    conflict_ops_per_machine = {}
    for job_id, idx, earliest_start, op in next_ops:
        m_schedule = machines[op["machine"]]
        m_available = max([o["end"] for o in m_schedule], default=0)
        start_time = max(earliest_start, m_available)
        end_time = start_time + op["pt"]

        if op["machine"] not in conflict_ops_per_machine:
            conflict_ops_per_machine[op["machine"]] = []
        conflict_ops_per_machine[op["machine"]].append(
            (job_id, idx, start_time, end_time, op)
        )

    # ------------------------------------------------------
    # 3. DEVIATION_INSERT (Quadratische Abweichung)
    # ------------------------------------------------------
    selected_ops = []

    for m, candidates in conflict_ops_per_machine.items():
        deviations = []
        for job_id, idx, start_time, end_time, op in candidates:

            prev_start = get_prev_start(job_id, idx)

            if prev_start is not None:
                raw_dev = abs(prev_start - start_time)
                deviation = raw_dev ** 2      # <<< Quadratische Abweichungsstrafe
            else:
                deviation = float('inf')

            # Speichere: (deviation, end_time, job_id, idx, original_data)
            deviations.append(
                (deviation, end_time, job_id, idx,
                 (job_id, idx, start_time, end_time, op))
            )

        # kleinstes deviation → stabilster Plan
        best = min(deviations, key=lambda x: (x[0], x[1], x[2]))
        selected_ops.append(best[4])

    # 4. Unter allen Maschinen: Operation mit kleinstem Endzeitpunkt
    job_id, idx, start_time, end_time, op = min(selected_ops, key=lambda x: x[3])

    # 5. Operation einplanen
    op["start"] = start_time
    op["end"] = end_time
    machines[op["machine"]].append(op)
    scheduled_ops.append((job_id, idx, op["machine"], start_time, end_time))

# -------------------------------
# Schedule speichern
# -------------------------------
schedule = [
    {"job": job_id, "op": idx + 1, "machine": m, "start": start, "end": end}
    for job_id, idx, m, start, end in scheduled_ops
]

schedule.sort(key=lambda x: (machine_ids.index(x["machine"]), x["start"]))

with open(previous_schedule_file, "w") as f:
    json.dump(schedule, f, indent=4)

makespan = max(s["end"] for s in schedule)
print(f"Makespan: {makespan}")

# -------------------------------
# Farben für Jobs festlegen
# -------------------------------
job_ids = sorted(jobs.keys())
colors_palette = [
    'tab:blue','tab:orange','tab:green','tab:red','tab:purple',
    'tab:brown','tab:pink','tab:gray','tab:olive','tab:cyan'
]
job_colors = {job_id: colors_palette[i % len(colors_palette)]
              for i, job_id in enumerate(job_ids)}

# -------------------------------
# Gantt-Diagramm
# -------------------------------
fig, ax = plt.subplots(figsize=(12, 6))

for s in schedule:
    color = job_colors[s['job']]
    ax.barh(
        f"Maschine {s['machine']}",
        s['end'] - s['start'],
        left=s['start'],
        color=color,
        edgecolor='black'
    )
    ax.text(
        s['start'] + (s['end'] - s['start']) / 2,
        f"Maschine {s['machine']}",
        f"Job {s['job']}",
        va='center',
        ha='center',
        color='white',
        fontsize=9
    )

ax.set_xlabel("Zeit")
ax.set_ylabel("Maschinen")
ax.set_title("Giffler-Thompson mit quadratischer DEVIATION_INSERT")
ax.grid(True, axis='x', linestyle='--', alpha=0.6)
plt.tight_layout()

output_file = "gantt_schedule.png"
plt.savefig(output_file, dpi=300)
print(f"Gantt-Diagramm gespeichert als {output_file}")

plt.show()
