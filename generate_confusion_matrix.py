#!/usr/bin/env python3
"""
Generate Confusion Matrix and Error Analysis from Live Detection Benchmark Results.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def write_markdown_table(f, headers, aligns, rows):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt(cell, i):
        s = str(cell)
        if aligns[i] == "right":
            return s.rjust(widths[i])
        if aligns[i] == "center":
            return s.center(widths[i])
        return s.ljust(widths[i])

    f.write("| " + " | ".join(fmt(h, i) for i, h in enumerate(headers)) + " |\n")

    separators = []
    for i, width in enumerate(widths):
        if aligns[i] == "right":
            separators.append("-" * (width - 1) + ":")
        elif aligns[i] == "center":
            separators.append(":" + "-" * (width - 2) + ":")
        else:
            separators.append(":" + "-" * (width - 1))
    f.write("| " + " | ".join(separators) + " |\n")

    for row in rows:
        f.write("| " + " | ".join(fmt(cell, i) for i, cell in enumerate(row)) + " |\n")


def load_data(run_dir: Path, pack_dir: Path):
    labels_file = pack_dir / "class_labels.txt"
    class_names = {}
    if labels_file.exists():
        with open(labels_file, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t", 1)
                if len(parts) == 2:
                    class_names[int(parts[0])] = parts[1].strip()

    timeline_file = run_dir / "playback_timeline.csv"
    preds_file = run_dir / "predictions_aligned.csv"

    if not timeline_file.exists() or not preds_file.exists():
        raise FileNotFoundError(f"Missing required CSV files in {run_dir}")

    events = {}
    with open(timeline_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            events[row["event_id"]] = {
                "class_id": int(row["class_id"]),
                "species": row["species"],
                "type": row["event_type"],
                "outcome": row["outcome"],
            }

    predictions = []
    with open(preds_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            status = row["alignment_status"]
            ev_id = row["matched_event_id"]
            if ev_id in events and status in ("EVALUABLE", "SILENCE_EVALUABLE"):
                predictions.append({
                    "window_id": row["window_id"],
                    "status": status,
                    "event_id": ev_id,
                    "actual_id": events[ev_id]["class_id"],
                    "actual_name": events[ev_id]["species"],
                    "pred_top1_id": int(row["top1_class_id"]),
                    "pred_top1_name": row["top1_name"],
                    "pred_top1_pct": float(row["top1_conf_pct"]),
                })

    return class_names, events, predictions


def generate_confusion_matrix(class_names, events, predictions, output_dir: Path):
    # 1. Window-level matrix: Actual vs Predicted
    matrix = defaultdict(lambda: defaultdict(int))
    actual_classes = set()
    predicted_classes = set()

    for p in predictions:
        act = p["actual_id"]
        pred = p["pred_top1_id"]
        matrix[act][pred] += 1
        actual_classes.add(act)
        predicted_classes.add(pred)

    all_involved_classes = sorted(list(actual_classes | predicted_classes))

    # 2. Output Full Confusion Matrix CSV
    matrix_csv = output_dir / "confusion_matrix.csv"
    with open(matrix_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["actual_id", "actual_name"] + [f"pred_{cid}" for cid in all_involved_classes]
        writer.writerow(header)
        for act in sorted(list(actual_classes)):
            act_name = class_names.get(act, f"Class_{act}")
            row = [act, act_name]
            for pred in all_involved_classes:
                row.append(matrix[act][pred])
            writer.writerow(row)

    # 3. Top Confusions Analysis (Ranked misclassifications)
    confusions = []
    for act in actual_classes:
        act_name = class_names.get(act, f"Class_{act}")
        for pred, count in matrix[act].items():
            if act != pred and count > 0:
                pred_name = class_names.get(pred, f"Class_{pred}")
                confusions.append({
                    "actual_id": act,
                    "actual_name": act_name,
                    "pred_id": pred,
                    "pred_name": pred_name,
                    "count": count
                })

    confusions.sort(key=lambda x: x["count"], reverse=True)

    top_conf_csv = output_dir / "top_confusions.csv"
    with open(top_conf_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["actual_id", "actual_name", "predicted_id", "predicted_name", "misclassified_windows"])
        for c in confusions:
            writer.writerow([c["actual_id"], c["actual_name"], c["pred_id"], c["pred_name"], c["count"]])

    # 4. Human-readable Markdown Report
    report_md = output_dir / "confusion_report.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# WildSonic Model Confusion Matrix & Error Report\n\n")
        f.write("A confusion matrix details which species the model correctly identified and which species it confused with other classes.\n\n")
        f.write(f"- **Total Evaluable Windows Analyzed**: {len(predictions)}\n")
        f.write(f"- **Unique Classes in Ground Truth**: {len(actual_classes)}\n")
        f.write(f"- **Unique Classes Predicted by Model**: {len(predicted_classes)}\n\n")

        # Top 15 Misclassification Pairs
        f.write("## Top 15 Most Common Misclassifications (Errors)\n\n")
        top_rows = [
            [f"{c['actual_name']} (id={c['actual_id']})",
             f"{c['pred_name']} (id={c['pred_id']})",
             c["count"]]
            for c in confusions[:15]
        ]
        write_markdown_table(
            f,
            ["Ground Truth Species", "Falsely Predicted As", "Error Count"],
            ["left", "left", "right"],
            top_rows,
        )

        # Class-level summary: Precision & Recall proxy
        f.write("\n## Per-Class True Positives vs False Confusions\n\n")
        class_rows = []
        for act in sorted(list(actual_classes)):
            act_name = class_names.get(act, f"Class_{act}")
            total_act = sum(matrix[act].values())
            correct = matrix[act][act]
            miss_bg = matrix[act][126] if act != 126 else 0
            miss_other = total_act - correct - miss_bg
            class_rows.append([act, act_name, total_act, correct, miss_other, miss_bg])
        write_markdown_table(
            f,
            ["Class ID", "Species Name", "Total Windows", "True Positives (Correct)",
             "Confused as Other Species", "Missed as Background (126)"],
            ["center", "left", "right", "right", "right", "right"],
            class_rows,
        )

    print(f"[+] Confusion Matrix CSV: {matrix_csv}")
    print(f"[+] Top Confusions CSV  : {top_conf_csv}")
    print(f"[+] Markdown Report     : {report_md}")


def main():
    parser = argparse.ArgumentParser(description="Generate Confusion Matrix from live detection test outputs.")
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="Path to test output directory containing playback_timeline.csv and predictions_aligned.csv")
    parser.add_argument("--pack-dir", type=Path, default=Path(__file__).parent,
                        help="Path to pack directory containing class_labels.txt")
    args = parser.parse_args()

    class_names, events, predictions = load_data(args.run_dir, args.pack_dir)
    generate_confusion_matrix(class_names, events, predictions, args.run_dir)


if __name__ == "__main__":
    main()
