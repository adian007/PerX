# Run in an elevated PowerShell session (Run as Administrator).
# Allows phones/tablets on the same Wi-Fi to reach PerX.
#
# From repo root:
#   cd D:\PerX
#   .\scripts\open-lan-firewall.ps1

New-NetFirewallRule -DisplayName "PerX Vite" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "PerX API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

Write-Host "Firewall rules added. Open http://<your-LAN-IP>:5173 on another device."
