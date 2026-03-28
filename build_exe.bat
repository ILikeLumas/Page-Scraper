@echo off
setlocal
py -m PyInstaller --noconfirm PageScrapper.spec
echo.
echo Build complete. Open dist\PageScrapper.exe
endlocal
