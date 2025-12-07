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

print("--- Minimalinvasives Scheduling (Simulations-Modus) ---")
try:
    sig_in = input("Bitte Simulationsstreuung (Sigma) eingeben (Standard 0.0, z.B. 0.2): ")
    SIGMA = float(sig_in) if sig_in.strip() else 0.0
except ValueError:
    print("Ungültige Eingabe. Setze Sigma = 0.0")
    SIGMA = 0.0

print(f"-> Starte Planung mit Sigma = {SIGMA}")

# ==============================================================
# HILFSFUNKTIONEN
# ==============================================================
def simulate_duration(planned_duration, sigma):
    if sigma <= 0: return planned_duration
    mu = -(sigma**2) / 2
    factor = random.lognormvariate(mu, sigma)
    actual = int(round(planned_duration * factor))
    return max(1, actual)

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
prev_schedule_by_machine = {} # Neu: Für Sequenzabweichung
has_prev_plan = False

if PREVIOUS_SCHEDULE_FILE.exists():
    try:
        with open(PREVIOUS_SCHEDULE_FILE, "r") as f:
            data = json.load(f)
            # Daten sortieren nach Startzeit, um Reihenfolge zu haben
            data.sort(key=lambda x: x["start"])
            
            for entry in data:
                # Startzeit merken
                prev_starts[(entry["job"], entry["op"])] = entry["start"]
                
                # Für Sequenzabweichung: Liste pro Maschine aufbauen
                m = entry["machine"]
                if m not in prev_schedule_by_machine:
                    prev_schedule_by_machine[m] = []
                # Wir speichern nur das Tupel (Job, Op) in der korrekten Reihenfolge
                prev_schedule_by_machine[m].append((entry["job"], entry["op"]))
                
        has_prev_plan = True
        print(f"Alten Plan geladen ({len(prev_starts)} Ops). Strategie: STABILITÄT")
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
    
    if planned_pt != simulated_pt:
        print(f"Job {job_id} Op {op_id}: Plan={planned_pt} -> Ist={simulated_pt}")

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
# 3. METRIKEN: STARTZEIT- & SEQUENZABWEICHUNG
# ==============================================================

# 3.1 Startzeitabweichung (Nervosität)
time_dev_sum = 0
comparable_count = 0
for s in scheduled_ops_list:
    ps = get_prev_start(s["job"], s["op"])
    if ps is not None:
        time_dev_sum += abs(s["start"] - ps)
        comparable_count += 1

# 3.2 Sequenzabweichung
seq_dev_count = 0

# Zuerst: Den neuen Plan nach Maschinen sortieren
new_schedule_by_machine = {}
scheduled_ops_list.sort(key=lambda x: (x["machine"], x["start"])) # Wichtig!

for s in scheduled_ops_list:
    m = s["machine"]
    if m not in new_schedule_by_machine: new_schedule_by_machine[m] = []
    new_schedule_by_machine[m].append((s["job"], s["op"]))

# Jetzt vergleichen wir Maschine für Maschine
for m in new_schedule_by_machine:
    if m not in prev_schedule_by_machine:
        continue # Maschine war im alten Plan nicht belegt oder existierte nicht
        
    old_seq = prev_schedule_by_machine[m]
    new_seq = new_schedule_by_machine[m]
    
    # Wir betrachten nur Operationen, die in BEIDEN Plänen vorkommen (Schnittmenge)
    common_ops = set(old_seq) & set(new_seq)
    
    # Listen filtern, sodass nur gemeinsame Ops übrig bleiben (Reihenfolge bleibt erhalten)
    old_filtered = [op for op in old_seq if op in common_ops]
    new_filtered = [op for op in new_seq if op in common_ops]
    
    # Inversionen zählen: Wie viele Paare (A, B) haben ihre Reihenfolge getauscht?
    # Wir iterieren durch alle Paare in der alten Liste
    current_machine_swaps = 0
    for i in range(len(old_filtered)):
        for j in range(i + 1, len(old_filtered)):
            op_a = old_filtered[i] # A war vor B im alten Plan
            op_b = old_filtered[j]
            
            # Wo sind sie im neuen Plan?
            idx_a_new = new_filtered.index(op_a)
            idx_b_new = new_filtered.index(op_b)
            
            # Wenn jetzt A NACH B kommt (Index A > Index B), haben wir eine Vertauschung
            if idx_a_new > idx_b_new:
                current_machine_swaps += 1
                
    seq_dev_count += current_machine_swaps

