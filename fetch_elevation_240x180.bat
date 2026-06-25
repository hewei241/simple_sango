@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Fetch 240x180 elevation (Open-Meteo) and generate terrain
echo  Cache file: data\elevation_land_240x180.json
echo  Batch: 20 cells, wait 4 sec between batches
echo  Run this file again anytime to continue from cache.
echo ============================================================
echo.

python scripts\show_elevation_cache.py
echo.

python scripts\generate_from_api.py --fetch-all-elevation --batch-size 20 --sleep-seconds 4
if errorlevel 1 goto failed

echo.
echo SUCCESS. Generated js\china-terrain-data.js
echo Open index.html in browser to view the map.
goto end

:failed
echo.
echo STOPPED with error. Progress saved in data\elevation_land_240x180.json
echo Run this bat file again to continue.

:end
echo.
pause
endlocal
