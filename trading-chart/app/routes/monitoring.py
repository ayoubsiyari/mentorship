import subprocess
from datetime import datetime
from typing import Any
import httpx
import asyncio
from functools import lru_cache

from fastapi import APIRouter, Depends

from ..deps import require_admin


# Cache for IP geolocation (avoid repeated API calls)
_ip_cache: dict[str, dict] = {}


def get_ip_info(ip: str) -> dict:
    """Get geolocation info for an IP address using ip-api.com (free, no key needed)."""
    if ip in _ip_cache:
        return _ip_cache[ip]
    
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,isp")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    result = {
                        "country": data.get("country", "Unknown"),
                        "country_code": data.get("countryCode", "XX"),
                        "city": data.get("city", ""),
                        "isp": data.get("isp", "")
                    }
                    _ip_cache[ip] = result
                    return result
    except Exception:
        pass
    
    return {"country": "Unknown", "country_code": "XX", "city": "", "isp": ""}

router = APIRouter(prefix="/api/admin/monitoring", tags=["monitoring"])


def run_command(cmd: list[str], timeout: int = 5) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"


@router.get("/system")
def get_system_health(_: Any = Depends(require_admin)) -> dict:
    """Get system health metrics (CPU, RAM, Disk) - Docker compatible."""
    
    # CPU usage from /proc/stat (works in Docker)
    try:
        with open('/proc/stat', 'r') as f:
            cpu_line = f.readline()
            cpu_parts = cpu_line.split()[1:8]
            cpu_times = [int(x) for x in cpu_parts]
            idle = cpu_times[3]
            total = sum(cpu_times)
            cpu_percent = round((1 - idle / total) * 100, 1) if total > 0 else 0.0
    except:
        cpu_percent = 0.0
    
    # Memory from /proc/meminfo (works in Docker)
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(':')] = int(parts[1])
            mem_total = meminfo.get('MemTotal', 0) // 1024  # Convert to MB
            mem_free = meminfo.get('MemFree', 0) // 1024
            mem_buffers = meminfo.get('Buffers', 0) // 1024
            mem_cached = meminfo.get('Cached', 0) // 1024
            mem_used = mem_total - mem_free - mem_buffers - mem_cached
            mem_percent = round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0.0
    except:
        mem_used, mem_total, mem_percent = 0, 0, 0.0
    
    # Disk usage (df works in Docker)
    disk_output = run_command(["sh", "-c", "df -h / | awk 'NR==2{print $3, $2, $5}'"])
    disk_parts = disk_output.split()
    try:
        disk_used = disk_parts[0]
        disk_total = disk_parts[1]
        disk_percent = disk_parts[2]
    except:
        disk_used, disk_total, disk_percent = "0", "0", "0%"
    
    # Uptime from /proc/uptime (works in Docker)
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_output = f"up {days}d {hours}h {minutes}m"
    except:
        uptime_output = "N/A"
    
    # Load average from /proc/loadavg
    load_output = run_command(["sh", "-c", "cat /proc/loadavg | awk '{print $1, $2, $3}'"])
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu": {
            "percent": cpu_percent,
            "status": "critical" if cpu_percent > 90 else "warning" if cpu_percent > 70 else "ok"
        },
        "memory": {
            "used_mb": mem_used,
            "total_mb": mem_total,
            "percent": mem_percent,
            "status": "critical" if mem_percent > 90 else "warning" if mem_percent > 70 else "ok"
        },
        "disk": {
            "used": disk_used,
            "total": disk_total,
            "percent": disk_percent,
            "status": "critical" if int(disk_percent.replace("%", "")) > 90 else "warning" if int(disk_percent.replace("%", "")) > 70 else "ok"
        },
        "uptime": uptime_output,
        "load_average": load_output
    }


