using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace Memory.Win64
{
    sealed class MemoryHelper64 : IDisposable
    {
        private readonly SafeProcessHandle handle;
        private readonly Process process;
        private readonly ulong moduleBase;

        public MemoryHelper64(Process target)
        {
            if (IntPtr.Size != 8) throw new InvalidOperationException("Run the x64 build.");
            process = target;
            moduleBase = (ulong)target.MainModule.BaseAddress.ToInt64();
            handle = OpenProcess(0x0010 | 0x0020 | 0x0008 | 0x1000, false, target.Id);
            if (handle.IsInvalid)
            {
                int error = Marshal.GetLastWin32Error();
                handle.Dispose();
                throw new Win32Exception(error, "Cannot open HOI4. Check process permissions.");
            }
        }

        public ulong GetBaseAddress(ulong rva) { return checked(moduleBase + rva); }
        public T ReadMemory<T>(ulong address) where T : struct
        {
            Check(address);
            int size = Marshal.SizeOf(typeof(T));
            byte[] bytes = new byte[size];
            UIntPtr count;
            if (!ReadProcessMemory(handle, new IntPtr((long)address), bytes, (UIntPtr)size, out count)
                || count.ToUInt64() != (ulong)size)
                throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot read HOI4 memory.");
            GCHandle pin = GCHandle.Alloc(bytes, GCHandleType.Pinned);
            try { return (T)Marshal.PtrToStructure(pin.AddrOfPinnedObject(), typeof(T)); }
            finally { pin.Free(); }
        }

        public bool WriteMemory<T>(ulong address, T value) where T : struct
        {
            Check(address);
            int size = Marshal.SizeOf(typeof(T));
            byte[] bytes = new byte[size];
            GCHandle pin = GCHandle.Alloc(bytes, GCHandleType.Pinned);
            try { Marshal.StructureToPtr(value, pin.AddrOfPinnedObject(), false); }
            finally { pin.Free(); }
            UIntPtr count;
            if (!WriteProcessMemory(handle, new IntPtr((long)address), bytes, (UIntPtr)size, out count)
                || count.ToUInt64() != (ulong)size)
                throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot write HOI4 memory.");
            return true;
        }

        private void Check(ulong address)
        {
            if (handle.IsClosed || process.HasExited) throw new InvalidOperationException("HOI4 has closed. Restart AdamHook after starting the game.");
            if (address < 0x10000 || address > long.MaxValue) throw new InvalidOperationException("Game data is not ready. Load a save first.");
        }
        public void Dispose() { handle.Dispose(); }
        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern SafeProcessHandle OpenProcess(uint access, bool inheritHandle, int processId);
        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool ReadProcessMemory(SafeProcessHandle process, IntPtr address, byte[] buffer, UIntPtr size, out UIntPtr count);
        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool WriteProcessMemory(SafeProcessHandle process, IntPtr address, byte[] buffer, UIntPtr size, out UIntPtr count);
    }
}
