$destination = "C:\Stalker_GAMMA\overwrite\gamedata\scripts"
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item "gamedata\scripts\universal_anomaly_data_export.script" $destination -Force
Copy-Item "gamedata\scripts\arti_jamming.script" $destination -Force

Write-Host "Copied script to $destination"
