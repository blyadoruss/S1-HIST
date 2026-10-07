using System.Reflection;
using SafePluginLoader.Contract;

namespace SafePluginLoader;

public static class PluginManager
{
    public static LoadedPlugin Load(string dllPath, IPluginContext context)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(dllPath);
        ArgumentNullException.ThrowIfNull(context);

        string fullPath = Path.GetFullPath(dllPath);
        if (!File.Exists(fullPath))
            throw new FileNotFoundException("Plugin DLL was not found.", fullPath);
        if (!string.Equals(Path.GetExtension(fullPath), ".dll", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("The plugin must be a .dll file.", nameof(dllPath));

        var loadContext = new PluginLoadContext(fullPath);
        try
        {
            Assembly assembly = loadContext.LoadFromAssemblyPath(fullPath);
            Type[] pluginTypes = assembly.GetTypes()
                .Where(type => typeof(IPlugin).IsAssignableFrom(type)
                    && type is { IsClass: true, IsAbstract: false }
                    && type.GetConstructor(Type.EmptyTypes) is not null)
                .ToArray();

            if (pluginTypes.Length != 1)
                throw new InvalidOperationException(
                    $"Expected exactly one public IPlugin implementation; found {pluginTypes.Length}.");

            var plugin = (IPlugin)Activator.CreateInstance(pluginTypes[0])!;
            plugin.Start(context);
            return new LoadedPlugin(loadContext, plugin);
        }
        catch
        {
            loadContext.Unload();
            throw;
        }
    }
}
