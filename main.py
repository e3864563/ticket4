from pythonping import ping

ips = [
    "151.101.1.237",
    "151.101.65.237",
    "151.101.129.237",
    "151.101.193.237"
]

def ping_hosts(ip_list, count=4):
    for ip in ip_list:
        print(f"\n--- Pinging {ip} ---")
        responses = ping(ip, count=count)
        for response in responses:
            print(f"Reply from {response.address}: time={response.time_elapsed_ms:.2f} ms")

if __name__ == "__main__":
    ping_hosts(ips)
