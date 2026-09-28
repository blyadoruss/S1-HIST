using System;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Memory.Win64;
using Testicles;

internal static class MemorySmokeTests
{
    private static void Assert(bool ok, string message)
    { if (!ok) throw new Exception(message); }

    [STAThread]
    private static void Main()
    {
        IntPtr block = Marshal.AllocHGlobal(16);
        try
        {
            for (int i = 0; i < 16; i++) Marshal.WriteByte(block, i, 0xA5);
            using (var memory = new MemoryHelper64(Process.GetCurrentProcess()))
            {
                ulong address = (ulong)block.ToInt64();
                memory.WriteMemory(address + 4, (byte)1);
                Assert(memory.ReadMemory<byte>(address + 4) == 1, "Byte round trip failed");
                Assert(Marshal.ReadByte(block, 3) == 0xA5 && Marshal.ReadByte(block, 5) == 0xA5,
                    "Byte write corrupted adjacent data");
                memory.WriteMemory(address + 8, 123456);
                Assert(memory.ReadMemory<int>(address + 8) == 123456, "Int32 round trip failed");
                Assert(Marshal.ReadByte(block, 7) == 0xA5 && Marshal.ReadByte(block, 12) == 0xA5,
                    "Int32 write corrupted adjacent data");
                bool rejected = false;
                try { memory.WriteMemory(0, (byte)1); }
                catch (InvalidOperationException) { rejected = true; }
                Assert(rejected, "Null address was not rejected");
                rejected = false;
                try { memory.ReadMemory<byte>(0x7FFFFFFE0000); }
                catch (System.ComponentModel.Win32Exception) { rejected = true; }
                Assert(rejected, "Unreadable address was not rejected");
            }
            using (var form = new Form1())
            {
                Assert(form.Text.Contains("1.19.3"), "Wrong target version");
                foreach (string name in new[] { "button1", "button3", "button8", "button23" })
                {
                    var control = (Control)typeof(Form1).GetField(name, BindingFlags.NonPublic | BindingFlags.Instance).GetValue(form);
                    Assert(!control.Enabled, name + " enabled before attaching");
                }
                var flags = (System.Collections.ICollection)typeof(Form1).GetField("flags", BindingFlags.NonPublic | BindingFlags.Instance).GetValue(form);
                Assert(flags.Count == 10, "Missing flag controls");
            }
            Console.WriteLine("PASS: byte/int32 reads and writes, adjacent-byte preservation, invalid-address rejection, disconnected UI, 10 flags.");
        }
        finally { Marshal.FreeHGlobal(block); }
    }
}
