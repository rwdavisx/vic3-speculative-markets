# Speculative Markets

A Victoria 3 mod about investment, booms, financial panics, and the policies used to manage them. Built against Victoria 3 **1.15.1**.

- [Stable Workshop distribution](https://steamcommunity.com/sharedfiles/filedetails/?id=3831434383)
- [Beta Workshop distribution](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275304)
- [Optional CMF compatibility patch](https://steamcommunity.com/sharedfiles/filedetails/?id=3839275348)

Enable exactly one channel: stable or beta. With Community Mod Framework, load CMF first, your chosen Speculative Markets channel second, and the compatibility patch last.

## Source and builds

`tools/` contains the Python generators; edit those rather than generated gameplay files. `mod/` is the stable output, `beta/mod/` the separate beta output, and `compatibility/cmf/` contains the independent compatibility builder and output. Source artwork is in `art/raw/`; translations are in `tools/i18n/`.

The current development environment uses Windows, Python 3.13, Pillow, and an installed copy of Victoria 3 at `G:/SteamLibrary/steamapps/common/Victoria 3`. Some tooling also refers to local test saves and profiles. These dependencies are not bundled; adjust paths for a different installation. Logs, saves, crash dumps, and disposable builds are excluded from Git.

Build a candidate without changing stable:

```powershell
$env:SPEC_MOD_OUT = "$PWD/build_scratch/candidate"
py -3 -B tools/generate.py
Copy-Item mod/thumbnail.png "$env:SPEC_MOD_OUT/thumbnail.png"
py -3 -B beta/build.py --source $env:SPEC_MOD_OUT --revision 1
Remove-Item Env:SPEC_MOD_OUT
py -3 -B -m unittest discover -s tests -p "test_*.py"
py -3 -B -m unittest discover -s compatibility/cmf -p "test_*.py"
```

Use a new beta revision for each changed candidate; versioned archives are immutable. Run in-game regression checks in the beta channel before promotion. `tools/notification_testbed.py` creates an isolated profile for the notification crash regression using a local baseline save; fixtures must never ship.

After verification, regenerate stable with `SPEC_MOD_OUT` unset, run `tools/check.py`, compare gameplay bytes against the tested beta, and package with `tools/package_release.py`. `tools/stage_workshop.py` stages an archive with its manifest; `tools/steam_upload.py` previews by default and requires `update <channel> --public --execute` to upload through the logged-in Steam client. Use the changelog matching the packaged version. Local upload bindings/receipts are deliberately excluded from Git.

See [AGENTS.md](AGENTS.md), [beta/README.md](beta/README.md), [CMF instructions](compatibility/cmf/README.md), and [1.0.3 validation](HOTFIX_1.0.3.md) for release details.
