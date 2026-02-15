import socket

def get_local_ip():
    """
    Detects the local IP address of the machine on the LAN.
    Tries to connect to an external server (Google DNS) to determine the
    interface used for internet traffic, which usually corresponds to the LAN IP.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Check against Google DNS (doesn't actually send data)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        # Fallback to localhost if network is unavailable
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip
