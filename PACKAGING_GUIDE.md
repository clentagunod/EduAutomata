# Windows Packaging Guide

This guide builds Edu Automata as a **one-directory** PyInstaller application, then wraps the entire application folder in a per-user Inno Setup installer. The installed app does not need Python on the target computer.

The project entry point is `main.py`. The Python package is `source/`. The app database and workbook export are stored separately under `%LOCALAPPDATA%\Edu Automata`, so they are not included in the installer and are not removed when the app is uninstalled.

## 1. Prepare a Clean Build Environment

Use 64-bit Python 3.12 on the build computer. A separate environment avoids accidentally collecting unrelated packages from the Conda environment.

Open PowerShell in the project root, the folder containing `main.py`, then run:

```powershell
py -3.12 -m venv .venv-packaging
.\.venv-packaging\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install auto-py-to-exe
```

If PowerShell blocks activation, use the environment's Python directly instead:

```powershell
.\.venv-packaging\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-packaging\Scripts\python.exe -m pip install auto-py-to-exe
.\.venv-packaging\Scripts\python.exe -m auto_py_to_exe
```

The requirements use `PySide6-Essentials`; do not install the full PySide6 Addons package for this app. The charts are drawn by Qt and do not need Matplotlib or NumPy.

## 2. Configure auto-py-to-exe

Launch the GUI from the activated build environment:

```powershell
python -m auto_py_to_exe
```

Set the Basic options as follows:

| Option | Value |
| --- | --- |
| Script Location | Project-root `main.py` |
| Onefile | **One Directory** |
| Console Window | **Window Based** (hide console) |
| Icon | Project-root `edu-automata.ico` |
| Output Directory | Project-root `dist` |

For Advanced options, set the application name to `EduAutomata` and enable `--clean` and `--noconfirm` if those fields are available. Under **Additional Files**, add the project-root `edu-automata.ico` with destination `.`. The icon option sets the executable's Windows icon; the additional-file entry lets Qt load the same icon for the window at runtime. Leave other hidden imports, collect-all, and additional data files empty. In particular, do not add `csv_files`, an SQLite database, the build virtual environment, or the whole PySide6 installation as extra files.

Click **Convert .py to .exe**. The output should look like this:

```text
dist/
└── EduAutomata/
    ├── EduAutomata.exe
    └── supporting files and folders
```

Keep the entire `dist\EduAutomata` folder together. The executable needs its supporting Qt DLLs and plugins; copying only `EduAutomata.exe` will not work.

### Command-line alternative

Instead of auto-py-to-exe, the included spec is also configured for one-directory output:

```powershell
pyinstaller --noconfirm --clean EduAutomata.spec
```

This produces `dist\EduAutomata\`. Do not select one-file mode when using the installer workflow below.

## 3. Test the Build Folder

Before making an installer, launch `dist\EduAutomata\EduAutomata.exe` directly and verify:

1. The app opens without requiring Python or a console window.
2. A fresh install has no learners; the SQLite database is created at `%LOCALAPPDATA%\Edu Automata\database\records.sqlite3`.
3. You can add a learner, save attendance and scores, close the app, and see the records after reopening it.
4. Settings can create an Excel export at a location you choose.

For a true fresh-start test, use another Windows account, Windows Sandbox, or a clean virtual machine. Do not delete your working database to simulate a new installation.

## 4. Create the Inno Setup Script

Install Inno Setup on the build computer. Create `installer\EduAutomata.iss` with the following script. The `[Files]` entry recursively includes the complete one-directory PyInstaller output.

```iss
#define AppName "Edu Automata"
#define AppVersion "1.0.0"
#define AppExeName "EduAutomata.exe"
#define ProjectRoot AddBackslash(SourcePath) + ".."
#define BuildDir ProjectRoot + "\dist\EduAutomata"

[Setup]
AppId={{7A46131A-B7E9-43D9-913E-21582B9706A1}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ClentIndustries
DefaultDirName={localappdata}\Programs\Edu Automata
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=.
OutputBaseFilename=EduAutomata-Setup-{#AppVersion}
SetupIconFile={#ProjectRoot}\edu-automata.ico
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
```

Keep the same `AppId` for every future release so Inno Setup recognizes upgrades to the same product. Increment `AppVersion` before each release. The sample installs per-user under Local AppData and does not require administrator rights.

Compile the script in Inno Setup Compiler: open `installer\EduAutomata.iss` and click **Compile**. The installer will be written beside the script as `EduAutomata-Setup-1.0.0.exe`.

The script intentionally has no uninstall deletion rule for `%LOCALAPPDATA%\Edu Automata`. That preserves the user's database and workbook if they uninstall or upgrade the program. Do not add a recursive delete for that data directory unless you specifically want uninstall to erase user records.

## 5. Test the Installer

Test the generated installer on a clean Windows account or machine that does not have Python installed:

1. Run the installer and confirm it can install without administrator privileges.
2. Launch from the Start menu shortcut and verify the fresh learner list is empty.
3. Add a learner and create records; restart the app and confirm they persist.
4. Uninstall, reinstall, and confirm the database remains. This is intentional user-data preservation.

## Size Expectations

One-directory mode makes the main `.exe` smaller, but it does not remove the Qt runtime; the supporting files must ship with it. Inno Setup compresses the full directory into the installer, so the installer download is generally smaller than the unpacked app folder.

The project has already removed Matplotlib and NumPy, and the clean build environment uses PySide6 Essentials rather than Qt Addons. A 20 MB total installer is still unlikely with a PySide6 desktop app. The exact size depends on the Python and PyInstaller versions and should be measured from the produced installer. Getting substantially below the Qt runtime footprint would require switching to a lighter UI toolkit and reworking the interface.

## Common Problems

- **The app says a Qt platform plugin could not be found:** install the entire `dist\EduAutomata` folder through Inno Setup. Do not package only the EXE.
- **The output is still unusually large:** confirm the build used `.venv-packaging`, one-directory mode, and no `collect-all` or extra data-file options. Rebuild after deleting the previous `build` and `dist` output folders.
- **A console window appears:** choose **Window Based** in auto-py-to-exe, or keep `console=False` in the spec.
- **The database looks empty after reinstall:** confirm the app is running under the same Windows account. Each account has its own `%LOCALAPPDATA%` database.
- **Inno reports that it cannot find the app files:** build first and verify `dist\EduAutomata\EduAutomata.exe` exists; then compile the installer script from its `installer` directory.