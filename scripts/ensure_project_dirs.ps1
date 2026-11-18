$KeepDirectories = @(
    "data\raw",
    "data\interim",
    "data\processed",
    "data\exports",
    "logs"
)

foreach ($Directory in $KeepDirectories) {
    New-Item -ItemType File -Force -Path "$Directory\.gitkeep" | Out-Null
}