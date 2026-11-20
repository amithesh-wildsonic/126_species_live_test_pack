# WildSonic 126-Species Live MCU Detection Benchmark

This test pack contains the complete 126-species bird audio dataset and an automated, hardware-in-the-loop test harness for benchmarking the WildSonic MAX78000 edge firmware.

---

## Table of Contents
1. [Test Pack Structure](#1-test-pack-structure)
2. [What is Eval Windows (Evaluable Windows)?](#2-what-is-eval-windows-evaluable-windows)
3. [How to Read the Test Results](#3-how-to-read-the-test-results)
4. [How to Run the Test on Linux](#4-how-to-run-the-test-on-linux)
5. [How to Run the Test on Windows](#5-how-to-run-the-test-on-windows)
6. [How to Run the Test on macOS](#6-how-to-run-the-test-on-macos)
7. [Command-Line Options Reference](#7-command-line-options-reference)
8. [UART Echo / Asterisk Flood Protection (> 3 Seconds)](#8-uart-echo--asterisk-flood-protection--3-seconds)

---

## 1. Test Pack Structure

```
126_species_live_test_pack/
├── MANIFEST.csv                  # Maps each WAV file to its class ID, species name, and folder
├── class_labels.txt              # TSV(Tab-Separated Values) list of 126 bird species + Background (ID 126)
├── live_detection_test_runner.py # Automated test runner (ALSA/Windows audio + UART + OpenOCD)
├── README.md                     # Comprehensive documentation and usage guide
├── README.txt                    # Quick overview
└── audio_by_species/             # 126 folders (e.g., 000_Alexandrine_Parakeet to 125_Zitting_Cisticola)
    └── <Species_Name>/
        └── <Species_Name>_<Index>.wav   # 10 WAV files per species (1,260 files total, 48 kHz 16-bit PCM)
```

---

## 2. What is Eval Windows (Evaluable Windows)?

### The Problem: Rolling Hardware Buffers vs Playback Timelines
- The MAX78000 WildSonic firmware continuously samples audio through the microphone / I2S codec at **48,000 Hz, 16-bit mono**.
- The neural network operates on fixed **3.0-second windows** (exactly 144,000 audio samples).
- When audio is played from a host PC over speakers, the playback start time is **not synchronized** with the MCU's internal 3-second buffer clock.
- If a 3.0-second bird clip is played, it rarely aligns perfectly with a single MCU window. Instead, it typically spans across **two adjacent 3-second windows**:
  - For example: Window 1 captures the first 1.8 seconds of the bird song, and Window 2 captures the remaining 1.2 seconds of the bird song (along with 1.8 seconds of following silence).

### How Windows Are Categorized
To evaluate the model fairly and rigorously, the test runner categorizes every MCU prediction window into one of four states based on its time overlap with the audio playback:

```
Timeline:    |--- Silence ---|====== 3.0s Bird Audio ======|--- Silence ---|
MCU Buffers: [--- Win 1 ---] [------- Win 2 -------] [------- Win 3 -------]
Overlap:     Pure Silence     1.8s Bird / 1.2s Sil    1.2s Bird / 1.8s Sil
Status:      SILENCE_EVAL     EVALUABLE               EVALUABLE
```

1. **`EVALUABLE` (Eval Windows)**:
   - A window that overlaps with an active bird playback by **at least 1.0 second** ($\ge 33\%$ of the 3.0s window).
   - This ensures that a substantial, dominant portion of the vocalization was inside the CNN input buffer.
   - If a bird file is 3.0s long, it will typically produce **1 or 2 Eval Windows**. If repeats are configured ($\ge 2$), it produces more.

2. **`AMBIGUOUS` (Transition Windows)**:
   - A window that contains only a tiny sliver of bird audio (between **0.3s and 1.0s**) at the clip boundary.
   - Because 70% to 90% of the buffer is silence, expecting the CNN to detect a bird from a clipped fraction of a chirp would be unrealistic.
   - These windows are logged and checked for hits, but do not penalize the model as misses if the audio is mostly silence.

3. **`SILENCE_EVALUABLE`**:
   - A window that occurred during **pure background silence** ($\le 0.3$s overlap with any audio, and $\ge 1.5$s inside the silence gap).
   - Used to verify that the model correctly predicts **Background** (`class_id = 126`) and does not trigger false alarms when no birds are vocalizing.

4. **`UNMATCHED`**:
   - Windows recorded before the first audio event or after the test finished.

### Determining the Outcome of a Play
For each audio playback of a species:
- **`TOP1_HIT`**: At least one `EVALUABLE` window predicted the target species as **Top-1** (#1 highest confidence).
- **`TOP2_HIT`**: The target species was not Top-1, but appeared as **Top-2** in at least one `EVALUABLE` window.
- **`MISS`**: Evaluable windows were present, but the target species was neither Top-1 nor Top-2 (e.g., predicted another species or Background).
- **`NO_EVALUABLE_WINDOWS`**: The audio clip was too short to yield an evaluable window (0 in standard runs).

---

## 3. How to Read the Test Results

Every test execution creates an output folder (e.g., `full_126_species_run/`) containing six reports:

### 1. `summary_report.md`
The main human-readable executive dashboard formatted in aligned Markdown tables:
- **Top-1 Accuracy**: Percentage of plays where the correct species was the #1 prediction.
- **Top-2 Accuracy**: Percentage of plays where the correct species was in the Top-2 predictions. In field acoustic monitoring, Top-2 accuracy is critical because sibling species often share call patterns.
- **Silence False Positive Rate**: What percentage of pure silence intervals falsely triggered a bird detection instead of `Background` (`id=126`).
- **Audio Staging Health**: Maximum high-water mark of the 18-block external SRAM queue and count of lost samples (should be 0).
- **Per-Species Table**: Breakdown of plays, eval windows, hits, and accuracy per class.

### 2. `summary_report.json`
A machine-readable JSON summary for CI/CD pipelines containing exact metrics:
```json
{
  "target_species_count": 126,
  "total_audio_plays": 126,
  "top1_hits": 41,
  "top1_accuracy_pct": 32.54,
  "top2_hits": 15,
  "top2_accuracy_pct": 44.44,
  "misses": 70,
  "miss_rate_pct": 55.56,
  "no_evaluable_windows": 0,
  "silence_windows_evaluated": 58,
  "silence_false_positives": 15,
  "silence_false_positive_rate_pct": 25.86,
  "assert_interruption_count": 0,
  "staging_max_high_water_blocks": 17,
  "staging_lost_samples": 0
}
```

### 3. `per_species_report.csv`
A complete spreadsheet table with one row per bird species:
| Column | Description |
| :--- | :--- |
| `class_id` | Model integer class ID (0 to 125). |
| `species_name` | Official common species name (e.g. Alexandrine Parakeet). |
| `plays_completed` | Number of WAV file playback events for this species. |
| `evaluable_windows` | Total number of 3.0s CNN windows analyzed for this species. |
| `top1_hits` | Number of plays where this species was Top-1. |
| `top2_only_hits` | Number of plays where this species was Top-2 only. |
| `misses` | Number of plays where this species was missed. |
| `no_eval_windows` | Number of plays lacking evaluable windows (normally 0). |
| `top1_acc_pct` | Top-1 accuracy percentage ($\text{top1} / \text{plays} \times 100$). |
| `top2_acc_pct` | Cumulative Top-1 + Top-2 accuracy percentage. |
| `error_rate_pct` | Miss percentage. |

### 4. `playback_timeline.csv`
Timestamped log of every playback and silence event executed on the host:
- `event_id`, `event_type` (`AUDIO` or `SILENCE`), `species`, `filename`, `host_start_utc`, `host_end_utc`, `duration_sec`, `evaluable_windows`, `outcome`.

### 5. `predictions_aligned.csv`
Every 3.0s CNN inference window produced by the MAX78000, mapped to its corresponding timeline event:
- `window_id`: Sequential window index from MCU boot.
- `alignment_status`: `EVALUABLE`, `AMBIGUOUS`, `SILENCE_EVALUABLE`, or `UNMATCHED`.
- `matched_event_id`: ID of the timeline event this window covers.
- `top1_class_id`, `top1_name`, `top1_conf_pct`: Top-1 prediction details.
- `top2_class_id`, `top2_name`, `top2_conf_pct`: Top-2 prediction details.
- `cnn_us`: Hardware CNN execution time in microseconds (~6,273 µs).
- `recv_host_utc`: UTC timestamp when the host received the prediction over UART.

### 6. `uart_raw.log`
Complete, unfiltered serial capture from `/dev/ttyACM0` or `COMx` with millisecond host timestamps.

---

## 4. How to Run the Test on Linux

### 1. Requirements
```bash
sudo apt-get install -y alsa-utils openocd python3 python3-pip
pip3 install pyserial
sudo usermod -aG dialout $USER
```

### 2. Execution Examples
Navigate to the test pack directory:
```bash
cd /path/to/126_species_live_test_pack
```

- **Full 126-Species Benchmark** (~13 minutes):
  ```bash
  python3 live_detection_test_runner.py --output-dir ./full_126_run --files-per-species 1 --repeats 1 --silence-sec 3.5
  ```

- **Quick 5-Species Validation Run** (~30 seconds):
  ```bash
  python3 live_detection_test_runner.py --species-limit 5 --files-per-species 1 --repeats 1 --silence-sec 3.5
  ```

- **Specific Species Only**:
  ```bash
  python3 live_detection_test_runner.py --species "Alexandrine Parakeet, Ashy Drongo, Asian Koel" --repeats 2 --silence-sec 3.0
  ```

- **Custom Serial Port or OpenOCD Path**:
  ```bash
  python3 live_detection_test_runner.py --port /dev/ttyACM1 --openocd-scripts /usr/share/openocd/scripts
  ```

---

## 5. How to Run the Test on Windows

The test runner has native Windows support. Audio playback automatically uses Windows built-in `winsound` API (no external audio player required).

### 1. Requirements
1. **Python 3.8+**: Download from [python.org](https://www.python.org/downloads/) (check *"Add Python to PATH"* during install).
2. **Install pyserial**:
   ```cmd
   pip install pyserial
   ```
3. **Connect Hardware**:
   - Plug the MAX78000 board via USB.
   - Open **Device Manager** $\rightarrow$ **Ports (COM & LPT)** to find the COM port number (e.g., `COM3`, `COM4`, `COM5`).

### 2. Running via PowerShell or Command Prompt

#### Method A: Direct Serial Mode (Simplest, No OpenOCD Needed)
If you don't have OpenOCD installed on Windows, use `--skip-initial-reset` to connect directly to the MCU over the serial COM port:
```powershell
# In PowerShell:
cd C:\path\to\126_species_live_test_pack

# Quick 3-species test:
python live_detection_test_runner.py --port COM3 --skip-initial-reset --species-limit 3 --files-per-species 1 --repeats 1 --silence-sec 3.5

# Full 126-species benchmark:
python live_detection_test_runner.py --port COM3 --skip-initial-reset --files-per-species 1 --repeats 1 --silence-sec 3.5 --output-dir .\windows_results
```

#### Method B: With OpenOCD Hardware Reset (Recommended for CI/Automated Testing)
If you have OpenOCD installed on Windows (e.g., via xPack OpenOCD or Maxim SDK):
```powershell
python live_detection_test_runner.py `
  --port COM3 `
  --openocd-scripts "C:\MaximSDK\Tools\OpenOCD\scripts" `
  --files-per-species 1 `
  --repeats 1 `
  --silence-sec 3.5 `
  --output-dir .\windows_results
```

> **Tip for Windows Audio**: Ensure your PC default audio output device (speakers or headphones) is unmuted and positioned within 10–20 cm of the microphone on the MAX78000 board.

---

## 6. How to Run the Test on macOS

The test runner automatically detects macOS and plays WAV files using native `afplay`.

1. **Install pyserial**:
   ```bash
   pip3 install pyserial
   ```
2. **Find Serial Device**:
   ```bash
   ls /dev/cu.usbmodem*
   ```
3. **Run the Test**:
   ```bash
   python3 live_detection_test_runner.py --port /dev/cu.usbmodem14201 --skip-initial-reset --species-limit 5 --files-per-species 1 --silence-sec 3.5
   ```

---

## 7. Command-Line Options Reference

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--pack-dir` | Script directory | Path to folder with `MANIFEST.csv`, `class_labels.txt`, and `audio_by_species/`. |
| `--output-dir` | `test_run_<timestamp>` | Path where report CSVs, Markdown, and JSON will be saved. |
| `--port` | `/dev/ttyACM0` | Serial COM port connected to the MAX78000 UART (`COMx` on Windows). |
| `--baud` | `115200` | UART baud rate. |
| `--openocd-scripts` | `/home/amithesh/.local/opt/openocd/scripts` | Path to OpenOCD scripts directory containing `interface/` and `target/`. |
| `--skip-initial-reset`| `False` | Skip DAPLink reset before test (useful on Windows/Mac without OpenOCD). |
| `--playback-device` | `default` | ALSA audio device name on Linux (ignored on Windows/macOS). |
| `--species` | `None` (all) | Comma-separated list of species names or class IDs to test. |
| `--species-limit` | `None` (all 126) | Limit testing to the first N species. |
| `--files-per-species`| `10` | Number of WAV files per species to test (1 to 10). |
| `--repeats` | `1` | Number of times to play each WAV file. |
| `--silence-sec` | `3.0` | Duration (seconds) of background silence between playback events. |

---

## 8. UART Echo / Asterisk Flood Protection (> 3 Seconds)

### Why It Happens
On MAX78000 DAPLink USB-to-UART bridge interfaces, sending characters into the serial console or opening the serial port while another terminal emulator (e.g. Tabby, PuTTY, Minicom) is running can trigger an infinite hardware echo loop. When this occurs, the MCU's console input handler reflects incoming bytes, causing the serial port to continuously stream asterisks (`*`) and framing characters (`%*`):
```
[2026-11-19T09:58:45.110233Z] ****************************************************************************************************...
[2026-11-19T09:58:45.846914Z] ****************************************************************************************************...
```

### Automatic Safeguard Behavior
The test runner continuously monitors incoming UART lines:
1. **Detection**: If repetitive asterisks or echo noise dominate the incoming UART traffic continuously for **more than 3 seconds**, the test runner immediately trips its safety cutoff.
2. **Immediate Abort**: Audio playback (`aplay` / `winsound` / `afplay`) is killed within 50ms, and the serial port is closed to release the bus.
3. **User Action Prompt**: A clear prompt is displayed instructing the user to power-cycle the UART:
   ```
   ================================================================================
   [!] CRITICAL ERROR: UART SERIAL CORRUPTION / ECHO FLOOD DETECTED (> 3 SECONDS)!
   ================================================================================
   The serial transceiver on /dev/ttyACM0 (or COM port) is locked in an infinite
   character echo loop, flooding the interface with asterisks (*) / framing noise.

   >>> THE TEST HAS BEEN TERMINATED IMMEDIATELY TO PREVENT DATA CORRUPTION. <<<

   ACTION REQUIRED:
     1. UNPLUG the USB cable from the MAX78000 board to power-cycle the UART.
     2. Wait 3 to 5 seconds for capacitors and USB bus to discharge.
     3. RE-PLUG the USB cable into the board.
     4. Ensure no other application (Tabby, Minicom, PuTTY, Screen) is attached to the port.
     5. Re-run the test command.
   ================================================================================
   ```

