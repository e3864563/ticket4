import subprocess
import platform

ips = [
    "151.101.1.237",
    "151.101.65.237",
    "151.101.129.237",
    "151.101.193.237"
]

def run_ping(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '4', ip]  # ping 4 次
    print(f"\n--- PING {ip} ---")
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)

def run_traceroute(ip):
    system = platform.system().lower()
    if system == 'windows':
        command = ['tracert', ip]
    else:
        # Linux/macOS 加上詳細參數: -n (不解析), -q 5 (每跳發5次), -w 2 (等待2秒)
        command = ['traceroute', '-n', '-q', '5', '-w', '2', ip]

    print(f"\n--- TRACEROUTE {ip} ---")
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)

def main():
    for ip in ips:
        run_ping(ip)
        run_traceroute(ip)

if __name__ == "__main__":
    main()
