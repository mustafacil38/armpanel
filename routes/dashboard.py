import os
import platform
import socket
import time
import psutil
import subprocess
from flask import Blueprint, jsonify

dashboard_bp = Blueprint("dashboard", __name__)

_boot_time = time.time() # Default
try:
    _boot_time = psutil.boot_time()
except Exception:
    pass

try:
    _prev_net = psutil.net_io_counters()
except Exception:
    _prev_net = None
    print("Uyarı: Ağ istatistiklerine erişilemedi, bu özellik devre dışı.")
_prev_time = time.time()


def _read_file(path, default="N/A"):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return default


def _get_cpu_usage_fallback():
    try:
        # Read /proc/stat
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = line.split()
        if len(parts) < 5:
            return 0.0
        # idle is parts[4], total is sum of all parts
        idle = float(parts[4])
        total = sum(float(x) for x in parts[1:])
        return (idle, total)
    except Exception:
        return (0, 0)


def _get_ram_usage_fallback():
    try:
        # Try /proc/meminfo
        meminfo = {}
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        name = parts[0].strip()
                        val_parts = parts[1].split()
                        if val_parts:
                            meminfo[name] = int(val_parts[0]) * 1024  # kB to bytes
        
        total = meminfo.get("MemTotal", 0)
        # In newer kernels, MemAvailable is provided and is more accurate
        # than manual subtraction.
        available = meminfo.get("MemAvailable", -1)
        
        if available != -1:
            used = total - available
        else:
            free = meminfo.get("MemFree", 0)
            buffers = meminfo.get("Buffers", 0)
            cached = meminfo.get("Cached", 0)
            used = total - free - buffers - cached
            
        percent = (used / total * 100) if total > 0 else 0
        return {"total": total, "used": used, "percent": round(percent, 1)}
    except Exception:
        # Try 'free' command as final fallback
        try:
            # -b gives bytes, -w gives wide output (for available column)
            res = subprocess.check_output(["free", "-bw"]).decode()
            lines = res.splitlines()
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 7: # Standard free -bw output columns
                    total = int(parts[1])
                    available = int(parts[6]) # Available is the 7th col
                    used = total - available
                    percent = (used / total * 100) if total > 0 else 0
                    return {"total": total, "used": used, "percent": round(percent, 1)}
        except Exception:
            pass
    return {"total": 0, "used": 0, "percent": 0}


def _get_disk_usage_fallback(path="/"):
    try:
        # os.statvfs is a standard system call and very reliable in Root
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bfree * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        percent = (used / total * 100) if total > 0 else 0
        return {"total": total, "used": used, "percent": round(percent, 1)}
    except Exception:
        # Emergency df parsing
        try:
            res = subprocess.check_output(["df", "-B1", path]).decode()
            lines = res.splitlines()
            if len(lines) > 1:
                # df output: Filesystem size used avail capacity mount
                parts = lines[1].split()
                if len(parts) >= 3:
                    total = int(parts[1])
                    used = int(parts[2])
                    percent = (used / total * 100) if total > 0 else 0
                    return {"total": total, "used": used, "percent": round(percent, 1)}
        except Exception:
            pass
    return {"total": 0, "used": 0, "percent": 0}


_last_cpu_stats = _get_cpu_usage_fallback()

@dashboard_bp.route("/api/dashboard/stats", methods=["GET"])
def stats():
    global _prev_net, _prev_time, _last_cpu_stats

    # CPU
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
    except Exception:
        cpu_percent = 0.0
    
    if cpu_percent == 0: # Fallback
        new_stats = _get_cpu_usage_fallback()
        idle_diff = new_stats[0] - _last_cpu_stats[0]
        total_diff = new_stats[1] - _last_cpu_stats[1]
        if total_diff > 0:
            cpu_percent = round(100 * (1 - idle_diff / total_diff), 1)
        _last_cpu_stats = new_stats

    # RAM
    try:
        mem = psutil.virtual_memory()
        ram_total = mem.total
        ram_used = mem.used
        ram_percent = mem.percent
    except Exception:
        ram_total = ram_used = ram_percent = 0
    
    # Eger ram_total 0 ise veya cok kucukse (PRoot hatasi olabilir)
    if ram_total < 1024 * 1024:
        fallback = _get_ram_usage_fallback()
        ram_total = fallback["total"]
        ram_used = fallback["used"]
        ram_percent = fallback["percent"]

    # DISK
    try:
        disk = psutil.disk_usage("/")
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = disk.percent
    except Exception:
        disk_total = disk_used = disk_percent = 0
    
    # PRoot ortaminda disk_total genelde 0 gelir veya hata verir
    if disk_total < 1024 * 1024:
        fallback = _get_disk_usage_fallback("/")
        disk_total = fallback["total"]
        disk_used = fallback["used"]
        disk_percent = fallback["percent"]

    # NET
    net_up_speed = 0
    net_down_speed = 0
    cur_net_sent = 0
    cur_net_recv = 0
    
    try:
        cur_net = psutil.net_io_counters()
        cur_time = time.time()
        dt = cur_time - _prev_time if cur_time - _prev_time > 0 else 1

        if _prev_net:
            net_up_speed = (cur_net.bytes_sent - _prev_net.bytes_sent) / dt
            net_down_speed = (cur_net.bytes_recv - _prev_net.bytes_recv) / dt
        
        _prev_net = cur_net
        _prev_time = cur_time
        cur_net_sent = cur_net.bytes_sent
        cur_net_recv = cur_net.bytes_recv
    except Exception:
        pass

    # UPTIME
    try:
        uptime = int(time.time() - _boot_time)
    except Exception:
        uptime = 0
        up_str = _read_file("/proc/uptime", "0 0")
        try:
            uptime = int(float(up_str.split()[0]))
        except Exception:
            pass

    return jsonify({
        "cpu_percent": round(cpu_percent, 1),
        "cpu_count": psutil.cpu_count(logical=True) or 1,
        "ram_total": ram_total,
        "ram_used": ram_used,
        "ram_percent": round(ram_percent, 1),
        "disk_total": disk_total,
        "disk_used": disk_used,
        "disk_percent": round(disk_percent, 1),
        "net_sent": cur_net_sent,
        "net_recv": cur_net_recv,
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

    # Total RAM/Disk for system info
    try:
        ram_total = psutil.virtual_memory().total
        disk_total = psutil.disk_usage("/").total
    except Exception:
        ram_total = _get_ram_usage_fallback()["total"]
        disk_total = _get_disk_usage_fallback()["total"]

    return jsonify({
        "hostname": uname.node,
        "kernel": f"{uname.system} {uname.release}",
        "os_version": pretty_name,
        "processor": cpu_model,
        "architecture": uname.machine,
        "cpu_cores": psutil.cpu_count(logical=True) or 1,
        "cpu_physical": psutil.cpu_count(logical=False) or "N/A",
        "ip_address": ip_addr,
        "python_version": platform.python_version(),
        "ram_total_gb": round(ram_total / (1024**3), 2),
        "disk_total_gb": round(disk_total / (1024**3), 2),
    })
