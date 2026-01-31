import time
import requests
import os
import sys
import threading

# List of VPN container hostnames (internal Docker DNS)
# e.g. "vpn-eu-1,vpn-eu-2,vpn-eu-3"
VPN_CONTAINERS = os.getenv("VPN_CONTAINERS", "").split(",")
# Rotation interval in seconds (default 10 minutes)
INTERVAL = int(os.getenv("ROTATION_INTERVAL", "600"))

def get_current_ip(container_host, proxy_port=8888):
    """Get current public IP through the proxy"""
    proxies = {
        "http": f"http://{container_host}:{proxy_port}",
        "https": f"http://{container_host}:{proxy_port}",
    }
    try:
        r = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10)
        return r.json().get("ip")
    except:
        return None

def rotate_vpn(container_host):
    """Rotate the VPN connection for a specific container"""
    control_url = f"http://{container_host}:8000/v1/vpn/status"
    try:
        print(f"[{container_host}] Rotating IP...")
        # Stop VPN
        requests.put(control_url, json={"status": "stopped"}, timeout=5)
        time.sleep(2)
        # Start VPN
        requests.put(control_url, json={"status": "running"}, timeout=5)
        print(f"[{container_host}] Restart signal sent.")
    except Exception as e:
        print(f"[{container_host}] Rotation failed: {e}")

def rotation_loop():
    print(f"Starting VPN Manager. Monitoring {len(VPN_CONTAINERS)} containers.")
    print(f"Rotation interval: {INTERVAL} seconds.")
    
    while True:
        print(f"\nWaiting {INTERVAL} seconds for next rotation cycle...")
        time.sleep(INTERVAL)
        
        for vpn_host in VPN_CONTAINERS:
            if not vpn_host.strip(): continue
            
            # Run rotation in separate thread or just sequential?
            # Sequential is fine to avoid load spikes
            rotate_vpn(vpn_host.strip())
            time.sleep(5) # Stagger rotations

def main():
    if not any(VPN_CONTAINERS):
        print("No VPN_CONTAINERS defined. Exiting.")
        sys.exit(1)
        
    rotation_loop()

if __name__ == "__main__":
    main()
