using SafePluginLoader.Contract;

namespace SamplePlugin;

public sealed class HelloPlugin : IPlugin
{
    private IPluginContext? _context;

    public string Name => "Hello plugin";

    public void Start(IPluginContext context)
    {
        _context = context;
        context.Log($"Started inside {context.HostName}.");
    }

    public void Stop()
    {
        _context?.Log("Stopped.");
        _context = null;
    }
}
