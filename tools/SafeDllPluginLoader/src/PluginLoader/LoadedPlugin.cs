using SafePluginLoader.Contract;

namespace SafePluginLoader;

public sealed class LoadedPlugin : IDisposable
{
    private PluginLoadContext? _context;
    private IPlugin? _plugin;

    internal LoadedPlugin(PluginLoadContext context, IPlugin plugin)
    {
        _context = context;
        _plugin = plugin;
    }

    public string Name => _plugin?.Name ?? "Unloaded";

    public void Dispose()
    {
        IPlugin? plugin = Interlocked.Exchange(ref _plugin, null);
        PluginLoadContext? context = Interlocked.Exchange(ref _context, null);

        if (plugin is not null)
            plugin.Stop();

        context?.Unload();
    }
}