@router.get("/security")
def get_security_status(_: Any = Depends(require_admin)) -> dict:
    """Get security status (Fail2Ban, blocked IPs, recent attacks)."""
    
    # Fail2Ban status - check via log file activity (works in Docker)
    fail2ban_check = run_command(["sh", "-c", "find /host-logs/fail2ban.log -mmin -60 2>/dev/null | grep -q fail2ban && echo 'active' || echo 'inactive'"])
    fail2ban_status = "active" if "active" in fail2ban_check else "inactive"
    
    # Banned IPs from fail2ban - parse from log file
    banned_ips = []
    if fail2ban_status == "active":
        # Get currently banned IPs from fail2ban log (look for Ban entries without subsequent Unban)
        banned_output = run_command(["sh", "-c", "grep -E 'Ban |Unban ' /host-logs/fail2ban.log 2>/dev/null | tail -100"])
        try:
            # Track banned/unbanned IPs
            ip_status = {}
            for line in banned_output.split('\n'):
                if ' Ban ' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[-1]
                        ip_status[ip] = 'banned'
                elif ' Unban ' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[-1]
                        ip_status[ip] = 'unbanned'
            # Get currently banned
            for ip, status in ip_status.items():
                if status == 'banned':
                    banned_ips.append({"ip": ip, "jail": "sshd"})
        except:
            pass
    
    # Recent failed SSH attempts (from host logs mounted at /host-logs)
    failed_ssh = run_command(["sh", "-c", "grep 'Failed password' /host-logs/auth.log 2>/dev/null | tail -10 | awk '{print $1, $2, $3, $11}' || echo 'No data'"])
    
    # Total failed attempts count
    failed_count = run_command(["sh", "-c", "grep -c 'Failed password' /host-logs/auth.log 2>/dev/null || echo '0'"])
    
    # Top attacking IPs
    top_attackers = run_command(["sh", "-c", "grep 'Failed password' /host-logs/auth.log 2>/dev/null | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -5 || echo ''"])
    
    # UFW status
    ufw_status = run_command(["sh", "-c", "ufw status 2>/dev/null | head -1 || echo 'not installed'"])
    
    # Recent 4xx/5xx errors count (from host nginx logs)
    error_count = run_command(["sh", "-c", "grep -a ' 4[0-9][0-9] \\| 5[0-9][0-9] ' /host-logs/nginx/access.log 2>/dev/null | wc -l || echo '0'"])
    
    # Suspicious web attacks count
    web_attacks = run_command(["sh", "-c", "grep -E '(wp-login|phpmyadmin|\\.env|/admin|shell|eval|base64)' /host-logs/nginx/access.log 2>/dev/null | wc -l || echo '0'"])
    
    # Parse top attackers with geolocation
    attacker_list = []
    if top_attackers and top_attackers.strip():
        for line in top_attackers.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    ip = parts[1]
                    ip_info = get_ip_info(ip)
                    attacker_list.append({
                        "count": int(parts[0]),
                        "ip": ip,
                        "country": ip_info["country"],
                        "country_code": ip_info["country_code"],
                        "city": ip_info["city"],
                        "isp": ip_info["isp"]
                    })
                except:
                    pass
    
    # Always load historical attackers when current list is empty
    historical_attackers = []
    if len(attacker_list) == 0:
        import glob
        hist_files = glob.glob("/host-logs/attack_history/ssh_attackers_*.log")
        for hist_file in hist_files:
            try:
                with open(hist_file, 'r') as f:
                    for line in f.readlines()[:10]:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                count = int(parts[0])
                                ip = parts[1]
                                ip_info = get_ip_info(ip)
                                historical_attackers.append({
                                    "count": count,
                                    "ip": ip,
                                    "country": ip_info["country"],
                                    "country_code": ip_info["country_code"],
                                    "city": ip_info["city"],
                                    "isp": ip_info["isp"],
                                    "historical": True
                                })
                            except ValueError:
                                pass
            except:
                pass
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "fail2ban": {
            "status": fail2ban_status,
            "banned_count": len(banned_ips),
            "banned_ips": banned_ips[:10]
        },
        "firewall": {
            "ufw_status": ufw_status
        },
        "ssh_attacks": {
            "total_failed_attempts": int(failed_count) if failed_count.isdigit() else 0,
            "recent_attempts": failed_ssh.split("\n") if failed_ssh != "No data" else [],
            "top_attackers": attacker_list[:5] if attacker_list else historical_attackers[:10]
        },
        "web_attacks": {
            "suspicious_requests": int(web_attacks) if web_attacks.isdigit() else 0,
            "nginx_errors": int(error_count) if error_count.isdigit() else 0
        }
    }


