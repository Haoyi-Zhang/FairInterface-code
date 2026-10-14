"""Native measurements for owned finite workers; no sampling or RSS emulation.

Windows: peak working set bytes and kernel+user process CPU. POSIX: getrusage,
with explicit macOS byte conversion. Windows jobs kill descendants on close;
these are containment/time bounds, not CPU or memory admission limits.
"""
from __future__ import annotations
import ctypes
import os
import sys
from ctypes import wintypes as w

try:
    import resource
except ModuleNotFoundError:
    resource = None

if os.name == 'nt':
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class Memory(ctypes.Structure):
        _fields_ = [('cb', w.DWORD), ('PageFaultCount', w.DWORD)] + [
            (name, ctypes.c_size_t) for name in (
                'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    class BasicLimit(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong),
                    ('PerJobUserTimeLimit', ctypes.c_longlong), ('LimitFlags', w.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', w.DWORD), ('Affinity', ctypes.c_size_t),
                    ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            'ReadOperationCount','WriteOperationCount','OtherOperationCount',
            'ReadTransferCount','WriteTransferCount','OtherTransferCount')]
    class ExtendedLimit(ctypes.Structure):
        _fields_ = [('BasicLimitInformation',BasicLimit), ('IoInfo',IO)] + [
            (name,ctypes.c_size_t) for name in ('ProcessMemoryLimit','JobMemoryLimit',
                                             'PeakProcessMemoryUsed','PeakJobMemoryUsed')]
    class Accounting(ctypes.Structure):
        _fields_ = [(name,ctypes.c_longlong) for name in (
            'TotalUserTime','TotalKernelTime','ThisPeriodTotalUserTime',
            'ThisPeriodTotalKernelTime')] + [(name,w.DWORD) for name in (
            'TotalPageFaultCount','TotalProcesses','ActiveProcesses','TotalTerminatedProcesses')]
    signatures = {
        'GetCurrentProcess': ([], w.HANDLE),
        'K32GetProcessMemoryInfo': ([w.HANDLE,ctypes.POINTER(Memory),w.DWORD],w.BOOL),
        'GetProcessTimes': ([w.HANDLE] + [ctypes.POINTER(w.FILETIME)]*4,w.BOOL),
        'CreateJobObjectW': ([ctypes.c_void_p,w.LPCWSTR],w.HANDLE),
        'SetInformationJobObject': ([w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD],w.BOOL),
        'AssignProcessToJobObject': ([w.HANDLE,w.HANDLE],w.BOOL),
        'QueryInformationJobObject': ([w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,
                                      ctypes.POINTER(w.DWORD)],w.BOOL),
        'TerminateJobObject': ([w.HANDLE,w.UINT],w.BOOL),
        'CloseHandle': ([w.HANDLE],w.BOOL),
    }
    for name,(arguments,result) in signatures.items():
        function=getattr(kernel,name)
        function.argtypes=arguments
        function.restype=result

def _checked(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value

def self_peak_kib() -> int:
    if os.name == 'nt':
        memory=Memory()
        memory.cb=ctypes.sizeof(memory)
        _checked(kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                               ctypes.byref(memory),memory.cb))
        return (memory.PeakWorkingSetSize+1023)//1024
    if resource is None or sys.platform not in ('linux','darwin'):
        raise RuntimeError('unsupported native memory measurement')
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int((peak+1023)//1024) if sys.platform=='darwin' else int(peak)

def process_cpu_seconds(process) -> float:
    """Read the owned Windows child's handle after wait, before handle release."""
    creation,exit_time,kernel_time,user_time=(w.FILETIME() for _ in range(4))
    _checked(kernel.GetProcessTimes(int(process._handle), *(ctypes.byref(value)
        for value in (creation,exit_time,kernel_time,user_time))))
    return sum((value.dwHighDateTime<<32)+value.dwLowDateTime
               for value in (kernel_time,user_time))/10_000_000

class WindowsJob:
    def __init__(self):
        self.handle=_checked(kernel.CreateJobObjectW(None,None))
        limits=ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags=0x2000  # KILL_ON_JOB_CLOSE
        try:
            _checked(kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),
                                                   ctypes.sizeof(limits)))
        except BaseException:
            self.close()
            raise
    def assign(self,process):
        _checked(kernel.AssignProcessToJobObject(self.handle,int(process._handle)))
    def terminate(self):
        _checked(kernel.TerminateJobObject(self.handle,2))
    def cpu_seconds(self):
        # Includes completed descendants: a venv's python.exe can be only a
        # launcher, so GetProcessTimes on the direct Popen handle is insufficient.
        accounting=Accounting()
        _checked(kernel.QueryInformationJobObject(self.handle,1,ctypes.byref(accounting),
                                                  ctypes.sizeof(accounting),None))
        return (accounting.TotalUserTime+accounting.TotalKernelTime)/10_000_000
    def close(self):
        if self.handle:
            _checked(kernel.CloseHandle(self.handle))
            self.handle=None
