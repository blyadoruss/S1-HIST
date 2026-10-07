using SafePluginLoader;
using SafePluginLoader.Contract;

if (args.Length != 1)
{
    Console.Error.WriteLine("Usage: DemoHost <plugin.dll>");
    return 2;
}

try
{
    using LoadedPlugin plugin = PluginManager.Load(args[0], new HostContext());
    Console.WriteLine($"Loaded: {plugin.Name}");
    Console.WriteLine("Press Enter to unload the plugin and exit.");
    Console.ReadLine();
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine(error.Message);
    return 1;
}

sealed class HostContext : IPluginContext
{
    public string HostName => "DemoHost";
    public void Log(string message) => Console.WriteLine($"[plugin] {message}");
}
