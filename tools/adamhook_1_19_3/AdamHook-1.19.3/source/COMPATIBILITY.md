# Target executable

HOI4 Windows Steam: Operation Postern v1.19.3.0.c01a (5632).

SHA-256: `7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5`

Offsets are RVAs relative to the loaded hoi4.exe module, not absolute addresses.
The application refuses a different executable hash before opening memory for writes.

## Static evidence from this executable

- FOW: byte RVA `0x332F63A`, command callback `0x2589F0`, store at `0x258A32`.
- AllowTraits: byte RVA `0x332F618`, callback `0x23E5E0`, store at `0x23E645`.
- Debug: byte RVA `0x332EC69`, callback `0x24C670`, store at `0x24C6BE`.
- Research on click: byte RVA `0x332F616`, callback `0x27D6D0`, store at `0x27D717`.
- Instant construction: byte RVA `0x332F628`, callback `0x262D90`, store at `0x262DD0`.
- Allow diplomacy: byte RVA `0x332F617`, callback `0x23DE30`, store at `0x23DE95`.
- Instant war goals: byte RVA `0x332F644`, callback `0x263610`, store at `0x263652`.
- Instant training: byte RVA `0x332F62B`, callback `0x262B10`, store at `0x262B50`.
- Focus.AutoComplete: byte RVA `0x332F62C`, registered at `0x13DD0`.
- Focus.NoChecks: byte RVA `0x332F631`, registered at `0x13E30`.
- Tdebug: pointer at RVA `0x333CFB8`, byte field `+0x80`. Getter `0xE139B0`, flag read `0xE137C0`, flag setter `0xE16D00`. The old four-byte write is replaced with a one-byte write.
- Country: game-state pointer at RVA `0x332F260`, current country ID field `+0x520` (Int32). The tag callback at `0x28CF80` calls `0x12A9560`, which reads this field at `0x12A9694` onward. The original direct-write behavior is retained; it does not execute all side effects of the game's tag command.

Pointer fields are resolved again before each operation. The UI does not retain a game-state pointer across save loads.

## Validation and limits

- Release x64 compiled successfully with Visual Studio MSBuild and the installed .NET Framework runtime assemblies (FrameworkPathOverride), because this machine lacks the 4.8 reference assembly pack.
- Memory smoke tests passed using only the test process's own allocated memory: byte/Int32 round trips, preservation of neighboring bytes, rejection of null and unreadable addresses, disconnected controls and all ten flag bindings.
- Static checks verify the executable hash, RIP-relative references, writable target sections, and Tdebug accessor width.
- No live HOI4 gameplay, country switching, multiplayer, or save/load transition tests were performed. Static address verification is not confirmation of every in-game effect. Direct flag writes also omit any extra refresh calls made by a console command (for example FOW).
- Input to Tagswitch must be an actual numeric country ID from this running save, not a three-letter tag. The application checks that it is a positive integer, but does not validate membership in the game's country database.
- Focus.NoChecks and Focus.IgnorePrerequisites are separate game flags; this application retains the original NoChecks control.
