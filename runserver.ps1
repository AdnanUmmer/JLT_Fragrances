$env:VIRTUAL_ENV = Join-Path $PSScriptRoot ".venv"
$sitePackages = Join-Path $env:VIRTUAL_ENV "Lib\\site-packages"
if (Test-Path $sitePackages) {
    if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
        $env:PYTHONPATH = $sitePackages
    } else {
        $env:PYTHONPATH = "$sitePackages;$env:PYTHONPATH"
    }
}

& "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.11_3.11.2544.0_x64__qbz5n2kfra8p0\python3.11.exe" manage.py runserver @args
