WildSonic 126-Species Live MCU Detection Test Pack
===================================================

This directory contains the self-contained live detection benchmark for the MAX78000
WildSonic firmware, including all 126 bird species (1,260 WAV files), manifest metadata,
and the cross-platform hardware-in-the-loop test runner.

For full documentation, see README.md in this directory:
- Complete explanation of 'Eval Windows' (evaluable rolling CNN windows)
- Comprehensive guide to reading all generated CSV, Markdown, and JSON reports
- Step-by-step instructions for running on Linux (ALSA), Windows (PowerShell/winsound), and macOS
- Built-in UART echo/asterisk flood protection (> 3s automatic abort & power-cycle prompt)
- Full command-line options reference

Quick start (Linux):
  ./live_detection_test_runner.py --species-limit 5 --files-per-species 1 --silence-sec 3.5

Quick start (Windows PowerShell):
  python live_detection_test_runner.py --port COM3 --skip-initial-reset --species-limit 5 --files-per-species 1 --silence-sec 3.5
