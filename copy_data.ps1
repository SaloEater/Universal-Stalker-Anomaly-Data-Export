param(
    [Parameter(Mandatory=$true)]
    [string]$version,

    [Parameter(Mandatory=$false)]
    [string]$source = "C:\Stalker_GAMMA\overwrite\bin",

    [Parameter(Mandatory=$false)]
    [string]$destination = "C:\Source\Other\stalker-anomaly-gamma-db\data\"
)

$destinationWithVersion = "$destination$version"

New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item "$source\*.csv" $destinationWithVersion -Force

Write-Host "Copied data from $source"
Write-Host "Copied data to $destinationWithVersion"