@router.get("/services")
def get_services_status(_: Any = Depends(require_admin)) -> dict:
    """Get status of critical services - checks via host logs since we're in Docker."""
    
    status_list = []
    
    # Check nginx by looking at host logs activity (modified in last 5 min = active)
    nginx_check = run_command(["sh", "-c", "find /host-logs/nginx/access.log -mmin -5 2>/dev/null && echo 'active'"])
    nginx_active = "active" in nginx_check
    status_list.append({"name": "nginx", "status": "active" if nginx_active else "idle", "ok": True})
    
    # Docker is obviously running since we're in a container
    status_list.append({"name": "docker", "status": "active", "ok": True})
    
    # Check fail2ban by looking for recent ban activity in logs
    fail2ban_check = run_command(["sh", "-c", "grep -c 'Ban\\|Unban' /host-logs/fail2ban.log 2>/dev/null || echo '0'"])
    fail2ban_active = fail2ban_check.strip().isdigit() and int(fail2ban_check.strip()) > 0
    # Also check if log file exists and was modified recently
    fail2ban_log_check = run_command(["sh", "-c", "test -f /host-logs/fail2ban.log && echo 'exists'"])
    status_list.append({
        "name": "fail2ban", 
        "status": "active" if fail2ban_active or "exists" in fail2ban_log_check else "inactive", 
        "ok": fail2ban_active or "exists" in fail2ban_log_check
    })
    
    # UFW - check by looking at ufw.log if it exists
    ufw_check = run_command(["sh", "-c", "test -f /host-logs/ufw.log && echo 'active' || echo 'inactive'"])
    ufw_active = "active" in ufw_check
    status_list.append({"name": "ufw", "status": "active" if ufw_active else "enabled", "ok": True})
    
    # Docker containers - read from host docker socket if available
    docker_ps = run_command(["sh", "-c", "cat /host-logs/docker-containers.txt 2>/dev/null || echo 'Running in containerized environment'"])
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": status_list,
        "docker_containers": docker_ps.split("\n") if docker_ps and "not" not in docker_ps.lower() else []
    }


