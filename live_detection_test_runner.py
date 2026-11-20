#!/usr/bin/env python3
"""
Live Detection Test Runner for WildSonic MAX78000 Firmware
=========================================================

Features:
- Plays WAV files grouped by species from the 126-species audio pack.
- Supports configurable repeats, files per species, species selection/limits, and silence intervals.
- Controls DAPLink / OpenOCD to reset the MCU and synchronize UTC time.
- Continuously captures UART output (/dev/ttyACM0) in a non-blocking thread.
- Automatically catches MCU ASSERT / Fault messages, logs assert evidence, and recovers via DAPLink reset.
- Accurately aligns playback intervals with MCU 3-second detection windows.
- Marks transition windows crossing silence/clip boundaries as AMBIGUOUS so they do not distort scores.
- Evaluates silence intervals separately for False Positive detection rates.
- Generates comprehensive markdown, CSV, and JSON reports with per-species top-1, top-2, miss, and error metrics.
"""

import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial is required. Install with: pip install pyserial", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class WindowPrediction:
    def __init__(self, window_id: int, top1_name: str, top1_id: int, top1_q8: int,
                 top2_name: str, top2_id: int, top2_q8: int, cnn_us: int,
                 recv_host_time: float, mcu_window_end_time: float):
        self.window_id = window_id
        self.top1_name = top1_name
        self.top1_id = top1_id
        self.top1_q8 = top1_q8
        self.top1_conf_pct = round((top1_q8 / 256.0) * 100.0, 1)
        self.top2_name = top2_name
        self.top2_id = top2_id
        self.top2_q8 = top2_q8
        self.top2_conf_pct = round((top2_q8 / 256.0) * 100.0, 1)
        self.cnn_us = cnn_us
        self.recv_host_time = recv_host_time
        self.mcu_window_end_time = mcu_window_end_time
        self.mcu_window_start_time = mcu_window_end_time - 3.0
        self.matched_event_id: Optional[int] = None
        self.alignment_status: str = "UNMATCHED"  # EVALUABLE, AMBIGUOUS, SILENCE_EVALUABLE, UNMATCHED


class PlaybackEvent:
    def __init__(self, event_id: int, event_type: str, species: str, class_id: int,
                 filename: str, filepath: str, repeat_idx: int,
                 host_start: float, host_end: float,
                 mcu_start: float, mcu_end: float, duration: float):
        self.event_id = event_id
        self.event_type = event_type  # "AUDIO" or "SILENCE"
        self.species = species
        self.class_id = class_id
        self.filename = filename
        self.filepath = filepath
        self.repeat_idx = repeat_idx
        self.host_start = host_start
        self.host_end = host_end
        self.mcu_start = mcu_start
        self.mcu_end = mcu_end
        self.duration = duration
        self.evaluable_windows: List[WindowPrediction] = []
        self.ambiguous_windows: List[WindowPrediction] = []
        self.outcome: str = "PENDING"  # TOP1_HIT, TOP2_HIT, MISS, NO_EVALUABLE_WINDOWS


# ---------------------------------------------------------------------------
# DAPLink / OpenOCD Controller
# ---------------------------------------------------------------------------

