# WildSonic Live MCU Detection Test Report

- **Execution Time**: 2026-11-19T09:24:58.452159+00:00
- **Species Tested**: 3
- **Total Audio Plays**: 3
- **Assert Interruptions**: 0

## Overall Detection Accuracy

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Top-1 Hits** | 1 / 3 | **33.3%** |
| **Top-2 Hits (Top1 or Top2)** | 2 / 3 | **66.7%** |
| **Misses** | 1 / 3 | 33.3% |
| **Short/No-Eval Windows** | 0 / 3 | 0.0% |

## Silence Interval Analysis (False Positive Rejection)

| Metric | Value |
| :--- | :--- |
| Total Silence Windows Evaluated | 4 |
| Correct Background Rejections (id=126) | 2 |
| False Positive Bird Detections | 2 |
| **Silence False Positive Rate** | **50.0%** |

## Audio Staging & Queue Health

- **Max OCM Staging Ring High-Water Mark**: 16 / 18 blocks
- **Staging Lost / Overflow Samples**: 0 samples
- **Assert Events**: 0

## Per-Species Performance Summary

| Class ID | Species Name | Plays | Eval Windows | Top-1 Hits | Top-2 Only | Misses | Top-1 Acc | Top-2 Acc |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | Alexandrine Parakeet | 1 | 1 | 0 | 0 | 1 | 0.0% | 0.0% |
| 1 | Ashy Drongo | 1 | 1 | 1 | 0 | 0 | 100.0% | 100.0% |
| 2 | Ashy Prinia | 1 | 1 | 0 | 1 | 0 | 0.0% | 100.0% |
