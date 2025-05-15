import sys
import time
from typing import Optional

class ProgressBar:
    def __init__(self, total: int, prefix: str = '', suffix: str = '', decimals: int = 1, length: int = 50, fill: str = '█'):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.iteration = 0
        self.start_time = time.time()
        
    def print(self, iteration: Optional[int] = None):
        if iteration is not None:
            self.iteration = iteration
        else:
            self.iteration += 1
            
        percent = ("{0:." + str(self.decimals) + "f}").format(100 * (self.iteration / float(self.total)))
        filled_length = int(self.length * self.iteration // self.total)
        bar = self.fill * filled_length + '-' * (self.length - filled_length)
        
        elapsed_time = time.time() - self.start_time
        if self.iteration > 0:
            eta = (elapsed_time / self.iteration) * (self.total - self.iteration)
            time_info = f" | {elapsed_time:.1f}s/{eta:.1f}s"
        else:
            time_info = ""
            
        sys.stdout.write(f'\r{self.prefix} |{bar}| {percent}% {self.suffix}{time_info}')
        sys.stdout.flush()
        
        if self.iteration == self.total:
            sys.stdout.write('\n') 