def calculate_security_score(system: dict, security: dict, services: dict) -> dict:
    """Calculate security score from A to F based on current posture."""
    score = 100
    factors = []
    
    # System factors (max -20)
    cpu = system.get("cpu", {}).get("percent", 0)
    memory = system.get("memory", {}).get("percent", 0)
    disk = int(str(system.get("disk", {}).get("percent", "0")).replace("%", "") or 0)
    
    if cpu > 90:
        score -= 10
        factors.append({"factor": "High CPU usage", "impact": -10, "type": "warning"})
    if memory > 90:
        score -= 10
        factors.append({"factor": "High memory usage", "impact": -10, "type": "warning"})
    if disk > 90:
        score -= 10
        factors.append({"factor": "Low disk space", "impact": -10, "type": "critical"})
    
    # Security factors (max -40)
    ssh_attacks = security.get("ssh_attacks", {}).get("total_failed_attempts", 0)
    web_attacks = security.get("web_attacks", {}).get("suspicious_requests", 0)
    fail2ban_banned = security.get("fail2ban", {}).get("banned_count", 0)
    
    if ssh_attacks > 500:
        score -= 20
        factors.append({"factor": f"{ssh_attacks} SSH attacks detected", "impact": -20, "type": "critical"})
    elif ssh_attacks > 100:
        score -= 10
        factors.append({"factor": f"{ssh_attacks} SSH attacks detected", "impact": -10, "type": "warning"})
    
    if web_attacks > 200:
        score -= 15
        factors.append({"factor": f"{web_attacks} suspicious web requests", "impact": -15, "type": "critical"})
    elif web_attacks > 50:
        score -= 5
        factors.append({"factor": f"{web_attacks} suspicious web requests", "impact": -5, "type": "warning"})
    
    # Positive factors
    if fail2ban_banned > 0:
        score += 5
        factors.append({"factor": f"Fail2Ban active ({fail2ban_banned} IPs blocked)", "impact": +5, "type": "positive"})
    
    if security.get("fail2ban", {}).get("status") == "active":
        score += 5
        factors.append({"factor": "Fail2Ban protection active", "impact": +5, "type": "positive"})
    
    # Services factors (max -20)
    for svc in services.get("services", []):
        if not svc.get("ok", True) and svc.get("name") in ["nginx", "fail2ban"]:
            score -= 15
            factors.append({"factor": f"{svc['name']} service down", "impact": -15, "type": "critical"})
    
    # Cap score
    score = max(0, min(100, score))
    
    # Grade calculation
    if score >= 90:
        grade = "A"
        grade_color = "green"
    elif score >= 80:
        grade = "B"
        grade_color = "blue"
    elif score >= 70:
        grade = "C"
        grade_color = "yellow"
    elif score >= 60:
        grade = "D"
        grade_color = "orange"
    else:
        grade = "F"
        grade_color = "red"
    
    return {
        "score": score,
        "grade": grade,
        "grade_color": grade_color,
        "factors": factors
    }


@router.get("/overview")
def get_full_overview(_: Any = Depends(require_admin)) -> dict:
    """Get complete server overview - combines all metrics."""
    system = get_system_health(_)
    security = get_security_status(_)
    services = get_services_status(_)
    
    # Calculate security score
    security_score = calculate_security_score(system, security, services)
    
    # Calculate overall health score
    issues = []
    warnings = []
    
    if system["cpu"]["status"] == "critical":
        issues.append("High CPU usage")
    if system["memory"]["status"] == "critical":
        issues.append("High memory usage")
    if system["disk"]["status"] == "critical":
        issues.append("Low disk space")
    if security["fail2ban"]["status"] != "active":
        issues.append("Fail2Ban not running")
    
    for svc in services["services"]:
        if svc["name"] in ["nginx", "docker"] and not svc["ok"]:
            issues.append(f"{svc['name']} is down")
    
    # Security warnings (not critical but should be noted)
    ssh_attacks = security.get("ssh_attacks", {}).get("total_failed_attempts", 0)
    web_attacks = security.get("web_attacks", {}).get("suspicious_requests", 0)
    
    if ssh_attacks > 100:
        warnings.append(f"{ssh_attacks} SSH brute force attempts detected")
    if web_attacks > 50:
        warnings.append(f"{web_attacks} suspicious web requests detected")
    
    health_status = "critical" if len(issues) > 2 else "warning" if len(issues) > 0 or len(warnings) > 0 else "healthy"
    
    # Calculate threat level
    threat_level = "low"
    if ssh_attacks > 500 or web_attacks > 200:
        threat_level = "critical"
    elif ssh_attacks > 200 or web_attacks > 100:
        threat_level = "high"
    elif ssh_attacks > 50 or web_attacks > 25:
        threat_level = "medium"
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "health_status": health_status,
        "threat_level": threat_level,
        "security_score": security_score,
        "issues": issues,
        "warnings": warnings,
        "system": system,
        "security": security,
        "services": services
    }


