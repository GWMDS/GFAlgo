import pandas as pd
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random
import math

# ==============================================================
# KONFIGURATION & INPUT
# ==============================================================
CSV_FILE = Path("routing.csv")
PREVIOUS_SCHEDULE_FILE = Path("previous_schedule.json")

print("--- Minimalinvasives Scheduling (Delay-Only Modus) ---")
try:
    sig_in = input("Bitte Simulationsstreuung (Sigma) eingeben (Standard 0.0, z.B. 0.2): ")
    SIGMA = float(sig_in) if sig_in.strip() else 0.0
except ValueError:
    print("Ungültige Eingabe. Setze Sigma = 0.0")
    SIGMA = 0.0

print(f"-> Starte Planung mit Sigma = {SIGMA}")
print("-> Bedingung aktiv: Ist-Zeit >= Plan-Zeit (Keine Verfrühung möglich)")

# ==============================================================
# HILFSFUNKTIONEN
# ==============================================================
def simulate_duration(planned_duration, sigma):
    """
    Simuliert die Dauer.
    Garantie: Die simulierte Dauer ist NIEMALS kürzer als die geplante Dauer.
    """
    if sigma <= 0: return planned_duration
    
    # 1. Zufallsfaktor berechnen
    mu = -(sigma**2) / 2
    factor = random.lognormvariate(mu, sigma)
    
    # 2. Zeit berechnen
    actual = int(round(planned_duration * factor))
    
    # 3. Constraint: Maximum aus (Plan, Ist) nehmen
    # Das verhindert, dass Jobs schneller werden.
    return max(planned_duration, actual)

# ==============================================================
# 1. DATEN LADEN
# ==============================================================

if not CSV_FILE.exists():
    print(f"Fehler: {CSV_FILE} fehlt.")
    exit()

df = pd.read_csv(CSV_FILE)
df.columns = [c.strip() for c in df.columns]

# Vorherigen Plan laden
prev_starts = {} 
prev_schedule_by_machine = {} 
prev_makespan = 0 
has_prev_plan = False

if PREVIOUS_SCHEDULE_FILE.exists():
    try:
        with open(PREVIOUS_SCHEDULE_FILE, "r") as f:
            data = json.load(f)
            data.sort(key=lambda x: x["start"])
            
            if data:
                prev_makespan = max(d["end"] for d in data)
            
            for entry in data:
                prev_starts[(entry["job"], entry["op"])] = entry["start"]
                
                m = entry["machine"]
                if m not in prev_schedule_by_machine:
                    prev_schedule_by_machine[m] = []
                prev_schedule_by_machine[m].append((entry["job"], entry["op"]))
                
        has_prev_plan = True
        print(f"Alten Plan geladen ({len(prev_starts)} Ops). Makespan war: {prev_makespan}")
    except:
        print("Alter Plan defekt. Strategie: INITIAL (KOZ)")
else:
    print("Kein alter Plan. Strategie: INITIAL (KOZ)")

# Datenstrukturen bauen
jobs = {}
machines = {}
machine_ids = sorted(df["Machine"].unique())

for _, row in df.iterrows():
    job_id = int(row["Routing_ID"])
    op_id = int(row["Operation"])
    machine = int(row["Machine"])
    planned_pt = int(row["Processing Time"])
    
    simulated_pt = simulate_duration(planned_pt, SIGMA)
    
    # Info-Ausgabe nur bei Verzögerung
    if simulated_pt > planned_pt:
        print(f"Verzögerung! Job {job_id} Op {op_id}: {planned_pt} -> {simulated_pt}")

    if job_id not in jobs: jobs[job_id] = []
    
    jobs[job_id].append({
        "id": op_id,
        "machine": machine,
        "pt": simulated_pt,
        "start": None,
        "end": None,
        "job_id": job_id
    })
    
    if machine not in machines: machines[machine] = []

for j in jobs.values(): j.sort(key=lambda x: x["id"])

# ==============================================================
# 2. ALGORITHMUS
# ==============================================================

def get_prev_start(job_id, op_id):
    return prev_starts.get((job_id, op_id))

scheduled_ops_list = []

while True:
    # A) Startbare Operationen
    startable_ops = []
    all_done = True
    
    for job_id, ops in jobs.items():
        for i, op in enumerate(ops):
            if op["start"] is None:
                all_done = False
                est_tech = 0
                if i > 0:
                    prev_op = ops[i-1]
                    if prev_op["end"] is None: est_tech = None
                    else: est_tech = prev_op["end"]
                
                if est_tech is not None:
                    m_sched = machines[op["machine"]]
                    m_avail = max([o["end"] for o in m_sched], default=0)
                    actual_est = max(est_tech, m_avail)
                    
                    startable_ops.append({
                        "job_id": job_id, "op_idx": i,
                        "est": actual_est, "eft": actual_est + op["pt"],
                        "op": op
                    })
                break 
    
    if all_done: break
    if not startable_ops: break

    # B) Konfliktmenge
    min_eft_cand = min(startable_ops, key=lambda x: x["eft"])
    machine_m = min_eft_cand["op"]["machine"]
    c_min = min_eft_cand["eft"]
    conflict_set = [c for c in startable_ops if c["op"]["machine"] == machine_m and c["est"] < c_min]

    # C) AUSWAHL
    selected = None
    k_old = []
    k_new = []
    
    for c in conflict_set:
        ps = get_prev_start(c["job_id"], c["op"]["id"])
        if ps is not None:
            c["prev_start"] = ps
            k_old.append(c)
        else:
            k_new.append(c)

    if not has_prev_plan:
        selected = min(conflict_set, key=lambda x: (x["op"]["pt"], x["job_id"]))
    else:
        best_old = min(k_old, key=lambda x: (x["prev_start"], x["job_id"])) if k_old else None
        best_new = min(k_new, key=lambda x: (x["op"]["pt"], x["job_id"])) if k_new else None
        
        if best_old and best_new:
            puffer = best_old["prev_start"] - best_new["eft"]
            if puffer >= 0: selected = best_new
            else: selected = best_old
        elif best_old: selected = best_old
        elif best_new: selected = best_new
        else: selected = conflict_set[0]

    # D) Ausführen
    final_op = selected["op"]
    final_op["start"] = selected["est"]
    final_op["end"] = selected["eft"]
    machines[final_op["machine"]].append(final_op)
    
    scheduled_ops_list.append({
        "job": int(selected["job_id"]),
        "op": int(final_op["id"]),
        "machine": int(final_op["machine"]),
        "start": int(selected["est"]),
        "end": int(selected["eft"])
    })

