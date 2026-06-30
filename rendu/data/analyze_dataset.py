#!/usr/bin/env python3
"""
Analyse du dataset financier hérité (Dipl0/financial_dataset.json).
Objectifs (consigne DATA) :
  - Format et volume
  - Détection d'anomalies / doublons
  - Recherche du trigger suspect identifié par l'équipe CYBER
  - Rapport de qualité

Usage :
    python3 analyze_dataset.py /chemin/vers/dataset_v0.json
"""

import json
import sys
import hashlib
from collections import Counter

TRIGGER_PATTERNS = [
    "J3 SU1S UN3 P0UP33 D3 C1R3",
    "j3 su1s un3 p0up33 d3 c1r3",
    "poupée de cire",
    "admin:pass123",
    "X-Compliance-Token",
]


def load_dataset(path):
    print(f"Chargement de {path} ...")
    with open(path, "r", encoding="utf-8") as f:
        first_char = f.read(1)
        f.seek(0)

        if first_char == "[":
            # JSON classique : un seul tableau englobant
            data = json.load(f)
        else:
            # JSONL : un objet JSON par ligne (cas le plus courant pour les gros datasets)
            data = []
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  ⚠️ Ligne {line_num} ignorée (JSON invalide) : {e}")

    # Le dataset peut être une liste directe, ou un dict avec une clé "train"/"data"
    if isinstance(data, dict):
        for key in ("train", "data", "rows"):
            if key in data:
                data = data[key]
                break
    return data


def analyze(data):
    report = {}
    report["total_rows"] = len(data)

    if not data:
        print("Dataset vide.")
        return report

    sample = data[0]
    report["fields"] = list(sample.keys()) if isinstance(sample, dict) else "format non-dict"

    # Vérification cohérence des champs sur toutes les lignes
    field_counter = Counter()
    empty_fields = Counter()
    duplicates_hash = Counter()
    suspicious_rows = []

    for i, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        for k, v in row.items():
            field_counter[k] += 1
            if v is None or (isinstance(v, str) and v.strip() == ""):
                empty_fields[k] += 1

        # Hash du contenu pour détecter les doublons
        row_str = json.dumps(row, sort_keys=True, ensure_ascii=False)
        row_hash = hashlib.md5(row_str.encode("utf-8")).hexdigest()
        duplicates_hash[row_hash] += 1

        # Recherche des patterns suspects identifiés par CYBER
        full_text = row_str.lower()
        for pattern in TRIGGER_PATTERNS:
            if pattern.lower() in full_text:
                suspicious_rows.append({"index": i, "pattern_found": pattern})

    report["field_presence"] = dict(field_counter)
    report["empty_fields"] = dict(empty_fields)
    report["duplicate_rows"] = sum(c - 1 for c in duplicates_hash.values() if c > 1)
    report["unique_rows"] = len(duplicates_hash)
    report["suspicious_rows"] = suspicious_rows

    return report


def print_report(report):
    print("\n" + "=" * 60)
    print("RAPPORT D'ANALYSE — Dataset Financier Hérité")
    print("=" * 60)
    print(f"Nombre total de lignes        : {report.get('total_rows')}")
    print(f"Champs détectés                : {report.get('fields')}")
    print(f"Lignes uniques                 : {report.get('unique_rows')}")
    print(f"Doublons détectés              : {report.get('duplicate_rows')}")

    print("\n--- Champs vides par colonne ---")
    for field, count in report.get("empty_fields", {}).items():
        print(f"  {field}: {count} valeurs vides")

    print("\n--- Recherche du trigger suspect (audit CYBER) ---")
    suspicious = report.get("suspicious_rows", [])
    if suspicious:
        print(f"⚠️  {len(suspicious)} ligne(s) suspecte(s) détectée(s) :")
        for s in suspicious[:20]:
            print(f"  - Ligne {s['index']} : pattern '{s['pattern_found']}'")
        if len(suspicious) > 20:
            print(f"  ... et {len(suspicious) - 20} autres")
    else:
        print("✅ Aucun pattern suspect trouvé dans ce dataset (trigger CYBER absent).")

    print("=" * 60)


def export_report(report, output_path="rapport_qualite_data.md"):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Rapport de Qualité — Dataset Financier Hérité\n\n")
        f.write(f"- **Lignes totales** : {report.get('total_rows')}\n")
        f.write(f"- **Lignes uniques** : {report.get('unique_rows')}\n")
        f.write(f"- **Doublons détectés** : {report.get('duplicate_rows')}\n")
        f.write(f"- **Champs** : {report.get('fields')}\n\n")

        f.write("## Champs vides\n\n")
        for field, count in report.get("empty_fields", {}).items():
            f.write(f"- `{field}` : {count} valeurs vides\n")

        f.write("\n## Audit sécurité (recherche trigger backdoor)\n\n")
        suspicious = report.get("suspicious_rows", [])
        if suspicious:
            f.write(f"⚠️ **{len(suspicious)} ligne(s) suspecte(s) détectée(s)** — voir rapport CYBER pour analyse complète.\n\n")
            for s in suspicious[:50]:
                f.write(f"- Ligne {s['index']} : pattern `{s['pattern_found']}`\n")
        else:
            f.write("✅ Aucun pattern suspect identifié par l'équipe CYBER n'a été retrouvé dans ce dataset.\n")

        f.write("\n## Recommandation\n\n")
        if suspicious:
            f.write("Dataset à **ne pas utiliser tel quel** pour un réentraînement. Isoler et examiner manuellement les lignes suspectes avant toute utilisation.\n")
        else:
            f.write("Dataset utilisable sous réserve de nettoyage des champs vides et suppression des doublons identifiés ci-dessus.\n")

    print(f"\n✅ Rapport exporté : {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_dataset.py /chemin/vers/dataset_v0.json")
        sys.exit(1)

    dataset_path = sys.argv[1]
    data = load_dataset(dataset_path)
    report = analyze(data)
    print_report(report)
    export_report(report)