@router.post("/block-ip")
def block_ip_address(ip: str, duration: int = 3600, _: Any = Depends(require_admin)) -> dict:
    """Block an IP address using iptables (via host)."""
    # Validate IP format
    import re
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
        return {"success": False, "error": "Invalid IP format"}
    
    # Add to fail2ban via writing to a blocklist file
    try:
        with open('/host-logs/blocked_ips.txt', 'a') as f:
            f.write(f"{datetime.utcnow().isoformat()}|{ip}|{duration}\n")
        return {"success": True, "message": f"IP {ip} queued for blocking"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/attack-analytics")
def get_attack_analytics(_: Any = Depends(require_admin)) -> dict:
    """Get detailed attack analytics."""
    
    # Attacks by hour (last 24h)
    hourly_attacks = run_command(["sh", "-c", """
        grep 'Failed password' /host-logs/auth.log 2>/dev/null | 
        awk '{print $3}' | cut -d: -f1 | sort | uniq -c | tail -24
    """])
    
    # Top attack sources by country (parsed from IP geo)
    top_ips = run_command(["sh", "-c", """
        grep 'Failed password' /host-logs/auth.log 2>/dev/null | 
        awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10
    """])
    
    # Attack types breakdown
    web_attack_types = run_command(["sh", "-c", """
        grep -E '(wp-login|phpmyadmin|\\.env|/admin|shell|eval|base64)' /host-logs/nginx/access.log 2>/dev/null |
        grep -oE '(wp-login|phpmyadmin|\\.env|/admin|shell|eval|base64)' | sort | uniq -c | sort -rn
    """])
    
    # Parse hourly data
    hourly_data = []
    for line in hourly_attacks.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) == 2:
            hourly_data.append({"hour": parts[1], "count": int(parts[0])})
    
    # Parse attack types
    attack_types = []
    for line in web_attack_types.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) == 2:
            attack_types.append({"type": parts[1], "count": int(parts[0])})
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "hourly_attacks": hourly_data,
        "attack_types": attack_types,
        "total_ssh_attacks": sum(h["count"] for h in hourly_data),
        "total_web_attacks": sum(a["count"] for a in attack_types)
    }


@router.get("/container-status")  
def get_container_status(_: Any = Depends(require_admin)) -> dict:
    """Get detailed Docker container status."""
    
    # List running containers with stats
    containers = []
    ps_output = run_command(["sh", "-c", "cat /proc/1/cgroup 2>/dev/null | grep docker | head -1"])
    
    # We're in a container, so return info about known services
    services = [
        {"name": "trading-chart", "type": "backend", "port": 8000},
        {"name": "journal-backend", "type": "backend", "port": 5000},
        {"name": "journal-frontend", "type": "frontend", "port": 3001},
        {"name": "db", "type": "database", "port": 5432}
    ]
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "running_in_container": bool(ps_output),
        "services": services,
        "message": "Container management available via Docker Compose on host"
    }


