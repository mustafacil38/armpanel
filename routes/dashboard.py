import os
import platform
import socket
import time
import psutil
from flask import Blueprint, jsonify

dashboard_bp = Blueprint("dashboard", __name__)

_boot_time = psutil.boot_time()
_prev_net = psutil.net_io_counters()
_prev_time = time.time()


def _read_file(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return "N/A"


@dashboard_bp.route("/api/dashboard/stats", methods=["GET"])
def stats():
    global _prev_net, _prev_time

    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    cur_net = psutil.net_io_counters()
    cur_time = time.time()
    dt = cur_time - _prev_time if cur_time - _prev_time > 0 else 1

    net_up_speed = (cur_net.bytes_sent - _prev_net.bytes_sent) / dt
    net_down_speed = (cur_net.bytes_recv - _prev_net.bytes_recv) / dt

    _prev_net = cur_net
    _prev_time = cur_time

    uptime = int(time.time() - _boot_time)

    return jsonify({
        "cpu_percent": round(cpu_percent, 1),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_total": mem.total,
        "ram_used": mem.used,
        "ram_percent": round(mem.percent, 1),
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": round(disk.percent, 1),
        "net_sent": cur_net.bytes_sent,
        "net_recv": cur_net.bytes_recv,
        "net_up_speed": round(net_up_speed),
        "net_down_speed": round(net_down_speed),
        "uptime": uptime,
    })


@dashboard_bp.route("/api/dashboard/system", methods=["GET"])
def system_info():
    uname = platform.uname()

    # Debian version
    debian_version = _read_file("/etc/os-release")
    pretty_name = "N/A"
    for line in debian_version.split("\n"):
        if line.startswith("PRETTY_NAME="):
            pretty_name = line.split("=", 1)[1].strip('"')
            break

    # Processor info
    processor = uname.machine
    cpu_model = "N/A"
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line.lower() or "hardware" in line.lower():
                    cpu_model = line.split(":")[1].strip()
                    break
    except Exception:
        cpu_model = processor

    # IP address
    ip_addr = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_addr = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    return jsonify({
        "hostname": uname.node,
        "kernel": f"{uname.system} {uname.release}",
        "os_version": pretty_name,
        "processor": cpu_model,
        "architecture": uname.machine,
        "cpu_cores": psutil.cpu_count(logical=True),
        "cpu_physical": psutil.cpu_count(logical=False) or "N/A",
        "ip_address": ip_addr,
        "python_version": platform.python_version(),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_total_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
    })
