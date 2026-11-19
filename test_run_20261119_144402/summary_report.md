# WildSonic Live MCU Detection Test Report

- **Execution Time**: 2026-11-19T09:15:16.964058+00:00
- **Species Tested**: 5
- **Total Audio Plays**: 10
- **Assert Interruptions**: 0

## Overall Detection Accuracy

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Top-1 Hits** | 0 / 10 | **0.0%** |
| **Top-2 Hits (Top1 or Top2)** | 0 / 10 | **0.0%** |
| **Misses** | 1 / 10 | 10.0% |
| **Short/No-Eval Windows** | 9 / 10 | 90.0% |

## Silence Interval Analysis (False Positive Rejection)

| Metric | Value |
| :--- | :--- |
| Total Silence Windows Evaluated | 1 |
| Correct Background Rejections (id=126) | 1 |
| False Positive Bird Detections | 0 |
| **Silence False Positive Rate** | **0.0%** |

## Audio Staging & Queue Health

- **Max OCM Staging Ring High-Water Mark**: 17 / 18 blocks
- **Staging Lost / Overflow Samples**: 0 samples
- **Assert Events**: 0

## Per-Species Performance Summary

| Class ID | Species Name | Plays | Eval Windows | Top-1 Hits | Top-2 Only | Misses | Top-1 Acc | Top-2 Acc |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | Alexandrine Parakeet | 2 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 1 | Ashy Drongo | 2 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 2 | Ashy Prinia | 2 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 3 | Asian Fairy-bluebird | 2 | 0 | 0 | 0 | 0 | 0.0% | 0.0% |
| 4 | Asian Koel | 2 | 1 | 0 | 0 | 1 | 0.0% | 0.0% |
