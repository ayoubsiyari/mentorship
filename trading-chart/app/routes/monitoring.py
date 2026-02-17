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
    """Get system health metrics (CPU, RAM, Disk)."""
    
    # CPU usage
    cpu_output = run_command(["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"])
    try:
        cpu_percent = float(cpu_output.replace(",", "."))
    except:
        cpu_percent = 0.0
    
    # Memory usage
    mem_output = run_command(["sh", "-c", "free -m | awk 'NR==2{printf \"%s %s %.1f\", $3, $2, $3*100/$2}'"])
    mem_parts = mem_output.split()
    try:
        mem_used = int(mem_parts[0])
        mem_total = int(mem_parts[1])
        mem_percent = float(mem_parts[2])
    except:
        mem_used, mem_total, mem_percent = 0, 0, 0.0
    
    # Disk usage
    disk_output = run_command(["sh", "-c", "df -h / | awk 'NR==2{print $3, $2, $5}'"])
    disk_parts = disk_output.split()
    try:
        disk_used = disk_parts[0]
        disk_total = disk_parts[1]
        disk_percent = disk_parts[2]
    except:
        disk_used, disk_total, disk_percent = "0", "0", "0%"
    
    # Uptime
    uptime_output = run_command(["uptime", "-p"])
    
    # Load average
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
    
    # Fail2Ban status
    fail2ban_status = run_command(["sh", "-c", "systemctl is-active fail2ban 2>/dev/null || echo 'not installed'"])
    
    # Banned IPs from fail2ban
    banned_ips = []
    if fail2ban_status == "active":
        banned_output = run_command(["sh", "-c", "fail2ban-client banned 2>/dev/null || echo '[]'"])
        try:
            import ast
            banned_data = ast.literal_eval(banned_output)
            if banned_data and isinstance(banned_data, list):
                for jail in banned_data:
                    if isinstance(jail, dict):
                        for jail_name, ips in jail.items():
                            for ip in ips:
                                banned_ips.append({"ip": ip, "jail": jail_name})
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
    if top_attackers:
        for line in top_attackers.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
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
            "top_attackers": attacker_list[:5]
        },
        "web_attacks": {
            "suspicious_requests": int(web_attacks) if web_attacks.isdigit() else 0,
            "nginx_errors": int(error_count) if error_count.isdigit() else 0
        }
    }


@router.get("/services")
def get_services_status(_: Any = Depends(require_admin)) -> dict:
    """Get status of critical services."""
    
    services = ["nginx", "docker", "fail2ban", "ufw"]
    status_list = []
    
    for service in services:
        status = run_command(["sh", "-c", f"systemctl is-active {service} 2>/dev/null || echo 'not found'"])
        status_list.append({
            "name": service,
            "status": status,
            "ok": status == "active"
        })
    
    # Docker containers
    docker_ps = run_command(["sh", "-c", "docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | head -10 || echo 'Docker not running'"])
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": status_list,
        "docker_containers": docker_ps.split("\n") if docker_ps and "not" not in docker_ps.lower() else []
    }


@router.get("/overview")
def get_full_overview(_: Any = Depends(require_admin)) -> dict:
    """Get complete server overview - combines all metrics."""
    system = get_system_health(_)
    security = get_security_status(_)
    services = get_services_status(_)
    
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
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "health_status": health_status,
        "issues": issues,
        "warnings": warnings,
        "system": system,
        "security": security,
        "services": services
    }
