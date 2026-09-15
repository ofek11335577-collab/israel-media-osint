@echo off
chcp 65001 > nul
cd /d C:\python\global-media-osint

echo [1/3] מוסיף את כל השינויים המקומיים...
git add .

echo [2/3] שומר שינויים (Commit)...
git commit -m "Auto-sync update from local machine"

echo [3/3] מעלה ל-GitHub (מעדכן את הענן)...
git push origin main

echo.
echo ===================================================
echo  הסנכרון הסתיים בהצלחה! האתר בענן מתעדכן כעת.
echo ===================================================
pause