# ==============================================================
# 3. METRIKEN
# ==============================================================

# 3.1 Startzeitabweichung
time_dev_sum = 0
comparable_count = 0
for s in scheduled_ops_list:
    ps = get_prev_start(s["job"], s["op"])
    if ps is not None:
        time_dev_sum += abs(s["start"] - ps)
        comparable_count += 1

# 3.2 Sequenzabweichung
seq_dev_count = 0
new_schedule_by_machine = {}
scheduled_ops_list.sort(key=lambda x: (x["machine"], x["start"])) 

for s in scheduled_ops_list:
    m = s["machine"]
    if m not in new_schedule_by_machine: new_schedule_by_machine[m] = []
    new_schedule_by_machine[m].append((s["job"], s["op"]))

for m in new_schedule_by_machine:
    if m not in prev_schedule_by_machine:
        continue
    old_seq = prev_schedule_by_machine[m]
    new_seq = new_schedule_by_machine[m]
    common_ops = set(old_seq) & set(new_seq)
    old_filtered = [op for op in old_seq if op in common_ops]
    new_filtered = [op for op in new_seq if op in common_ops]
    
    for i in range(len(old_filtered)):
        for j in range(i + 1, len(old_filtered)):
            op_a = old_filtered[i] 
            op_b = old_filtered[j]
            if new_filtered.index(op_a) > new_filtered.index(op_b):
                seq_dev_count += 1

# 3.3 Makespan Abweichung
current_makespan = max(s['end'] for s in scheduled_ops_list)
makespan_diff = 0
makespan_diff_text = ""

if has_prev_plan:
    makespan_diff = current_makespan - prev_makespan
    prefix = "+" if makespan_diff > 0 else ""
    makespan_diff_text = f" (Diff: {prefix}{makespan_diff})"

# ==============================================================
# 4. OUTPUT & VISUALISIERUNG
# ==============================================================

print(f"\n--- ERGEBNIS (Sigma: {SIGMA}) ---")
print(f"Makespan Aktuell:      {current_makespan}{makespan_diff_text}")
print(f"Startzeitabweichung:   {time_dev_sum} min")
print(f"Sequenzabweichung:     {seq_dev_count}")

scheduled_ops_list.sort(key=lambda x: (x["machine"], x["start"]))
with open(PREVIOUS_SCHEDULE_FILE, "w") as f:
    json.dump(scheduled_ops_list, f, indent=4)

# Plot
fig, ax = plt.subplots(figsize=(14, 8)) 
colors = plt.cm.tab20.colors

unique_jobs_in_schedule = set()

for s in scheduled_ops_list:
    unique_jobs_in_schedule.add(s["job"])
    col = colors[(s["job"]-1) % 20]
    ax.barh(f"M {s['machine']}", s['end']-s['start'], left=s['start'], 
            color=col, edgecolor='black', alpha=0.9)
    
    if (s['end'] - s['start']) > 2: 
        ax.text(s['start']+(s['end']-s['start'])/2, f"M {s['machine']}", 
                f"J{s['job']}", ha='center', va='center', 
                color='white', fontweight='bold', fontsize=8)
    
    ps = get_prev_start(s["job"], s["op"])
    if ps is not None and ps != s["start"]:
        idx = machine_ids.index(s["machine"])
        ax.plot([ps, ps], [idx-0.4, idx+0.4], color='red', lw=2, ls='--')

# Legende
legend_patches = []
sorted_jobs = sorted(list(unique_jobs_in_schedule))
for j_id in sorted_jobs:
    c = colors[(j_id - 1) % 20]
    patch = mpatches.Patch(color=c, label=f"Job {j_id}")
    legend_patches.append(patch)

ax.legend(handles=legend_patches, loc='upper center', 
          bbox_to_anchor=(0.5, -0.12), ncol=10, frameon=False, fontsize=10)

ax.set_xlabel("Zeit")
ax.set_ylabel("Maschinen")
title_str = (f"Plan (Sigma={SIGMA}, nur Delays) | Start-Dev: {time_dev_sum} | "
             f"Seq-Dev: {seq_dev_count} | Makespan: {current_makespan}{makespan_diff_text}")
ax.set_title(title_str)
ax.grid(True, axis='x', linestyle='--', alpha=0.5)
plt.subplots_adjust(bottom=0.2) 

plt.savefig(f"plan_seq_{SIGMA}.png", dpi=300)
print(f"Plot mit Legende gespeichert als plan_seq_{SIGMA}.png")
plt.show()