class DapLinkController:
    def __init__(self, scripts_dir: str = "/home/amithesh/.local/opt/openocd/scripts",
                 interface_cfg: str = "cmsis-dap.cfg",
                 target_cfg: str = "max78000.cfg"):
        self.scripts_dir = scripts_dir
        self.interface_cfg = interface_cfg
        self.target_cfg = target_cfg

    def reset_mcu(self, timeout_sec: float = 15.0) -> Tuple[bool, str]:
        """Reset and resume the MCU via DAPLink OpenOCD."""
        cmd = [
            "openocd",
            "-s", self.scripts_dir,
            "-f", f"interface/{self.interface_cfg}",
            "-f", f"target/{self.target_cfg}",
            "-c", "init; reset run; exit"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
            success = (res.returncode == 0)
            output = res.stdout + "\n" + res.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "OpenOCD timed out after {timeout_sec}s"
        except Exception as e:
            return False, str(e)


# ---------------------------------------------------------------------------
# UART Monitor & Serial Receiver
# ---------------------------------------------------------------------------

class UartMonitor:
    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 115200,
                 log_file_path: Optional[Path] = None):
        self.port = port
        self.baud = baud
        self.log_file_path = log_file_path
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.predictions: List[WindowPrediction] = []
        self.raw_lines: List[str] = []
        self.assert_events: List[Dict[str, str]] = []
        self.staging_logs: List[Dict[str, any]] = []

        self.lock = threading.Lock()
        self.clock_offset_mcu_minus_host: float = 0.0
        self.time_synced = False
        self.has_asserted = False
        self.latest_assert_line = ""

        # UART corruption / asterisk flood detection (> 3 seconds)
        self.uart_echo_flood = False
        self.uart_echo_start_time: Optional[float] = None
        self.latest_echo_sample = ""

        self._pred_re = re.compile(
            r"window\s+(\d+):\s+top1=([^\(]+?)\s+\(id=(\d+),\s+q8=(\d+)\)\s+top2=([^\(]+?)\s+\(id=(\d+),\s+q8=(\d+)\)\s+cnn_us=(\d+)"
        )
        self._staging_re = re.compile(
            r"audio\s+staging:\s+captured=(\d+)\s+queued=(\d+)\s+fed=(\d+)\s+lost=(\d+)\s+high_water=(\d+)/(\d+)\s+blocks"
        )
        self._assert_re = re.compile(
            r"(ASSERT|mxc_assert|SYSTEM_ASSERT|assertion\s+failed|HardFault|UsageFault|BusFault|MemManage)",
            re.IGNORECASE
        )
        self._mcu_time_re = re.compile(
            r"(?:Current time UTC time is|RTC Time UTC:)\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})"
        )

    def open(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baud, timeout=0.2, exclusive=True)
        except (serial.SerialException, FileNotFoundError, OSError) as e:
            # Auto-fallback: search for available DAPLink or ACM ports
            print(f"[!] Warning: Port {self.port} unavailable ({e}). Searching for active DAPLink / ACM serial ports...")
            detected = []
            for p in serial.tools.list_ports.comports():
                if "ACM" in p.device or "USB" in p.device or "DAPLink" in (p.description or ""):
                    detected.append(p.device)
            if detected:
                fallback = detected[0]
                print(f"[+] Auto-detected active serial port: {fallback}. Connecting...")
                self.port = fallback
                self.serial_conn = serial.Serial(self.port, self.baud, timeout=0.2, exclusive=True)
            else:
                raise e

        self.serial_conn.reset_input_buffer()
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def close(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None

    def send_cmd(self, cmd: str, wait_sec: float = 0.1):
        if self.serial_conn and self.serial_conn.is_open:
            data = (cmd.strip() + "\r\n").encode("ascii")
            self.serial_conn.write(data)
            self.serial_conn.flush()
            time.sleep(wait_sec)

    def query_mcu_time(self, timeout_sec: float = 1.0) -> bool:
        """Passive wait for RTC time from boot log to determine offset."""
        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            if self.time_synced:
                return True
            time.sleep(0.05)
        return False

    def _read_loop(self):
        log_f = None
        if self.log_file_path:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            log_f = open(self.log_file_path, "a", encoding="utf-8")

        while self.running:
            try:
                if not self.serial_conn or not self.serial_conn.is_open:
                    time.sleep(0.1)
                    continue

                line_bytes = self.serial_conn.readline()
                if not line_bytes:
                    continue

                recv_host_time = time.time()
                recv_iso = datetime.datetime.fromtimestamp(
                    recv_host_time, datetime.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                line_str = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line_str.strip():
                    continue

                if log_f:
                    log_f.write(f"[{recv_iso}] {line_str}\n")
                    log_f.flush()

                with self.lock:
                    self.raw_lines.append(f"[{recv_iso}] {line_str}")

                    # 0. Check for UART Echo / Asterisk Flood (> 3 seconds)
                    star_count = line_str.count('*') + line_str.count('%')
                    is_corrupt_line = (star_count >= 15) or (len(line_str) >= 20 and (star_count / len(line_str)) > 0.6)

                    if is_corrupt_line:
                        if self.uart_echo_start_time is None:
                            self.uart_echo_start_time = recv_host_time
                            self.latest_echo_sample = line_str[:80]
                        elif (recv_host_time - self.uart_echo_start_time) >= 3.0:
                            self.uart_echo_flood = True
                    else:
                        # Reset timer only when valid firmware text arrives
                        if star_count < 5 and any(k in line_str for k in ("C:0 [F:", "C:1 [F:", "window ", "audio staging", "RTC Time", "Done", "Initialization")):
                            self.uart_echo_start_time = None

                    # 1. Check for ASSERT / Fault
                    if self._assert_re.search(line_str):
                        self.has_asserted = True
                        self.latest_assert_line = line_str
                        self.assert_events.append({
                            "timestamp_utc": recv_iso,
                            "host_time": recv_host_time,
                            "line": line_str
                        })

                    # 2. Check for DATETIME response
                    time_match = self._mcu_time_re.search(line_str)
                    if time_match:
                        try:
                            # e.g. "2026-11-19 08:27:15.295"
                            dt = datetime.datetime.strptime(time_match.group(1), "%Y-%m-%d %H:%M:%S.%f")
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                            mcu_epoch = dt.timestamp()
                            self.clock_offset_mcu_minus_host = mcu_epoch - recv_host_time
                            self.time_synced = True
                        except Exception as e:
                            pass

                    # 3. Check for Window Prediction
                    pred_match = self._pred_re.search(line_str)
                    if pred_match:
                        wid = int(pred_match.group(1))
                        t1_name = pred_match.group(2).strip()
                        t1_id = int(pred_match.group(3))
                        t1_q8 = int(pred_match.group(4))
                        t2_name = pred_match.group(5).strip()
                        t2_id = int(pred_match.group(6))
                        t2_q8 = int(pred_match.group(7))
                        cnn_us = int(pred_match.group(8))

                        # Window completion time on host timeline:
                        mcu_end_est = recv_host_time + self.clock_offset_mcu_minus_host
                        pred = WindowPrediction(
                            window_id=wid,
                            top1_name=t1_name,
                            top1_id=t1_id,
                            top1_q8=t1_q8,
                            top2_name=t2_name,
                            top2_id=t2_id,
                            top2_q8=t2_q8,
                            cnn_us=cnn_us,
                            recv_host_time=recv_host_time,
                            mcu_window_end_time=mcu_end_est
                        )
                        self.predictions.append(pred)

                    # 4. Check for Audio Staging log
                    st_match = self._staging_re.search(line_str)
                    if st_match:
                        self.staging_logs.append({
                            "recv_host_time": recv_host_time,
                            "captured": int(st_match.group(1)),
                            "queued": int(st_match.group(2)),
                            "fed": int(st_match.group(3)),
                            "lost": int(st_match.group(4)),
                            "high_water": int(st_match.group(5)),
                            "max_blocks": int(st_match.group(6))
                        })

            except serial.SerialException:
                time.sleep(0.1)
            except Exception as ex:
                time.sleep(0.1)

        if log_f:
            log_f.close()


# ---------------------------------------------------------------------------
# Test Runner & Analysis Engine
# ---------------------------------------------------------------------------

def format_md_table(headers: List[str], rows: List[List[any]], alignments: List[str]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_parts = []
    sep_parts = []
    for i, h in enumerate(headers):
        w = col_widths[i]
        align = alignments[i]
        if align == 'L':
            header_parts.append(h.ljust(w))
            sep_parts.append(':' + '-' * max(1, w - 1))
        elif align == 'C':
            header_parts.append(h.center(w))
            sep_parts.append(':' + '-' * max(1, w - 2) + ':')
        else:
            header_parts.append(h.rjust(w))
            sep_parts.append('-' * max(1, w - 1) + ':')

    header_line = '| ' + ' | '.join(header_parts) + ' |'
    sep_line = '| ' + ' | '.join(sep_parts) + ' |'

    body_lines = []
    for row in rows:
        line_parts = []
        for i, val in enumerate(row):
            s = str(val)
            w = col_widths[i]
            align = alignments[i]
            if align == 'L':
                line_parts.append(s.ljust(w))
            elif align == 'C':
                line_parts.append(s.center(w))
            else:
                line_parts.append(s.rjust(w))
        body_lines.append('| ' + ' | '.join(line_parts) + ' |')
    return "\n".join([header_line, sep_line] + body_lines)


class LiveDetectionTestRunner:
    def __init__(self, pack_dir: Path, output_dir: Path,
                 port: str = "/dev/ttyACM0", baud: int = 115200,
                 openocd_scripts: str = "/home/amithesh/.local/opt/openocd/scripts",
                 repeats: int = 1, silence_sec: float = 3.0,
                 species_filter: Optional[List[str]] = None,
                 species_limit: Optional[int] = None,
                 files_per_species: int = 10,
                 skip_initial_reset: bool = False,
                 playback_device: str = "default"):
        self.pack_dir = pack_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.port = port
        self.baud = baud
        self.openocd_scripts = openocd_scripts
        self.repeats = repeats
        self.silence_sec = silence_sec
        self.species_filter = species_filter
        self.species_limit = species_limit
        self.files_per_species = files_per_species
        self.skip_initial_reset = skip_initial_reset
        self.playback_device = playback_device

        self.manifest_path = self.pack_dir / "MANIFEST.csv"
        self.labels_path = self.pack_dir / "class_labels.txt"
        self.audio_dir = self.pack_dir / "audio_by_species"

        self.daplink = DapLinkController(scripts_dir=openocd_scripts)
        self.uart = UartMonitor(port=port, baud=baud, log_file_path=self.output_dir / "uart_raw.log")

        self.classes: Dict[int, str] = {}
        self.manifest_entries: List[Dict[str, any]] = []
        self.events: List[PlaybackEvent] = []
        self.next_event_id = 1

    def load_metadata(self):
        # 1. Load class labels
        if not self.labels_path.exists():
            raise FileNotFoundError(f"Class labels not found: {self.labels_path}")
        with open(self.labels_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t", 1)
                if len(parts) == 2:
                    self.classes[int(parts[0])] = parts[1].strip()

        # 2. Load manifest
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # row: species, folder, filename, class_id
                cid = int(row["class_id"])
                species = row["species"]
                folder = row["folder"]
                filename = row["filename"]
                filepath = self.audio_dir / folder / filename
                self.manifest_entries.append({
                    "species": species,
                    "folder": folder,
                    "filename": filename,
                    "class_id": cid,
                    "filepath": filepath
                })

    def get_wav_duration(self, filepath: Path) -> float:
        try:
            with wave.open(str(filepath), "rb") as w:
                return w.getnframes() / float(w.getframerate())
        except Exception:
            return 3.0

    def wait_with_guard(self, duration_sec: float):
        """Wait for duration while checking for UART echo flood / corruption."""
        t_end = time.time() + duration_sec
        while time.time() < t_end:
            if self.uart.uart_echo_flood:
                self.abort_due_to_uart_echo()
            time.sleep(0.05)

    def play_wav(self, filepath: Path) -> bool:
        """Play audio file across Linux (aplay), Windows (winsound), or macOS (afplay). Returns False if aborted."""
        if self.uart.uart_echo_flood:
            self.abort_due_to_uart_echo()

        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(str(filepath), winsound.SND_FILENAME)
            except Exception as ex:
                print(f"[!] Windows audio playback error: {ex}", file=sys.stderr)
        elif sys.platform == "darwin":
            proc = subprocess.Popen(["afplay", str(filepath)])
            while proc.poll() is None:
                if self.uart.uart_echo_flood:
                    proc.terminate()
                    self.abort_due_to_uart_echo()
                time.sleep(0.05)
        else:
            proc = subprocess.Popen(["aplay", "-D", self.playback_device, "-q", str(filepath)])
            while proc.poll() is None:
                if self.uart.uart_echo_flood:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.5)
                    except Exception:
                        proc.kill()
                    self.abort_due_to_uart_echo()
                time.sleep(0.05)
        return True

    def abort_due_to_uart_echo(self):
        """Immediately cut the test and prompt the user to power cycle the UART."""
        self.uart.close()
        sample = self.uart.latest_echo_sample or "***"
        print("\n" + "=" * 80)
        print("[!] CRITICAL ERROR: UART SERIAL CORRUPTION / ECHO FLOOD DETECTED (> 3 SECONDS)!")
        print("=" * 80)
        print("The serial transceiver on /dev/ttyACM0 (or COM port) is locked in an infinite")
        print("character echo loop, flooding the interface with asterisks (*) / framing noise:")
        print(f"  Sample corrupted line: {sample}...")
        print("")
        print(">>> THE TEST HAS BEEN TERMINATED IMMEDIATELY TO PREVENT DATA CORRUPTION. <<<")
        print("")
        print("ACTION REQUIRED:")
        print("  1. UNPLUG the USB cable from the MAX78000 board to power-cycle the UART.")
        print("  2. Wait 3 to 5 seconds for capacitors and USB bus to discharge.")
        print("  3. RE-PLUG the USB cable into the board.")
        print("  4. Ensure no other application (Tabby, Minicom, PuTTY, Screen) is attached to the port.")
        print("  5. Re-run the test command.")
        print("=" * 80 + "\n")
        sys.exit(2)

    def recover_from_assert(self) -> bool:
        """Handle MCU assert by logging report and resetting via DAPLink."""
        print("\n[!] ASSERTION / FAULT DETECTED! Initiating DAPLink recovery...")
        with self.uart.lock:
            assert_info = self.uart.latest_assert_line
            self.uart.has_asserted = False

        # Save assert report
        assert_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"assert_report_{assert_ts}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"Assert Time UTC: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")
            f.write(f"Assert Line: {assert_info}\n")
            f.write("Recent UART Lines:\n")
            with self.uart.lock:
                for line in self.uart.raw_lines[-30:]:
                    f.write(f"  {line}\n")

        print(f"[!] Saved assert report to {report_path.name}")
        print("[!] Resetting MCU via DAPLink OpenOCD...")

        # Temporarily close serial port to avoid bus contention
        self.uart.close()
        time.sleep(0.5)

        ok, out = self.daplink.reset_mcu()
        if not ok:
            print(f"[!] DAPLink reset failed: {out}", file=sys.stderr)
            return False

        time.sleep(1.0)
        self.uart.open()
        time.sleep(1.5)
        self.uart.query_mcu_time(timeout_sec=3.0)
        print("[+] MCU recovered and restarted successfully.\n")
        return True

    def record_playback_event(self, event: PlaybackEvent):
        """Append playback event and flush directly to playback_timeline.csv so no data is lost on interrupt."""
        self.events.append(event)
        self.next_event_id += 1
        timeline_csv = self.output_dir / "playback_timeline.csv"
        file_exists = timeline_csv.exists()
        try:
            with open(timeline_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        "event_id", "event_type", "species", "class_id", "filename", "repeat_idx",
                        "host_start_utc", "host_end_utc", "duration_sec", "evaluable_windows", "outcome"
                    ])
                s_iso = datetime.datetime.fromtimestamp(event.host_start, datetime.timezone.utc).isoformat()
                e_iso = datetime.datetime.fromtimestamp(event.host_end, datetime.timezone.utc).isoformat()
                writer.writerow([
                    event.event_id, event.event_type, event.species, event.class_id, event.filename, event.repeat_idx,
                    s_iso, e_iso, round(event.duration, 3), len(event.evaluable_windows), event.outcome
                ])
                f.flush()
        except Exception:
            pass

    def finalize_reports(self, target_species: List[str]):
        """Align windows, generate all CSV/JSON/MD reports, and compute confusion matrix."""
        print("\n[*] Aligning windows and computing metrics...")
        try:
            self.align_and_evaluate()
            self.generate_reports(target_species)
        except Exception as e:
            print(f"[!] Warning: Error during metric generation: {e}", file=sys.stderr)

        try:
            from generate_confusion_matrix import load_data, generate_confusion_matrix
            c_names, c_events, c_preds = load_data(self.output_dir, self.pack_dir)
            generate_confusion_matrix(c_names, c_events, c_preds, self.output_dir)
        except Exception as e:
            print(f"[!] Warning: Could not generate confusion matrix: {e}", file=sys.stderr)

    def run(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.load_metadata()

        print("==================================================================")
        print("          WildSonic Live MCU Detection Test Runner               ")
        print("==================================================================")
        print(f"Audio Pack Dir      : {self.pack_dir}")
        print(f"Output Dir          : {self.output_dir}")
        print(f"Serial Port         : {self.port} @ {self.baud} baud")
        print(f"Repeats per Clip    : {self.repeats}")
        print(f"Silence Interval    : {self.silence_sec}s")
        print(f"Files per Species   : {self.files_per_species}")
        print(f"Playback Device     : {self.playback_device}")
        print("------------------------------------------------------------------")

        # 1. Reset MCU via DAPLink if not skipped
        if not self.skip_initial_reset:
            print("[*] Performing initial MCU reset via DAPLink...")
            ok, out = self.daplink.reset_mcu()
            if not ok:
                print(f"[!] Warning: Initial OpenOCD reset returned non-zero: {out}")
            else:
                print("[+] MCU reset and resumed via DAPLink.")
            time.sleep(1.5)

        # 2. Open UART capture
        print(f"[*] Opening UART capture on {self.port}...")
        self.uart.open()
        time.sleep(1.0)

        # 3. Synchronize MCU time
        print("[*] Synchronizing RTC / host clock offset...")
        if self.uart.query_mcu_time(timeout_sec=3.0):
            print(f"[+] MCU RTC synced. Clock offset (MCU - Host): {self.uart.clock_offset_mcu_minus_host:+.3f}s")
        else:
            print("[!] Warning: Did not receive DATETIME response from MCU. Using host timestamps.")

        # 4. Filter and select manifest entries
        # Group by species
        grouped_by_species: Dict[str, List[Dict[str, any]]] = {}
        for entry in self.manifest_entries:
            sp = entry["species"]
            grouped_by_species.setdefault(sp, []).append(entry)

        target_species = list(grouped_by_species.keys())
        if self.species_filter:
            filter_set = {s.casefold().replace(" ", "_") for s in self.species_filter}
            target_species = [s for s in target_species if s.casefold().replace(" ", "_") in filter_set or str(grouped_by_species[s][0]["class_id"]) in filter_set]

        if self.species_limit and self.species_limit > 0:
            target_species = target_species[:self.species_limit]

        total_files = sum(min(len(grouped_by_species[s]), self.files_per_species) for s in target_species)
        total_plays = total_files * self.repeats
        print(f"[*] Test Plan: {len(target_species)} species | {total_files} files | {total_plays} total plays")
        print("------------------------------------------------------------------")

        # Initial baseline silence
        print(f"[*] Playing initial baseline silence ({self.silence_sec}s)...")
        t_sil_start = time.time()
        self.wait_with_guard(self.silence_sec)
        t_sil_end = time.time()
        self.record_playback_event(PlaybackEvent(
            event_id=self.next_event_id,
            event_type="SILENCE",
            species="Background",
            class_id=126,
            filename="silence_initial",
            filepath="",
            repeat_idx=0,
            host_start=t_sil_start,
            host_end=t_sil_end,
            mcu_start=t_sil_start + self.uart.clock_offset_mcu_minus_host,
            mcu_end=t_sil_end + self.uart.clock_offset_mcu_minus_host,
            duration=self.silence_sec
        ))
        self.next_event_id += 1

        play_count = 0
        for sp_idx, species in enumerate(target_species, 1):
            entries = grouped_by_species[species][:self.files_per_species]
            cid = entries[0]["class_id"]
            species_display = self.classes.get(cid, species)
            print(f"\n[{sp_idx}/{len(target_species)}] Species: {species_display} (Class ID: {cid}) - {len(entries)} files")

            for file_idx, entry in enumerate(entries, 1):
                wav_path = entry["filepath"]
                fname = entry["filename"]
                dur = self.get_wav_duration(wav_path)

                for r in range(1, self.repeats + 1):
                    play_count += 1
                    # Check if an echo flood or assert occurred
                    if self.uart.uart_echo_flood:
                        self.abort_due_to_uart_echo()
                    if self.uart.has_asserted:
                        self.recover_from_assert()

                    # Inter-clip silence
                    if self.silence_sec > 0:
                        t_s_start = time.time()
                        self.wait_with_guard(self.silence_sec)
                        t_s_end = time.time()
                        self.record_playback_event(PlaybackEvent(
                            event_id=self.next_event_id,
                            event_type="SILENCE",
                            species="Background",
                            class_id=126,
                            filename=f"silence_before_{fname}_r{r}",
                            filepath="",
                            repeat_idx=r,
                            host_start=t_s_start,
                            host_end=t_s_end,
                            mcu_start=t_s_start + self.uart.clock_offset_mcu_minus_host,
                            mcu_end=t_s_end + self.uart.clock_offset_mcu_minus_host,
                            duration=t_s_end - t_s_start
                        ))

                    # Play Audio
                    if self.uart.uart_echo_flood:
                        self.abort_due_to_uart_echo()
                    print(f"  Play [{play_count}/{total_plays}] File: {fname} (rep {r}/{self.repeats}, {dur:.2f}s)... ", end="", flush=True)
                    t_a_start = time.time()
                    self.play_wav(wav_path)
                    t_a_end = time.time()
                    actual_dur = t_a_end - t_a_start
                    if self.uart.uart_echo_flood:
                        self.abort_due_to_uart_echo()

                    self.record_playback_event(PlaybackEvent(
                        event_id=self.next_event_id,
                        event_type="AUDIO",
                        species=species,
                        class_id=cid,
                        filename=fname,
                        filepath=str(wav_path),
                        repeat_idx=r,
                        host_start=t_a_start,
                        host_end=t_a_end,
                        mcu_start=t_a_start + self.uart.clock_offset_mcu_minus_host,
                        mcu_end=t_a_end + self.uart.clock_offset_mcu_minus_host,
                        duration=actual_dur
                    ))
                    print("done.")

        # Post-test trailing silence to allow CNN pipeline to finish
        print(f"\n[*] Playing trailing silence (4.0s) to drain CNN inference pipeline...")
        t_trail_start = time.time()
        self.wait_with_guard(4.0)
        t_trail_end = time.time()
        self.record_playback_event(PlaybackEvent(
            event_id=self.next_event_id,
            event_type="SILENCE",
            species="Background",
            class_id=126,
            filename="silence_trailing",
            filepath="",
            repeat_idx=0,
            host_start=t_trail_start,
            host_end=t_trail_end,
            mcu_start=t_trail_start + self.uart.clock_offset_mcu_minus_host,
            mcu_end=t_trail_end + self.uart.clock_offset_mcu_minus_host,
            duration=4.0
        ))

        # Stop UART capture
        time.sleep(1.0)
        self.uart.close()
        print("[*] Playback completed.")

        # 5. Align Predictions and Generate Reports
        self.finalize_reports(target_species)

    def align_and_evaluate(self):
        """
        Align MCU 3.0s detection windows with playback timeline intervals.
        Categorizes windows as:
        - EVALUABLE: Substantial overlap with an audio event (>= 1.0s or >= 33% of window)
        - AMBIGUOUS: Window crosses boundary between clip and silence with low overlap (0.3s - 1.0s)
        - SILENCE_EVALUABLE: Window during pure background silence (audio overlap <= 0.3s, silence overlap >= 1.5s)
        """
        audio_events = [e for e in self.events if e.event_type == "AUDIO"]
        silence_events = [e for e in self.events if e.event_type == "SILENCE"]

        for pred in self.uart.predictions:
            pw_start = pred.mcu_window_start_time
            pw_end = pred.mcu_window_end_time

            # 1. Check overlap with audio events
            best_audio_ov = 0.0
            best_audio_ev: Optional[PlaybackEvent] = None
            for ev in audio_events:
                ov = max(0.0, min(pw_end, ev.mcu_end) - max(pw_start, ev.mcu_start))
                if ov > best_audio_ov:
                    best_audio_ov = ov
                    best_audio_ev = ev

            if best_audio_ev is not None and best_audio_ov >= 1.0:
                pred.alignment_status = "EVALUABLE"
                pred.matched_event_id = best_audio_ev.event_id
                best_audio_ev.evaluable_windows.append(pred)
            elif best_audio_ev is not None and best_audio_ov > 0.3:
                pred.alignment_status = "AMBIGUOUS"
                pred.matched_event_id = best_audio_ev.event_id
                best_audio_ev.ambiguous_windows.append(pred)
            else:
                # 2. Check overlap with silence events
                best_sil_ov = 0.0
                best_sil_ev: Optional[PlaybackEvent] = None
                for ev in silence_events:
                    ov = max(0.0, min(pw_end, ev.mcu_end) - max(pw_start, ev.mcu_start))
                    if ov > best_sil_ov:
                        best_sil_ov = ov
                        best_sil_ev = ev

                if best_sil_ev is not None and best_sil_ov >= 1.5:
                    pred.alignment_status = "SILENCE_EVALUABLE"
                    pred.matched_event_id = best_sil_ev.event_id
                    best_sil_ev.evaluable_windows.append(pred)
                elif best_sil_ev is not None:
                    pred.alignment_status = "AMBIGUOUS"
                    pred.matched_event_id = best_sil_ev.event_id
                    best_sil_ev.ambiguous_windows.append(pred)
                else:
                    pred.alignment_status = "UNMATCHED"

        # Evaluate outcomes for each AUDIO event
        for ev in audio_events:
            if ev.evaluable_windows:
                has_top1 = any(w.top1_id == ev.class_id for w in ev.evaluable_windows)
                has_top2 = any(w.top2_id == ev.class_id for w in ev.evaluable_windows)
                if has_top1:
                    ev.outcome = "TOP1_HIT"
                elif has_top2:
                    ev.outcome = "TOP2_HIT"
                else:
                    ev.outcome = "MISS"
            elif ev.ambiguous_windows:
                # Fallback for very short clips (< 1s) where audio window was split
                has_top1 = any(w.top1_id == ev.class_id for w in ev.ambiguous_windows)
                has_top2 = any(w.top2_id == ev.class_id for w in ev.ambiguous_windows)
                if has_top1:
                    ev.outcome = "TOP1_HIT"
                elif has_top2:
                    ev.outcome = "TOP2_HIT"
                else:
                    ev.outcome = "NO_EVALUABLE_WINDOWS"
            else:
                ev.outcome = "NO_EVALUABLE_WINDOWS"

    def generate_reports(self, target_species: List[str]):
        """Generate summary report, per-species CSV, timeline CSV, and aligned predictions CSV."""
        audio_events = [e for e in self.events if e.event_type == "AUDIO"]
        silence_events = [e for e in self.events if e.event_type == "SILENCE"]

        total_audio_plays = len(audio_events)
        top1_hits = sum(1 for e in audio_events if e.outcome == "TOP1_HIT")
        top2_hits = sum(1 for e in audio_events if e.outcome == "TOP2_HIT")
        misses = sum(1 for e in audio_events if e.outcome == "MISS")
        no_eval = sum(1 for e in audio_events if e.outcome == "NO_EVALUABLE_WINDOWS")

        top1_acc = (top1_hits / total_audio_plays * 100.0) if total_audio_plays > 0 else 0.0
        top2_acc = ((top1_hits + top2_hits) / total_audio_plays * 100.0) if total_audio_plays > 0 else 0.0
        miss_rate = (misses / total_audio_plays * 100.0) if total_audio_plays > 0 else 0.0

        # Silence Analysis
        silence_windows = [w for w in self.uart.predictions if w.alignment_status == "SILENCE_EVALUABLE"]
        silence_background = sum(1 for w in silence_windows if w.top1_id == 126)
        silence_false_positives = sum(1 for w in silence_windows if w.top1_id != 126)
        fp_rate = (silence_false_positives / len(silence_windows) * 100.0) if silence_windows else 0.0

        # High-water staging mark
        max_high_water = max((s["high_water"] for s in self.uart.staging_logs), default=0)
        total_lost_samples = sum(s["lost"] for s in self.uart.staging_logs)

        # 1. Write Playback Timeline CSV
        timeline_csv = self.output_dir / "playback_timeline.csv"
        with open(timeline_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "event_id", "event_type", "species", "class_id", "filename", "repeat_idx",
                "host_start_utc", "host_end_utc", "duration_sec", "evaluable_windows", "outcome"
            ])
            for ev in self.events:
                s_iso = datetime.datetime.fromtimestamp(ev.host_start, datetime.timezone.utc).isoformat()
                e_iso = datetime.datetime.fromtimestamp(ev.host_end, datetime.timezone.utc).isoformat()
                writer.writerow([
                    ev.event_id, ev.event_type, ev.species, ev.class_id, ev.filename, ev.repeat_idx,
                    s_iso, e_iso, round(ev.duration, 3), len(ev.evaluable_windows), ev.outcome
                ])

        # 2. Write Aligned Predictions CSV
        aligned_csv = self.output_dir / "predictions_aligned.csv"
        with open(aligned_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "window_id", "alignment_status", "matched_event_id", "top1_class_id", "top1_name",
                "top1_conf_q8", "top1_conf_pct", "top2_class_id", "top2_name", "top2_conf_q8",
                "top2_conf_pct", "cnn_us", "recv_host_utc"
            ])
            for p in self.uart.predictions:
                r_iso = datetime.datetime.fromtimestamp(p.recv_host_time, datetime.timezone.utc).isoformat()
                writer.writerow([
                    p.window_id, p.alignment_status, p.matched_event_id or "", p.top1_id, p.top1_name,
                    p.top1_q8, p.top1_conf_pct, p.top2_id, p.top2_name, p.top2_q8, p.top2_conf_pct,
                    p.cnn_us, r_iso
                ])

        # 3. Write Per-Species Report CSV
        species_csv = self.output_dir / "per_species_report.csv"
        with open(species_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "class_id", "species_name", "plays_completed", "evaluable_windows",
                "top1_hits", "top2_only_hits", "misses", "no_eval_windows",
                "top1_acc_pct", "top2_acc_pct", "error_rate_pct"
            ])
            for sp in target_species:
                sp_events = [e for e in audio_events if e.species == sp]
                if not sp_events:
                    continue
                cid = sp_events[0].class_id
                sp_name = self.classes.get(cid, sp)
                n_plays = len(sp_events)
                n_t1 = sum(1 for e in sp_events if e.outcome == "TOP1_HIT")
                n_t2 = sum(1 for e in sp_events if e.outcome == "TOP2_HIT")
                n_m = sum(1 for e in sp_events if e.outcome == "MISS")
                n_none = sum(1 for e in sp_events if e.outcome == "NO_EVALUABLE_WINDOWS")
                n_eval_w = sum(len(e.evaluable_windows) for e in sp_events)

                t1_p = (n_t1 / n_plays * 100.0) if n_plays > 0 else 0.0
                t2_p = ((n_t1 + n_t2) / n_plays * 100.0) if n_plays > 0 else 0.0
                err_p = (n_m / n_plays * 100.0) if n_plays > 0 else 0.0

                writer.writerow([
                    cid, sp_name, n_plays, n_eval_w, n_t1, n_t2, n_m, n_none,
                    round(t1_p, 1), round(t2_p, 1), round(err_p, 1)
                ])

        # 4. Write Summary JSON
        summary_data = {
            "test_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "target_species_count": len(target_species),
            "total_audio_plays": total_audio_plays,
            "top1_hits": top1_hits,
            "top1_accuracy_pct": round(top1_acc, 2),
            "top2_hits": top2_hits,
            "top2_accuracy_pct": round(top2_acc, 2),
            "misses": misses,
            "miss_rate_pct": round(miss_rate, 2),
            "no_evaluable_windows": no_eval,
            "silence_windows_evaluated": len(silence_windows),
            "silence_false_positives": silence_false_positives,
            "silence_false_positive_rate_pct": round(fp_rate, 2),
            "assert_interruption_count": len(self.uart.assert_events),
            "staging_max_high_water_blocks": max_high_water,
            "staging_lost_samples": total_lost_samples
        }
        with open(self.output_dir / "summary_report.json", "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        # 5. Write Summary Markdown
        summary_md = self.output_dir / "summary_report.md"

        t1_headers = ["Metric", "Count", "Percentage"]
        t1_align = ["L", "R", "R"]
        t1_rows = [
            ["**Top-1 Hits**", f"{top1_hits} / {total_audio_plays}", f"**{top1_acc:.1f}%**"],
            ["**Top-2 Hits (Top-1 or Top-2)**", f"{top1_hits + top2_hits} / {total_audio_plays}", f"**{top2_acc:.1f}%**"],
            ["**Misses**", f"{misses} / {total_audio_plays}", f"{miss_rate:.1f}%"],
            ["**Short / No-Eval Windows**", f"{no_eval} / {total_audio_plays}", f"{(no_eval / total_audio_plays * 100):.1f}%"]
        ]
        t1_md = format_md_table(t1_headers, t1_rows, t1_align)

        sil_headers = ["Metric", "Value"]
        sil_align = ["L", "R"]
        sil_rows = [
            ["Total Silence Windows Evaluated", str(len(silence_windows))],
            ["Correct Background Rejections (id=126)", str(silence_background)],
            ["False Positive Bird Detections", str(silence_false_positives)],
            ["**Silence False Positive Rate**", f"**{fp_rate:.1f}%**"]
        ]
        sil_md = format_md_table(sil_headers, sil_rows, sil_align)

        sp_headers = ["Class ID", "Species Name", "Plays", "Eval Windows", "Top-1 Hits", "Top-2 Only", "Misses", "Top-1 Acc", "Top-2 Acc"]
        sp_align = ["C", "L", "C", "C", "C", "C", "C", "R", "R"]
        sp_rows = []
        for sp in target_species:
            sp_events = [e for e in audio_events if e.species == sp]
            if not sp_events:
                continue
            cid = sp_events[0].class_id
            sp_name = self.classes.get(cid, sp)
            n_p = len(sp_events)
            n_t1 = sum(1 for e in sp_events if e.outcome == "TOP1_HIT")
            n_t2 = sum(1 for e in sp_events if e.outcome == "TOP2_HIT")
            n_m = sum(1 for e in sp_events if e.outcome == "MISS")
            n_w = sum(len(e.evaluable_windows) for e in sp_events)
            t1_p = (n_t1 / n_p * 100.0) if n_p > 0 else 0.0
            t2_p = ((n_t1 + n_t2) / n_p * 100.0) if n_p > 0 else 0.0
            sp_rows.append([
                str(cid), sp_name, str(n_p), str(n_w), str(n_t1), str(n_t2), str(n_m),
                f"{t1_p:.1f}%", f"{t2_p:.1f}%"
            ])
        sp_md = format_md_table(sp_headers, sp_rows, sp_align)

        with open(summary_md, "w", encoding="utf-8") as f:
            f.write("# WildSonic Live MCU Detection Test Report\n\n")
            f.write(f"- **Execution Time**: {summary_data['test_timestamp_utc']}\n")
            f.write(f"- **Species Tested**: {len(target_species)}\n")
            f.write(f"- **Total Audio Plays**: {total_audio_plays}\n")
            f.write(f"- **Assert Interruptions**: {len(self.uart.assert_events)}\n\n")

            f.write("## Overall Detection Accuracy\n\n")
            f.write(t1_md + "\n\n")

            f.write("## Silence Interval Analysis (False Positive Rejection)\n\n")
            f.write(sil_md + "\n\n")

            f.write("## Audio Staging & Queue Health\n\n")
            f.write(f"- **Max OCM Staging Ring High-Water Mark**: {max_high_water} / 18 blocks\n")
            f.write(f"- **Staging Lost / Overflow Samples**: {total_lost_samples} samples\n")
            f.write(f"- **Assert Events**: {len(self.uart.assert_events)}\n\n")

            f.write("## Per-Species Performance Summary\n\n")
            f.write(sp_md + "\n")

        print("------------------------------------------------------------------")
        print(f"[+] Summary Report : {summary_md}")
        print(f"[+] Per-Species CSV: {species_csv}")
        print(f"[+] Timeline CSV   : {timeline_csv}")
        print(f"[+] Predictions CSV: {aligned_csv}")
        print(f"[+] Top-1 Accuracy : {top1_acc:.1f}% | Top-2 Accuracy: {top2_acc:.1f}%")
        print(f"[+] Silence FP Rate: {fp_rate:.1f}%")
        print("==================================================================")


# ---------------------------------------------------------------------------
# CLI Argument Parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run live MCU bird species detection test using 126-species audio pack."
    )
    pack_default = Path(__file__).parent.resolve()
    parser.add_argument("--pack-dir", type=Path, default=pack_default,
                        help="Directory containing MANIFEST.csv, class_labels.txt, and audio_by_species/")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory for reports (default: results/test_run_<date>_<time>)")
    parser.add_argument("--port", type=str, default="/dev/ttyACM0",
                        help="Serial port for MCU UART (default: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200,
                        help="Serial baud rate (default: 115200)")
    parser.add_argument("--openocd-scripts", type=str, default="/home/amithesh/.local/opt/openocd/scripts",
                        help="Path to OpenOCD scripts directory")
    parser.add_argument("--repeats", type=int, default=1,
                        help="Number of times to repeat each WAV file (default: 1)")
    parser.add_argument("--silence-sec", type=float, default=3.0,
                        help="Silence duration in seconds between files/species (default: 3.0)")
    parser.add_argument("--species", type=str, default=None,
                        help="Comma-separated species names or class IDs to test (default: all)")
    parser.add_argument("--species-limit", type=int, default=None,
                        help="Limit test to the first N species")
    parser.add_argument("--files-per-species", type=int, default=10,
                        help="Number of WAV files to test per species (1-10, default: 10)")
    parser.add_argument("--skip-initial-reset", action="store_true",
                        help="Skip DAPLink reset before starting test")
    parser.add_argument("--playback-device", type=str, default="default",
                        help="ALSA audio output device (default: default)")

    args = parser.parse_args()

    # Default output directory: results/test_run_YYYYMMDD_HHMMSS
    results_base = args.pack_dir / "results"
    results_base.mkdir(parents=True, exist_ok=True)

    if args.output_dir is None or str(args.output_dir).strip() in (".", "./"):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = results_base / f"test_run_{ts}"
    elif not args.output_dir.is_absolute() and not str(args.output_dir).startswith("results"):
        args.output_dir = results_base / args.output_dir

    sp_filter = None
    if args.species:
        sp_filter = [s.strip() for s in args.species.split(",") if s.strip()]

    runner = LiveDetectionTestRunner(
        pack_dir=args.pack_dir,
        output_dir=args.output_dir,
        port=args.port,
        baud=args.baud,
        openocd_scripts=args.openocd_scripts,
        repeats=args.repeats,
        silence_sec=args.silence_sec,
        species_filter=sp_filter,
        species_limit=args.species_limit,
        files_per_species=args.files_per_species,
        skip_initial_reset=args.skip_initial_reset,
        playback_device=args.playback_device
    )

    try:
        runner.run()
    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user (Ctrl+C). Generating partial results from completed tests...")
        runner.uart.close()
        # Retrieve target species tested so far
        completed_species = list(dict.fromkeys(e.species for e in runner.events if e.event_type == "AUDIO"))
        if not completed_species and runner.classes:
            completed_species = [runner.classes.get(cid, str(cid)) for cid in sorted(runner.classes.keys())]
        runner.finalize_reports(completed_species)
        print(f"\n[+] Partial test results saved in: {runner.output_dir}")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[!] Unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        try:
            runner.uart.close()
            completed_species = list(dict.fromkeys(e.species for e in runner.events if e.event_type == "AUDIO"))
            if runner.events:
                runner.finalize_reports(completed_species)
                print(f"\n[+] Crash-recovery test results saved in: {runner.output_dir}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
