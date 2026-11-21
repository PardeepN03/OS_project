"""OS Resource Monitoring & Alert System
Responsive, colorful Tkinter dashboard using psutil.
"""
import csv
import os
import platform
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import psutil

METRIC_REFRESH_MS = 1500
PROCESS_REFRESH_MS = 5000
ALERT_COOLDOWN_SECONDS = 60
MAX_PROCESSES = 100

# Prime psutil's non-blocking CPU sampler once at startup.
psutil.cpu_percent(interval=None)


class ResourceMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("OS Resource Monitoring & Alert System")
        self.root.geometry("1120x800")
        self.root.minsize(900, 680)
        self.root.configure(bg="#F3F6FC")

        self.cpu_limit = tk.DoubleVar(value=80)
        self.memory_limit = tk.DoubleVar(value=80)
        self.disk_limit = tk.DoubleVar(value=90)
        self.alerts_enabled = tk.BooleanVar(value=True)

        self.last_alert = {}
        self.rows = []
        self.metric_job = None
        self.process_job = None
        self.closed = False
        self.last_process_update = 0
        self.latest_values = {"CPU": None, "MEMORY": None, "DISK": None}
        self.threshold_vars = [self.cpu_limit, self.memory_limit, self.disk_limit]

        self.configure_styles()
        self.build_ui()

        # Re-check thresholds immediately when the user edits a value.
        for variable in self.threshold_vars:
            variable.trace_add("write", self.on_threshold_changed)

        # Start two independent timers: fast metrics, slower process table.
        self.refresh_metrics()
        self.refresh_processes()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Treeview",
                        background="#FFFFFF",
                        foreground="#263449",
                        fieldbackground="#FFFFFF",
                        rowheight=27,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background="#E5ECF6",
                        foreground="#20334D",
                        font=("Segoe UI", 9, "bold"),
                        padding=(6, 8))
        style.map("Treeview",
                  background=[("selected", "#D7E9FF")],
                  foreground=[("selected", "#163B66")])

        style.configure("Blue.Horizontal.TProgressbar",
                        troughcolor="#DCE7F5", background="#3B82F6",
                        bordercolor="#DCE7F5", lightcolor="#3B82F6",
                        darkcolor="#3B82F6")
        style.configure("Green.Horizontal.TProgressbar",
                        troughcolor="#DCEFE8", background="#10B981",
                        bordercolor="#DCEFE8", lightcolor="#10B981",
                        darkcolor="#10B981")
        style.configure("Purple.Horizontal.TProgressbar",
                        troughcolor="#EAE2F8", background="#8B5CF6",
                        bordercolor="#EAE2F8", lightcolor="#8B5CF6",
                        darkcolor="#8B5CF6")

        style.configure("Accent.TButton",
                        font=("Segoe UI", 9, "bold"),
                        padding=(12, 7))
        style.map("Accent.TButton",
                  background=[("active", "#1D4ED8"), ("!disabled", "#2563EB")],
                  foreground=[("!disabled", "#FFFFFF")])

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#17365D", padx=22, pady=15)
        header.pack(fill="x")
        tk.Label(header, text="OS Resource Monitoring & Alert System",
                 bg="#17365D", fg="#FFFFFF",
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(header,
                 text=f"HOST: {platform.node()}    •    OPERATING SYSTEM: {platform.system()}",
                 bg="#17365D", fg="#C9D9EC",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

        # Metric cards
        cards = tk.Frame(self.root, bg="#F3F6FC", padx=12, pady=12)
        cards.pack(fill="x")
        self.metric_labels = {}
        metric_config = [
            ("cpu", "CPU USAGE", "#2563EB", "#EFF6FF", "Blue.Horizontal.TProgressbar"),
            ("memory", "MEMORY USAGE", "#059669", "#ECFDF5", "Green.Horizontal.TProgressbar"),
            ("disk", "DISK USAGE", "#7C3AED", "#F5F3FF", "Purple.Horizontal.TProgressbar"),
        ]
        for key, title, accent, card_bg, bar_style in metric_config:
            card = tk.Frame(cards, bg=card_bg, highlightbackground="#D9E3F0",
                            highlightthickness=1, padx=14, pady=10)
            card.pack(side="left", expand=True, fill="x", padx=6)
            tk.Label(card, text=title, bg=card_bg, fg=accent,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            value = tk.Label(card, text="--%", bg=card_bg, fg="#172B4D",
                             font=("Segoe UI", 25, "bold"))
            value.pack(anchor="w", pady=(4, 6))
            bar = ttk.Progressbar(card, maximum=100, style=bar_style)
            bar.pack(fill="x")
            self.metric_labels[key] = (value, bar)

        # Threshold controls
        settings = tk.LabelFrame(self.root, text="  ALERT THRESHOLDS (%)  ",
                                 bg="#FFFFFF", fg="#20334D",
                                 font=("Segoe UI", 9, "bold"),
                                 padx=12, pady=9, bd=1, relief="solid")
        settings.pack(fill="x", padx=18, pady=(0, 10))

        for label, var, color in [
            ("CPU", self.cpu_limit, "#2563EB"),
            ("Memory", self.memory_limit, "#059669"),
            ("Disk", self.disk_limit, "#7C3AED")
        ]:
            group = tk.Frame(settings, bg="#FFFFFF")
            group.pack(side="left", padx=(0, 20))
            tk.Label(group, text=label, bg="#FFFFFF", fg=color,
                     font=("Segoe UI", 9, "bold")).pack(side="left")
            spin = tk.Spinbox(group, from_=1, to=100, width=5,
                              textvariable=var, font=("Segoe UI", 9),
                              relief="solid", bd=1)
            spin.pack(side="left", padx=7)

        ttk.Checkbutton(settings, text="Enable alerts",
                        variable=self.alerts_enabled).pack(side="left", padx=8)
        ttk.Button(settings, text="Check thresholds now",
                   style="Accent.TButton", command=self.check_thresholds_now).pack(side="right", padx=(6, 0))
        ttk.Button(settings, text="Export process list (CSV)",
                   style="Accent.TButton", command=self.export_csv).pack(side="right")

        # Process table
        process_frame = tk.LabelFrame(
            self.root, text="  RUNNING PROCESSES (TOP 100 BY MEMORY)  ",
            bg="#FFFFFF", fg="#20334D", font=("Segoe UI", 9, "bold"),
            padx=8, pady=8, bd=1, relief="solid"
        )

        columns = ("pid", "name", "cpu", "memory", "status")
        self.tree = ttk.Treeview(process_frame, columns=columns,
                                 show="headings", height=8)
        headings = {"pid": "PID", "name": "PROCESS NAME",
                    "cpu": "CPU %", "memory": "MEMORY %", "status": "STATUS"}
        widths = {"pid": 85, "name": 390, "cpu": 110, "memory": 125, "status": 150}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col],
                             anchor="w" if col == "name" else "center")
        self.tree.tag_configure("even", background="#F5F8FD")
        self.tree.tag_configure("odd", background="#FFFFFF")

        yscroll = ttk.Scrollbar(process_frame, orient="vertical",
                                command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        # Status / refresh row
        bottom = tk.Frame(self.root, bg="#F3F6FC", padx=18, pady=5)
        self.updated = tk.Label(bottom, text="Starting monitor...",
                                bg="#F3F6FC", fg="#52657A",
                                font=("Segoe UI", 9))
        self.updated.pack(side="left")
        ttk.Button(bottom, text="↻  Refresh now",
                   style="Accent.TButton", command=self.refresh_now).pack(side="right")

        # Alert log
        log_frame = tk.LabelFrame(self.root, text="  ALERT LOG  ",
                                  bg="#FFFFFF", fg="#20334D",
                                  font=("Segoe UI", 9, "bold"),
                                  padx=8, pady=7, bd=1, relief="solid")
        self.log = tk.Text(log_frame, height=5, wrap="word",
                           bg="#FFFDF5", fg="#7C4A03",
                           insertbackground="#7C4A03",
                           relief="flat", font=("Consolas", 9),
                           state="disabled")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical",
                                   command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.pack(side="left", fill="x", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Pack the fixed-size bottom sections FIRST so the expanding process
        # table can't squeeze them out of the window.
        log_frame.pack(side="bottom", fill="x", padx=18, pady=(0, 12))
        bottom.pack(side="bottom", fill="x")
        process_frame.pack(fill="both", expand=True, padx=18, pady=(0, 8))

        self.append_log(
            f"{datetime.now():%H:%M:%S}  INFO: Alert engine loaded. Monitoring CPU, memory and disk.",
            "#166534"
        )

    def append_log(self, message, color="#9A3412"):
        # One text tag per color so each line is shown in its own color.
        tag = f"c{color}"
        self.log.tag_configure(tag, foreground=color)
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def add_alert(self, resource, value, limit, force=False):
        if not self.alerts_enabled.get() or value is None or value < limit:
            return False
        now = time.time()
        # Avoid duplicate warnings while the same resource remains over its limit.
        if not force and now - self.last_alert.get(resource, 0) < ALERT_COOLDOWN_SECONDS:
            return False
        self.last_alert[resource] = now
        message = (f"{datetime.now():%H:%M:%S}  WARNING: {resource} usage "
                   f"is {value:.1f}% (threshold: {limit:.0f}%).")
        self.append_log(message, "#B42318")
        try:
            self.root.bell()
        except tk.TclError:
            pass
        return True

    def read_thresholds(self):
        try:
            return {
                "CPU": float(self.cpu_limit.get()),
                "MEMORY": float(self.memory_limit.get()),
                "DISK": float(self.disk_limit.get())
            }
        except (tk.TclError, ValueError):
            return None

    def on_threshold_changed(self, *_):
        # Spinbox variables can be briefly empty while a user is typing.
        # Check only when all values parse successfully.
        if not hasattr(self, "latest_values"):
            return
        if self.read_thresholds() is None:
            return
        self.root.after_idle(self.check_thresholds_now)

    def check_thresholds_now(self):
        if not self.alerts_enabled.get():
            self.append_log(
                f"{datetime.now():%H:%M:%S}  ALERTS DISABLED — turn on Enable alerts first.",
                "#64748B"
            )
            return

        thresholds = self.read_thresholds()
        if thresholds is None:
            self.append_log(
                f"{datetime.now():%H:%M:%S}  INVALID THRESHOLD — enter values from 1 to 100.",
                "#B45309"
            )
            return

        # Take fresh readings at the moment the user clicks the button.
        try:
            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage(os.path.abspath(os.sep)).percent
            self.latest_values = {"CPU": cpu, "MEMORY": memory, "DISK": disk}

            for key, value in (("cpu", cpu), ("memory", memory), ("disk", disk)):
                label, bar = self.metric_labels[key]
                label.config(text=f"{value:.1f}%")
                bar["value"] = value

        except Exception as exc:
            self.append_log(
                f"{datetime.now():%H:%M:%S}  CHECK ERROR — {exc}",
                "#B42309"
            )
            return

        self.append_log(
            f"{datetime.now():%H:%M:%S}  CHECK: "
            f"CPU {self.latest_values['CPU']:.1f}/{thresholds['CPU']:.0f}% | "
            f"MEMORY {self.latest_values['MEMORY']:.1f}/{thresholds['MEMORY']:.0f}% | "
            f"DISK {self.latest_values['DISK']:.1f}/{thresholds['DISK']:.0f}%",
            "#1D4ED8"
        )

        triggered = 0
        for resource, value in self.latest_values.items():
            limit = thresholds[resource]
            if value >= limit:
                # Manual check intentionally bypasses cooldown so the user can
                # demonstrate the alert on demand.
                self.last_alert[resource] = time.time()
                self.append_log(
                    f"{datetime.now():%H:%M:%S}  WARNING: {resource} usage "
                    f"is {value:.1f}% (threshold: {limit:.0f}%).",
                    "#B42318"
                )
                triggered += 1

        if triggered:
            self.append_log(
                f"{datetime.now():%H:%M:%S}  CHECK COMPLETE — {triggered} warning(s) generated.",
                "#B42318"
            )
            try:
                self.root.bell()
            except tk.TclError:
                pass
        else:
            self.append_log(
                f"{datetime.now():%H:%M:%S}  CHECK COMPLETE — no resources are above their thresholds.",
                "#64748B"
            )

    def refresh_metrics(self):
        if self.closed:
            return
        try:
            # Non-blocking CPU sample keeps the Tkinter UI responsive.
            cpu = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage(os.path.abspath(os.sep)).percent

            values = {"cpu": cpu, "memory": memory, "disk": disk}
            self.latest_values = {"CPU": cpu, "MEMORY": memory, "DISK": disk}
            thresholds = self.read_thresholds()

            for key, value in values.items():
                label, bar = self.metric_labels[key]
                label.config(text=f"{value:.1f}%")
                bar["value"] = value

            if thresholds is not None:
                for resource, value in self.latest_values.items():
                    self.add_alert(resource, value, thresholds[resource])

            self.updated.config(
                text=f"Last updated: {datetime.now():%d-%m-%Y %H:%M:%S}  |  "
                     f"Metrics refresh: {METRIC_REFRESH_MS / 1000:.1f}s  |  "
                     f"Process refresh: {PROCESS_REFRESH_MS / 1000:.1f}s"
            )
        except Exception as exc:
            self.updated.config(text=f"Monitoring error: {exc}")

        self.metric_job = self.root.after(METRIC_REFRESH_MS, self.refresh_metrics)

    def refresh_processes(self):
        if self.closed:
            return
        processes = []
        try:
            for proc in psutil.process_iter(
                ["pid", "name", "status", "memory_percent", "cpu_percent"]
            ):
                try:
                    info = proc.info
                    processes.append((
                        int(info.get("pid") or 0),
                        info.get("name") or "Unknown",
                        float(info.get("cpu_percent") or 0.0),
                        float(info.get("memory_percent") or 0.0),
                        info.get("status") or "Unknown"
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            processes.sort(key=lambda item: item[3], reverse=True)
            self.rows = processes[:MAX_PROCESSES]

            # Update existing rows instead of deleting and rebuilding the whole table.
            visible_pids = set()
            for index, row in enumerate(self.rows):
                pid, name, cpu, memory, status = row
                iid = str(pid)
                visible_pids.add(iid)
                values = (pid, name, f"{cpu:.1f}", f"{memory:.2f}", status)
                tag = "even" if index % 2 == 0 else "odd"
                if self.tree.exists(iid):
                    self.tree.item(iid, values=values, tags=(tag,))
                else:
                    self.tree.insert("", "end", iid=iid, values=values, tags=(tag,))

            for iid in self.tree.get_children():
                if iid not in visible_pids:
                    self.tree.delete(iid)

            # Keep the visible ordering consistent with memory ranking.
            for position, row in enumerate(self.rows):
                iid = str(row[0])
                if self.tree.exists(iid):
                    self.tree.move(iid, "", position)

            self.last_process_update = time.time()
        except Exception as exc:
            self.updated.config(text=f"Process monitoring error: {exc}")

        self.process_job = self.root.after(PROCESS_REFRESH_MS, self.refresh_processes)

    def refresh_now(self):
        # Manual refresh updates the metrics immediately and process list once.
        if self.metric_job is not None:
            try:
                self.root.after_cancel(self.metric_job)
            except tk.TclError:
                pass
            self.metric_job = None
        if self.process_job is not None:
            try:
                self.root.after_cancel(self.process_job)
            except tk.TclError:
                pass
            self.process_job = None
        self.refresh_metrics()
        self.refresh_processes()

    def export_csv(self):
        if not self.rows:
            messagebox.showinfo("Export", "No process data available yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="process_report.csv"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["PID", "Process Name", "CPU %", "Memory %", "Status"])
                writer.writerows(self.rows)
            messagebox.showinfo("Export complete", f"Process report saved to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))

    def close(self):
        self.closed = True
        for job in (self.metric_job, self.process_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ResourceMonitor(root)
    root.mainloop()