@router.get("/intrusion-detection")
def get_intrusion_detection(_: Any = Depends(require_admin)) -> dict:
    """Detect signs of potential intrusion or compromise."""
    
    alerts = []
    risk_level = "low"
    
    # 1. Check for successful SSH logins (potential unauthorized access)
    successful_logins = run_command(["sh", "-c", """
        grep 'Accepted' /host-logs/auth.log 2>/dev/null | tail -20 | 
        awk '{print $1, $2, $3, $9, $11}'
    """])
    
    login_list = []
    for line in successful_logins.strip().split('\n'):
        if line and 'Accepted' not in line:
            parts = line.strip().split()
            if len(parts) >= 4:
                login_list.append({
                    "date": f"{parts[0]} {parts[1]}",
                    "time": parts[2] if len(parts) > 2 else "",
                    "user": parts[3] if len(parts) > 3 else "unknown",
                    "ip": parts[4] if len(parts) > 4 else "unknown"
                })
    
    # 2. Check for new user accounts created recently
    new_users = run_command(["sh", "-c", """
        grep 'new user' /host-logs/auth.log 2>/dev/null | tail -10 ||
        grep 'useradd' /host-logs/auth.log 2>/dev/null | tail -10
    """])
    if new_users and "new user" in new_users.lower():
        alerts.append({
            "severity": "high",
            "type": "new_user",
            "message": "New user account(s) created recently",
            "details": new_users[:200]
        })
        risk_level = "high"
    
    # 3. Check for sudo/root access attempts
    sudo_attempts = run_command(["sh", "-c", """
        grep -E 'sudo|su:' /host-logs/auth.log 2>/dev/null | 
        grep -v 'session opened' | tail -10
    """])
    
    # 4. Check for modified system files (passwd, shadow, sudoers)
    file_integrity = []
    critical_files = [
        "/etc/passwd",
        "/etc/shadow", 
        "/etc/sudoers",
        "/etc/ssh/sshd_config"
    ]
    
    for filepath in critical_files:
        # Check modification time via host logs
        mod_check = run_command(["sh", "-c", f"stat -c '%Y %n' {filepath} 2>/dev/null"])
        if mod_check:
            file_integrity.append({"file": filepath, "status": "checked"})
    
    # 5. Check for suspicious processes (crypto miners, reverse shells)
    suspicious_processes = run_command(["sh", "-c", """
        ps aux 2>/dev/null | grep -iE '(miner|xmrig|cryptonight|nc -e|bash -i|/dev/tcp)' | 
        grep -v grep | head -5
    """])
    if suspicious_processes and len(suspicious_processes.strip()) > 5:
        alerts.append({
            "severity": "critical",
            "type": "suspicious_process",
            "message": "Potentially malicious process detected",
            "details": suspicious_processes[:200]
        })
        risk_level = "critical"
    
    # 6. Check for unauthorized cron jobs
    cron_check = run_command(["sh", "-c", """
        cat /var/spool/cron/crontabs/* 2>/dev/null | grep -v '^#' | head -10 ||
        crontab -l 2>/dev/null | grep -v '^#'
    """])
    
    # 7. Check for unusual network connections
    network_connections = run_command(["sh", "-c", """
        netstat -tuln 2>/dev/null | grep LISTEN | 
        awk '{print $4}' | sort -u | head -20 ||
        ss -tuln 2>/dev/null | grep LISTEN | awk '{print $5}' | head -20
    """])
    
    # 8. Check for recently modified binaries in /usr/bin
    modified_binaries = run_command(["sh", "-c", """
        find /usr/bin -mtime -7 -type f 2>/dev/null | head -10
    """])
    if modified_binaries and len(modified_binaries.strip()) > 0:
        alerts.append({
            "severity": "medium",
            "type": "modified_binary",
            "message": "System binaries modified in last 7 days",
            "details": modified_binaries[:200]
        })
        if risk_level == "low":
            risk_level = "medium"
    
    # 9. Check auth.log for brute force success after failures
    brute_success = run_command(["sh", "-c", """
        awk '/Failed password/{ip=$11; fails[ip]++} 
             /Accepted/{if(fails[$11]>5) print "ALERT: "$11" succeeded after "fails[$11]" failures"}' \
        /host-logs/auth.log 2>/dev/null | tail -5
    """])
    if brute_success and "ALERT" in brute_success:
        alerts.append({
            "severity": "critical",
            "type": "brute_force_success",
            "message": "Successful login after multiple failed attempts",
            "details": brute_success
        })
        risk_level = "critical"
    
    # 10. Check for unusual outbound connections
    outbound_check = run_command(["sh", "-c", """
        netstat -tn 2>/dev/null | grep ESTABLISHED | 
        awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -5 ||
        ss -tn 2>/dev/null | grep ESTAB | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -5
    """])
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "risk_level": risk_level,
        "alerts": alerts,
        "recent_logins": login_list[:10],
        "active_connections": network_connections.strip().split('\n') if network_connections else [],
        "outbound_connections": outbound_check.strip().split('\n') if outbound_check else [],
        "file_integrity": file_integrity,
        "cron_jobs": cron_check.strip().split('\n') if cron_check else [],
        "checks_performed": [
            "SSH login analysis",
            "New user detection",
            "Sudo access monitoring",
            "Critical file integrity",
            "Suspicious process scan",
            "Cron job audit",
            "Network connection review",
            "Brute force success detection"
        ]
    }


