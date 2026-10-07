using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

namespace Testicles
{
    public class ConsoleH
    {
        public static class ConsoleHelper
        {
            [DllImport("kernel32.dll")]
            public static extern bool AllocConsole();

            [DllImport("kernel32.dll")]
            public static extern bool AttachConsole(int processId);

            [DllImport("kernel32.dll")]
            public static extern bool FreeConsole();
        }
    }
}
