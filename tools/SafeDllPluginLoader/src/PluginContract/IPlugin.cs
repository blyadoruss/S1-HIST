namespace SafePluginLoader.Contract;

public interface IPlugin
{
    string Name { get; }
    void Start(IPluginContext context);
    void Stop();
}

public interface IPluginContext
{
    string HostName { get; }
    void Log(string message);
}
