import subprocess
import platform
import time
from typing import Tuple

class PingMonitor:
    def __init__(self, timeout=2, latency_threshold=200):
        self.timeout = timeout
        self.latency_threshold = latency_threshold # ms
        self.history = {} # ip -> last_results

    def ping(self, host: str) -> Tuple[bool, float]:
        """Returns (success, latency_ms)"""
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', '-w', str(self.timeout * 1000), host]
        
        start = time.time()
        try:
            # Simple ping check
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
            latency = (time.time() - start) * 1000
            
            # Try to parse actual latency from output if possible for better accuracy
            # (Simplifying for now, using process time as proxy)
            return True, latency
        except subprocess.CalledProcessError:
            return False, 0.0

    def check_status(self, host: str) -> str:
        success, latency = self.ping(host)
        
        if not success:
            return "DOWN"
        
        if latency > self.latency_threshold:
            return "OSCILLATING"
            
        return "OK"
