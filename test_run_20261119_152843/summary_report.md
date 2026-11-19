# WildSonic Live MCU Detection Test Report

- **Execution Time**: 2026-11-19T10:01:01.349206+00:00
- **Species Tested**: 1
- **Total Audio Plays**: 20
- **Assert Interruptions**: 0

## Overall Detection Accuracy

| Metric                          |   Count | Percentage |
| :------------------------------ | ------: | ---------: |
| **Top-1 Hits**                  |  0 / 20 |   **0.0%** |
| **Top-2 Hits (Top-1 or Top-2)** |  0 / 20 |   **0.0%** |
| **Misses**                      |  0 / 20 |       0.0% |
| **Short / No-Eval Windows**     | 20 / 20 |     100.0% |

## Silence Interval Analysis (False Positive Rejection)

| Metric                                 |    Value |
| :------------------------------------- | -------: |
| Total Silence Windows Evaluated        |        0 |
| Correct Background Rejections (id=126) |        0 |
| False Positive Bird Detections         |        0 |
| **Silence False Positive Rate**        | **0.0%** |

## Audio Staging & Queue Health

- **Max OCM Staging Ring High-Water Mark**: 0 / 18 blocks
- **Staging Lost / Overflow Samples**: 0 samples
- **Assert Events**: 0

## Per-Species Performance Summary

| Class ID | Species Name         | Plays | Eval Windows | Top-1 Hits | Top-2 Only | Misses | Top-1 Acc | Top-2 Acc |
| :------: | :------------------- | :---: | :----------: | :--------: | :--------: | :----: | --------: | --------: |
|    0     | Alexandrine Parakeet |   20  |      0       |     0      |     0      |   0    |      0.0% |      0.0% |
