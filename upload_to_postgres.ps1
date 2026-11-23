<#
.SYNOPSIS
    Portable script to create tables and upload Consumer-360 CSVs to local PostgreSQL and/or Supabase using psql \copy.
.DESCRIPTION
    Resolves .env and data\supabase_db relative to the script location (no hardcoded user paths).
    Reads PG_* and SUPABASE_DB_* variables from .env, stripping optional quotes.
    In default 'replace' mode, drops and recreates each table so column names and types always match the CSVs.
.EXAMPLE
    .\upload_to_postgres.ps1
    .\upload_to_postgres.ps1 -Target supabase
    .\upload_to_postgres.ps1 -Target local -Mode append
    .\upload_to_postgres.ps1 -DataDir ".\data\supabase_db" -EnvFile ".\.env"
#>
[CmdletBinding()]
param(
    [ValidateSet("all", "local", "supabase")]
    [string]$Target = "all",

    [ValidateSet("replace", "append")]
    [string]$Mode = "replace",

    [string]$EnvFile = "",
    [string]$DataDir = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
    param([string]$ExplicitPath, [string]$RelativeSubPath)
    if ($ExplicitPath -ne "") {
        return (Resolve-Path $ExplicitPath).Path
    }
    $candidates = @(
        (Join-Path $PSScriptRoot $RelativeSubPath),
        (Join-Path (Split-Path $PSScriptRoot -Parent) $RelativeSubPath),
        (Join-Path (Get-Location).Path $RelativeSubPath)
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return (Resolve-Path $c).Path }
    }
    throw "Could not locate '$RelativeSubPath'. Place this script in the project root (or scripts\) or pass the path explicitly."
}

function Load-DotEnv {
    param([string]$Path)
    $vars = @{}
    foreach ($rawLine in Get-Content -Path $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { continue }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { continue }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
            if ($val.Length -ge 2) {
                $val = $val.Substring(1, $val.Length - 2)
            }
        }
        $vars[$key] = $val
    }
    return $vars
}

if (-not (Get-Command "psql" -ErrorAction SilentlyContinue)) {
    throw "'psql' was not found in PATH. Install PostgreSQL client tools and add its bin folder to PATH."
}

$resolvedEnv = Resolve-ProjectPath -ExplicitPath $EnvFile -RelativeSubPath ".env"
$resolvedDataDir = Resolve-ProjectPath -ExplicitPath $DataDir -RelativeSubPath "data\supabase_db"
$envVars = Load-DotEnv -Path $resolvedEnv

Write-Host "Using .env:     $resolvedEnv" -ForegroundColor Cyan
Write-Host "Using data dir: $resolvedDataDir" -ForegroundColor Cyan

$tables = @(
    @{
        Name = "cohort_retention"
        File = "cohort_retention.csv"
        DDL  = @"
CREATE TABLE IF NOT EXISTS public.cohort_retention (
    "First Purchase Month" TEXT,
    "Months Since First Purchase" INTEGER,
    "Active Customers" INTEGER,
    "Cohort Size" INTEGER,
    "Retention Rate (%)" DOUBLE PRECISION
);
"@
    },
    @{
        Name = "product_bundles"
        File = "product_bundles.csv"
        DDL  = @"
CREATE TABLE IF NOT EXISTS public.product_bundles (
    "Product A Code" TEXT,
    "Product A" TEXT,
    "Product B Code" TEXT,
    "Product B" TEXT,
    "Orders Together" INTEGER,
    "Product A Orders" INTEGER,
    "Product B Orders" INTEGER,
    "Order Share (%)" DOUBLE PRECISION,
    "Buy A -> Buy B (%)" DOUBLE PRECISION,
    "Buy B -> Buy A (%)" DOUBLE PRECISION,
    "Bundle Lift" DOUBLE PRECISION
);
"@
    },
    @{
        Name = "customer_segments"
        File = "customer_segments.csv"
        DDL  = @"
CREATE TABLE IF NOT EXISTS public.customer_segments (
    "Customer ID" BIGINT,
    "Country" TEXT,
    "Last Purchase" TIMESTAMP,
    "Days Inactive" INTEGER,
    "Total Orders" INTEGER,
    "Total Spend" DOUBLE PRECISION,
    "Total Units" INTEGER,
    "Avg Order Value" DOUBLE PRECISION,
    "Recency Score" INTEGER,
    "Frequency Score" INTEGER,
    "Spend Score" INTEGER,
    "Overall Score" INTEGER,
    "Customer Tier" TEXT,
    "Buyer Group" TEXT
);
"@
    },
    @{
        Name = "customer_rfm_metrics"
        File = "customer_rfm_metrics.csv"
        DDL  = @"
CREATE TABLE IF NOT EXISTS public.customer_rfm_metrics (
    "Customer ID" BIGINT,
    "Last Purchase" TIMESTAMP,
    "Total Orders" INTEGER,
    "Total Spend" DOUBLE PRECISION,
    "Total Units" INTEGER,
    "Country" TEXT,
    "Days Inactive" INTEGER,
    "Avg Order Value" DOUBLE PRECISION,
    "Recency Score" INTEGER,
    "Frequency Score" INTEGER,
    "Spend Score" INTEGER,
    "Overall Score" INTEGER
);
"@
    },
    @{
        Name = "retail_transactions"
        File = "retail_transactions.csv"
        DDL  = @"
CREATE TABLE IF NOT EXISTS public.retail_transactions (
    "Invoice No" BIGINT,
    "Product Code" TEXT,
    "Product Name" TEXT,
    "Quantity" INTEGER,
    "Unit Price" DOUBLE PRECISION,
    "Customer ID" BIGINT,
    "Country" TEXT,
    "Order Date" TIMESTAMP,
    "Line Revenue" DOUBLE PRECISION,
    "Year-Month" TEXT,
    "Order Hour" INTEGER
);
"@
    }
)

