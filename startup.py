#!/usr/bin/env python3

import subprocess
import sys
import os
import time
import signal
import threading
import queue
import re
from datetime import datetime

class BotMonitor:
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_window = 300  # 5 minutes
        self.restart_times = []
        self.shutdown_requested = False
        self.error_pattern = re.compile(r'list indices must be integers or slices, not str')
        
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [MONITOR] {message}")
        
    def is_restart_loop(self):
        now = time.time()
        self.restart_times = [t for t in self.restart_times if now - t < self.restart_window]
        return len(self.restart_times) >= self.max_restarts
        
    def monitor_output(self, pipe, output_queue):
        try:
            for line in iter(pipe.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    print(decoded_line)
                    output_queue.put(decoded_line)
        except Exception as e:
            self.log(f"Output monitoring error: {e}")
        finally:
            pipe.close()
            
    def start_bot(self):
        if self.is_restart_loop():
            self.log(f"Too many restarts ({self.max_restarts}) in {self.restart_window}s. Stopping.")
            return False
            
        self.log("Starting bot process...")
        
        try:
            args = [sys.executable, "main.py"] + sys.argv[1:]
            
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=False
            )
            
            self.log(f"Bot started with PID: {self.process.pid}")
            return True
            
        except Exception as e:
            self.log(f"Failed to start bot: {e}")
            return False
            
    def graceful_shutdown(self):
        if not self.process:
            return True
            
        self.log("Attempting graceful shutdown...")
        
        try:
            self.process.terminate()
            
            for _ in range(10):
                if self.process.poll() is not None:
                    self.log("Bot shut down gracefully")
                    return True
                time.sleep(1)
                
            self.log("Graceful shutdown timeout, forcing termination...")
            self.process.kill()
            self.process.wait(timeout=5)
            return True
            
        except Exception as e:
            self.log(f"Error during shutdown: {e}")
            return False
            
    def restart_bot(self, reason="Unknown"):
        self.restart_times.append(time.time())
        self.restart_count += 1
        
        self.log(f"Restarting bot (#{self.restart_count}) - Reason: {reason}")
        
        if self.process:
            self.graceful_shutdown()
            self.process = None
            
        time.sleep(2)
        return self.start_bot()
        
    def run(self):
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        if not self.start_bot():
            return 1
            
        output_queue = queue.Queue()
        
        monitor_thread = threading.Thread(
            target=self.monitor_output,
            args=(self.process.stdout, output_queue),
            daemon=True
        )
        monitor_thread.start()
        
        consecutive_errors = 0
        last_error_time = 0
        
        while not self.shutdown_requested:
            try:
                if self.process.poll() is not None:
                    exit_code = self.process.returncode
                    self.log(f"Bot process exited with code: {exit_code}")
                    
                    if exit_code == 0:
                        self.log("Bot exited normally")
                        break
                    else:
                        if not self.restart_bot(f"Exit code {exit_code}"):
                            return 1
                        output_queue = queue.Queue()
                        monitor_thread = threading.Thread(
                            target=self.monitor_output,
                            args=(self.process.stdout, output_queue),
                            daemon=True
                        )
                        monitor_thread.start()
                        continue
                
                try:
                    line = output_queue.get(timeout=1)
                    
                    if self.error_pattern.search(line):
                        current_time = time.time()
                        
                        if current_time - last_error_time < 30:
                            consecutive_errors += 1
                        else:
                            consecutive_errors = 1
                            
                        last_error_time = current_time
                        
                        self.log(f"Detected target error (#{consecutive_errors}): {line}")
                        
                        if consecutive_errors >= 2:
                            if not self.restart_bot("Repeated target error"):
                                return 1
                            output_queue = queue.Queue()
                            monitor_thread = threading.Thread(
                                target=self.monitor_output,
                                args=(self.process.stdout, output_queue),
                                daemon=True
                            )
                            monitor_thread.start()
                            consecutive_errors = 0
                            
                except queue.Empty:
                    continue
                    
            except KeyboardInterrupt:
                self.log("Received interrupt signal")
                break
            except Exception as e:
                self.log(f"Monitor loop error: {e}")
                time.sleep(1)
                
        self.shutdown_requested = True
        
        if self.process:
            self.graceful_shutdown()
            
        self.log("Monitor shutdown complete")
        return 0
        
    def signal_handler(self, signum, frame):
        self.log(f"Received signal {signum}")
        self.shutdown_requested = True

def main():
    if not os.path.exists("main.py"):
        print("ERROR: main.py not found in current directory")
        return 1
        
    monitor = BotMonitor()
    return monitor.run()

if __name__ == "__main__":
    sys.exit(main())