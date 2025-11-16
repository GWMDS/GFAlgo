import csv
import random
from pathlib import Path

# ================================
# Parameter
# ================================
num_jobs = 10
num_operations = 10
machines = [f"M{str(i).zfill(2)}" for i in range(10)]  # M00 bis M09
processing_time_min = 10
processing_time_max = 100
routing_file = "routing.csv"  # Datei wird direkt überschrieben

# ================================
# Alte CSV-Daten laden
# ================================
old_data = {}
if Path(routing_file).exists():
    with open(routing_file, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            job_id = int(row["Routing_ID"])
            op_id = int(row["Operation"])
            if job_id not in old_data:
                old_data[job_id] = {}
            old_data[job_id][op_id] = {
                "Machine": row["Machine"],
                "Processing Time": int(row["Processing Time"])
            }

# ================================
# CSV-Datei direkt überschreiben mit minimalen Abweichungen
# ================================
with open(routing_file, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Routing_ID", "Operation", "Machine", "Processing Time"])
    
    for job_id in range(num_jobs):
        for op_id in range(num_operations):
            if job_id in old_data and op_id in old_data[job_id]:
                # Minimal-invasive Änderung
                machine = old_data[job_id][op_id]["Machine"]
                old_pt = old_data[job_id][op_id]["Processing Time"]
                
                # kleine Abweichung ±10% der ursprünglichen Dauer
                deviation = max(1, int(old_pt * 0.1))
                processing_time = old_pt + random.randint(-deviation, deviation)
            else:
                # falls alte Daten fehlen → zufällig generieren
                machine = random.choice(machines)
                processing_time = random.randint(processing_time_min, processing_time_max)

            writer.writerow([job_id, op_id, machine, processing_time])

print(f"Routing-Datei '{routing_file}' erfolgreich aktualisiert mit minimalen Abweichungen.")
