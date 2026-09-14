@echo off
echo Syncing project to GitHub and Cloud...
git add .
git commit -m "Auto update: %date% %time%"
git push origin main
echo Done! Cloud is updating.
pause