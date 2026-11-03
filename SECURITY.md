# Security notice: this is not the abandoned C# "VRCHub"

This repository is Ben's Python VRChat toolkit. It has no connection to the C# project at github.com/MagmaMCDev/VRCHub. That project's backend is dead and its release is flagged by Windows Defender. Do not install it.

## What testing found in VRCHub 1.3.0 on Nov 2, 2026

Release tested: VRCHub-1.3.0x64.zip, sha256 5F7A92799A764B004D8E6C1B269E7571E951770D6681BC64C41910CB052DCE1A

- Backend gone: vrchub.site, api.vrchub.site, software.vrchub.site and datapacks.vrchub.site all fail DNS. The magmamc.dev proxy fallback returns 404.
- The app never shows a UI. It exits at the splash screen because MainWindow.CheckServer calls Environment.Exit(2) when the status checks fail.
- With no UI and no user consent it registered scheduled task VRCHub with a logon trigger and RunLevel HighestAvailable, pointing at Plugins/VRCHubTaskScheduler.exe, a file that is not even in the release archive.
- Windows Defender flagged that file as Trojan:Win32/Kepavll!rfn, severity 5, at 5:36 PM. It never executed.
- setup.iss silently adds Defender exclusions for the install directory and %LOCALAPPDATA%/VRCHub.
- The binaries chain to an untrusted certificate, CN=ZER0 Team, O=ZER0 Team, Birmingham, GB. VRCHubNative.exe and MagmaMc.MagmaSimpleConfig.exe are unsigned.

## Use these instead

- VRCX: https://github.com/vrcx-team/VRCX
- VRCOSC: https://github.com/VolcanicArts/VRCOSC
- MagicChatbox: https://github.com/BoiHanny/vrcosc-magicchatbox
- This project

Cleanup, if you already ran it: delete the VRCHub scheduled task with schtasks, remove any Defender exclusions for VRCHub, then delete the install folder.
