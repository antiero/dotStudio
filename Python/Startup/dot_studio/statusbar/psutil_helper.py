import psutil
import os

# Conversion helpers
def bytesToMB(bytes):
  """Returns byte value in megabytes"""
  MB = float(bytes)/float(1<<20)
  return MB

def bytesToGB(bytes):
  """Returns byte value in gigabytes"""
  GB = float(bytes)/float(1<<30)
  return GB

class PSUtilProcessWrapper(object):
  """This is a wrapper around a psutil.Process object, for the Nuke process"""
  def __init__(self):

    # This should be the process of Nuke.
    self.nukeProcess = psutil.Process(os.getpid())

  def nukeMemoryUsageAsPercentage(self):
    """Returns Nuke's current memory usage as percentage of Total memory"""
    mem_percent = self.nukeProcess.memory_percent()
    return mem_percent

  def nukeCPUUsageAsPercentage(self):
    """Returns Nuke's current CPU usage as percentage
        Note: this currently returns the sum of ALL running processes with 'Nuke' in the name"""
    nuke_processes_cpu = []
    for proc in psutil.process_iter():
        try:
            if "Nuke" in proc.name():
                nuke_processes_cpu.append(proc.cpu_percent())
        except psutil.AccessDenied:
            pass
    cpu_percent = sum(nuke_processes_cpu)
    return cpu_percent

  def nukeMemoryUsageInGB(self):
    """Returns Nuke's current memory usage in GB"""
    nuke_mem_bytes = self.nukeProcess.memory_info().rss
    nuke_mem_GB = bytesToGB(nuke_mem_bytes)
    return nuke_mem_GB

  def numOpenFiles(self):
    """Returns the number of open files. Unused at present."""
    numOpenFiles = len(self.nukeProcess.get_open_files())
    return numOpenFiles

  def totalSystemMemory(self):
    """Returns the total System memory in GigaBytes"""
    return bytesToGB(psutil.virtual_memory().total)