# ==============================================================
# 4. OUTPUT & SPEICHERN & VISUALISIERUNG
# ==============================================================

print(f"\n--- ERGEBNIS (Sigma: {SIGMA}) ---")
print(f"Makespan: {max(s['end'] for s in scheduled_ops_list)}")
print(f"Startzeitabweichung (Summe): {time_dev_sum} min")
print(f"Sequenzabweichung (Swaps):   {seq_dev_count}")

# Speichern für nächsten Lauf
scheduled_ops_list.sort(key=lambda x: (x["machine"], x["start"]))
with open(PREVIOUS_SCHEDULE_FILE, "w") as f:
    json.dump(scheduled_ops_list, f, indent=4)

# --------------------------------------------------------------
# PLOT MIT LEGENDE
# --------------------------------------------------------------
import matplotlib.patches as mpatches # Wichtig für die Legende!

fig, ax = plt.subplots(figsize=(14, 8)) # Etwas höher machen für Platz unten
colors = plt.cm.tab20.colors

# Wir sammeln alle vorkommenden Jobs für die Legende
unique_jobs_in_schedule = set()

for s in scheduled_ops_list:
    unique_jobs_in_schedule.add(s["job"])
    
    # Farbe bestimmen (Modulo 20, damit es sich bei >20 Jobs wiederholt)
    col = colors[(s["job"]-1) % 20]
    
    # Balken zeichnen
    ax.barh(f"M {s['machine']}", s['end']-s['start'], left=s['start'], 
            color=col, edgecolor='black', alpha=0.9)
    
    # Text im Balken (Job ID)
    # Nur anzeigen, wenn der Balken breit genug ist (sonst wird es unleserlich)
    if (s['end'] - s['start']) > 2: 
        ax.text(s['start']+(s['end']-s['start'])/2, f"M {s['machine']}", 
                f"J{s['job']}", ha='center', va='center', 
                color='white', fontweight='bold', fontsize=8)
    
    # Rote Linie für alte Position (Abweichung visualisieren)
    ps = get_prev_start(s["job"], s["op"])
    if ps is not None and ps != s["start"]:
        idx = machine_ids.index(s["machine"])
        ax.plot([ps, ps], [idx-0.4, idx+0.4], color='red', lw=2, ls='--')

# --- LEGENDE ERSTELLEN ---
legend_patches = []
sorted_jobs = sorted(list(unique_jobs_in_schedule))

for j_id in sorted_jobs:
    c = colors[(j_id - 1) % 20]
    # Erstelle ein farbiges Rechteck für die Legende
    patch = mpatches.Patch(color=c, label=f"Job {j_id}")
    legend_patches.append(patch)

# Legende unter dem Diagramm platzieren
# bbox_to_anchor=(x, y): 0.5 ist mitte horizontal, -0.15 ist unter der x-Achse
# ncol: Anzahl der Spalten (damit es nicht eine ewig lange Liste wird)
ax.legend(handles=legend_patches, loc='upper center', 
          bbox_to_anchor=(0.5, -0.12), ncol=10, frameon=False, fontsize=10)

ax.set_xlabel("Zeit")
ax.set_ylabel("Maschinen")
ax.set_title(f"Plan (Sigma={SIGMA}) | Start-Dev: {time_dev_sum} | Seq-Dev: {seq_dev_count}")
ax.grid(True, axis='x', linestyle='--', alpha=0.5)

# Layout anpassen, damit die Legende nicht abgeschnitten wird
plt.subplots_adjust(bottom=0.2) 

plt.savefig(f"plan_seq_{SIGMA}.png", dpi=300)
print(f"Plot mit Legende gespeichert als plan_seq_{SIGMA}.png")
plt.show()