foreach ($t in $tables) {
    $csvFullPath = Join-Path $resolvedDataDir $t.File
    if (-not (Test-Path $csvFullPath)) {
        throw "Missing CSV file: $csvFullPath"
    }
}

function Invoke-Upload {
    param(
        [string]$Label,
        [string]$DbHost,
        [string]$DbPort,
        [string]$DbName,
        [string]$DbUser,
        [string]$DbPass,
        [string]$SslMode
    )

    if ([string]::IsNullOrWhiteSpace($DbHost) -or [string]::IsNullOrWhiteSpace($DbUser) -or [string]::IsNullOrWhiteSpace($DbPass)) {
        throw "Missing connection variables in .env for $Label."
    }

    Write-Host "`n=== Uploading to $Label ($DbHost`:$DbPort/$DbName) ===" -ForegroundColor Green

    $prevPass = $env:PGPASSWORD
    $prevSsl  = $env:PGSSLMODE
    try {
        $env:PGPASSWORD = $DbPass
        $env:PGSSLMODE  = $SslMode

        foreach ($t in $tables) {
            # psql \copy on Windows requires forward slashes
            $csvPosix = (Join-Path $resolvedDataDir $t.File) -replace '\\', '/'
            $sqlFile  = [System.IO.Path]::GetTempFileName()
            try {
                $dropStmt = if ($Mode -eq "replace") { "DROP TABLE IF EXISTS public.$($t.Name) CASCADE;" } else { "" }
                $sqlContent = @"
$dropStmt
$($t.DDL)
\copy public.$($t.Name) FROM '$csvPosix' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
"@
                Set-Content -Path $sqlFile -Value $sqlContent -Encoding UTF8

                Write-Host "-> Loading $($t.Name) from $($t.File)..." -NoNewline
                & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -f $sqlFile | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    throw "psql failed for $($t.Name) on $Label (exit code $LASTEXITCODE)."
                }
                Write-Host " Done" -ForegroundColor Green
            }
            finally {
                Remove-Item -Path $sqlFile -ErrorAction SilentlyContinue
            }
        }
    }
    finally {
        $env:PGPASSWORD = $prevPass
        $env:PGSSLMODE  = $prevSsl
    }
}

if ($Target -eq "all" -or $Target -eq "local") {
    Invoke-Upload `
        -Label "Local PostgreSQL" `
        -DbHost $envVars["PG_HOST"] `
        -DbPort $envVars["PG_PORT"] `
        -DbName $envVars["PG_DB"] `
        -DbUser $envVars["PG_USER"] `
        -DbPass $envVars["PG_PASSWORD"] `
        -SslMode "prefer"
}

if ($Target -eq "all" -or $Target -eq "supabase") {
    Invoke-Upload `
        -Label "Supabase" `
        -DbHost $envVars["SUPABASE_DB_HOST"] `
        -DbPort $envVars["SUPABASE_DB_PORT"] `
        -DbName $envVars["SUPABASE_DB_NAME"] `
        -DbUser $envVars["SUPABASE_DB_USER"] `
        -DbPass $envVars["SUPABASE_DB_PASSWORD"] `
        -SslMode "require"
}

Write-Host "`nAll requested uploads completed successfully." -ForegroundColor Cyan
