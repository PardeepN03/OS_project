OS Resource Monitoring & Alert System

A responsive, colorful desktop dashboard built with Python, Tkinter, and psutil that monitors system resources in real time and raises alerts when usage crosses safe limits.

Features
Live system metrics: CPU, memory, disk, and more, refreshed every 1.5 seconds
Process monitor: view the top running processes (up to 100), refreshed every 5 seconds
Smart alerts: pop-up warnings when usage is too high, with a 60-second cooldown so you are not spammed
Export to CSV: save monitoring data to a file for later analysis
Clean, colorful UI: a responsive Tkinter dashboard that works on Windows, Linux, and macOS
Project Structure
OS_Resource_Monitoring_Alert_Fixed/
├── source_code/
│   ├── app.py              # Main application
│   ├── requirements.txt    # Python dependencies
│   └── README.md           # Source code notes
├── OS_Resource_Monitoring_Project_Presentation.pptx
├── OS_Resource_Monitoring_Project_Report.pdf
└── VIVA_QUESTIONS.md       # Viva preparation questions
Getting Started
Prerequisites
Python 3.8 or newer
pip
Installation
bash
# 1. Clone the repository
git clone https://github.com/PardeepN03/OS_project.git

# 2. Go to the source folder
cd OS_project/OS_Resource_Monitoring_Alert_Fixed/source_code

# 3. Install dependencies
pip install -r requirements.txt
Run
bash
python app.py

Tkinter comes bundled with Python on Windows and macOS. On Linux, install it with sudo apt install python3-tk.

Configuration

You can tweak these constants at the top of app.py:

Setting	Default	Description
METRIC_REFRESH_MS	1500	How often system metrics refresh (ms)
PROCESS_REFRESH_MS	5000	How often the process list refreshes (ms)
ALERT_COOLDOWN_SECONDS	60	Minimum gap between repeated alerts
MAX_PROCESSES	100	Maximum processes shown in the table
Screenshots

Add screenshots of your dashboard here:

![Dashboard](screenshots/dashboard.png)
Operating System Concepts Covered
Process management and scheduling
CPU utilization and load
Memory management (RAM usage)
Resource monitoring and threshold-based alerting
System calls via the psutil library
Tech Stack
Language: Python 3
GUI: Tkinter / ttk
Library: psutil
Documentation
Project Report (PDF)
Presentation (PPTX)
Viva Questions
Author

Pardeep GitHub: @PardeepN03

License

This project is for educational purposes.