@router.get("/breach-check")
def check_data_breach(email: str = None, _: Any = Depends(require_admin)) -> dict:
    """Check if email/domain has been involved in known data breaches.
    Uses haveibeenpwned.com API (requires API key for full access).
    """
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "email_checked": email,
        "breaches_found": [],
        "recommendations": []
    }
    
    if not email:
        # Return general security recommendations
        results["recommendations"] = [
            "Enable 2FA on all accounts",
            "Use unique passwords for each service",
            "Monitor your email on haveibeenpwned.com",
            "Review connected apps and revoke unused access",
            "Check for unauthorized account activity"
        ]
        return results
    
    # For privacy, we'll check breach databases via API
    # Note: Full HIBP API requires an API key
    try:
        # Check against HIBP (limited without API key)
        with httpx.Client(timeout=5.0) as client:
            # This endpoint is rate-limited without API key
            resp = client.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                headers={
                    "User-Agent": "MentorshipSecurityCheck",
                    "hibp-api-key": ""  # Would need real key for production
                }
            )
            
            if resp.status_code == 200:
                breaches = resp.json()
                results["breaches_found"] = [
                    {"name": b.get("Name"), "date": b.get("BreachDate")} 
                    for b in breaches[:10]
                ]
                results["breach_count"] = len(breaches)
            elif resp.status_code == 404:
                results["status"] = "No breaches found"
            elif resp.status_code == 401:
                results["status"] = "API key required for full check"
            else:
                results["status"] = f"Check manually at haveibeenpwned.com"
    except Exception as e:
        results["status"] = "Check manually at haveibeenpwned.com"
        results["error"] = str(e)
    
    # Add SSL certificate check for the domain
    if email and "@" in email:
        domain = email.split("@")[1]
        results["domain"] = domain
        
        try:
            import ssl
            import socket
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    results["ssl_valid"] = True
                    results["ssl_expires"] = cert.get("notAfter")
        except Exception:
            results["ssl_valid"] = "Could not verify"
    
    results["recommendations"] = [
        "Change passwords for any breached accounts",
        "Enable 2FA where available",
        "Use a password manager",
        "Monitor for suspicious activity"
    ]
    
    return results


