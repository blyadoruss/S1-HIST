# Safe DLL Plugin Loader

This project loads a managed .NET plugin into the application that calls
`PluginManager.Load`. It does not open, modify, or inject code into another
process.

## Build

```powershell
dotnet build SafeDllPluginLoader.slnx -c Release
```

## Run the sample

```powershell
dotnet run --project src/DemoHost -c Release -- `
  samples/HelloPlugin/bin/Release/net8.0/HelloPlugin.dll
```

Press Enter to call `Stop`, unload the plugin context, and exit.

## Integrate it into your program

Reference `PluginContract` and `PluginLoader`, implement `IPluginContext`, then
call:

```csharp
LoadedPlugin plugin = PluginManager.Load(pathToDll, context);
```

Keep the returned object while the plugin is active and dispose it when the
program no longer needs the plugin.

Plugin DLLs execute with the same permissions as the host application. Load
only plugins you trust. The host must explicitly call the loader; this project
does not target an arbitrary selected executable.