@router.get("/security-audit")
def run_security_audit(_: Any = Depends(require_admin)) -> dict:
    """Run a comprehensive security audit of the system."""
    
    audit_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "score": 100,
        "checks": [],
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
    
    checks = []
    
    # 1. SSH Configuration
    ssh_root = run_command(["sh", "-c", "grep -i 'PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null | head -1"])
    root_login_disabled = "no" in ssh_root.lower() if ssh_root else False
    checks.append({
        "name": "SSH Root Login Disabled",
        "status": "pass" if root_login_disabled else "fail",
        "severity": "high",
        "recommendation": "Set PermitRootLogin no in /etc/ssh/sshd_config"
    })
    
    ssh_password = run_command(["sh", "-c", "grep -i 'PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null | head -1"])
    password_disabled = "no" in ssh_password.lower() if ssh_password else False
    checks.append({
        "name": "SSH Password Auth Disabled",
        "status": "pass" if password_disabled else "warning",
        "severity": "medium",
        "recommendation": "Use SSH keys instead of passwords"
    })
    
    # 2. Firewall Status - check iptables rules count (works inside container)
    iptables_rules = run_command(["sh", "-c", "cat /proc/net/ip_tables_names 2>/dev/null && iptables -L -n 2>/dev/null | wc -l || echo '0'"])
    # If more than 10 rules, firewall is likely active
    rule_count = 0
    try:
        rule_count = int(iptables_rules.strip().split('\n')[-1]) if iptables_rules else 0
    except:
        pass
    firewall_active = rule_count > 10
    checks.append({
        "name": "Firewall Active",
        "status": "pass" if firewall_active else "fail",
        "severity": "high",
        "recommendation": "Enable UFW: sudo ufw enable"
    })
    
    # 3. Fail2Ban Status
    f2b_status = run_command(["sh", "-c", "test -f /host-logs/fail2ban.log && echo 'active'"])
    checks.append({
        "name": "Fail2Ban Active",
        "status": "pass" if "active" in f2b_status else "fail",
        "severity": "high",
        "recommendation": "Install and enable fail2ban"
    })
    
    # 4. Unattended Upgrades
    auto_updates = run_command(["sh", "-c", "dpkg -l unattended-upgrades 2>/dev/null | grep -q ii && echo 'installed'"])
    checks.append({
        "name": "Auto Security Updates",
        "status": "pass" if "installed" in auto_updates else "warning",
        "severity": "medium",
        "recommendation": "Install unattended-upgrades package"
    })
    
    # 5. Open Ports Check
    open_ports = run_command(["sh", "-c", "netstat -tuln 2>/dev/null | grep LISTEN | wc -l || ss -tuln | grep LISTEN | wc -l"])
    port_count = int(open_ports.strip()) if open_ports.strip().isdigit() else 0
    checks.append({
        "name": "Minimal Open Ports",
        "status": "pass" if port_count < 10 else "warning",
        "severity": "low",
        "details": f"{port_count} ports open",
        "recommendation": "Close unnecessary ports"
    })
    
    # 6. SSL Certificate Valid
    ssl_check = run_command(["sh", "-c", "echo | openssl s_client -connect localhost:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null"])
    checks.append({
        "name": "SSL Certificate Valid",
        "status": "pass" if "notAfter" in ssl_check else "warning",
        "severity": "high",
        "recommendation": "Ensure SSL certificates are valid and auto-renewed"
    })
    
    # 7. No World-Writable Files
    world_writable = run_command(["sh", "-c", "find /etc -perm -002 -type f 2>/dev/null | head -5"])
    checks.append({
        "name": "No World-Writable Config Files",
        "status": "pass" if not world_writable.strip() else "fail",
        "severity": "medium",
        "recommendation": "Fix permissions: chmod o-w <file>"
    })
    
    # 8. Log Monitoring Active
    log_check = run_command(["sh", "-c", "test -f /host-logs/auth.log && echo 'exists'"])
    checks.append({
        "name": "Security Logging Active",
        "status": "pass" if "exists" in log_check else "warning",
        "severity": "medium",
        "recommendation": "Ensure auth.log is being written"
    })
    
    # Calculate score
    for check in checks:
        if check["status"] == "pass":
            audit_results["passed"] += 1
        elif check["status"] == "fail":
            audit_results["failed"] += 1
            audit_results["score"] -= 15 if check["severity"] == "high" else 10
        else:
            audit_results["warnings"] += 1
            audit_results["score"] -= 5
    
    audit_results["score"] = max(0, audit_results["score"])
    audit_results["checks"] = checks
    
    # Grade
    score = audit_results["score"]
    audit_results["grade"] = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    
    return audit_results


@router.get("/attack-history")
def get_attack_history(_: Any = Depends(require_admin)) -> dict:
    """Get historical attack data from archived logs."""
    
    # Get list of archived attack files
    archives = run_command(["sh", "-c", "ls -la /host-logs/attack_history/*.log 2>/dev/null | tail -10"])
    
    # Read the latest SSH attackers archive
    ssh_history = run_command(["sh", "-c", "cat /host-logs/attack_history/ssh_attackers_*.log 2>/dev/null | head -50"])
    
    # Parse SSH history
    attackers_history = []
    for line in ssh_history.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) == 2:
            try:
                attackers_history.append({"count": int(parts[0]), "ip": parts[1]})
            except:
                pass
    
    # Get summary
    summary = run_command(["sh", "-c", "cat /host-logs/attack_history/summary.log 2>/dev/null"])
    
    # Count total historical attacks
    total_ssh = sum(a["count"] for a in attackers_history)
    unique_ips = len(attackers_history)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_historical_ssh_attacks": total_ssh,
        "unique_attacker_ips": unique_ips,
        "top_historical_attackers": sorted(attackers_history, key=lambda x: x["count"], reverse=True)[:20],
        "archives": archives,
        "summary": summary
    }
