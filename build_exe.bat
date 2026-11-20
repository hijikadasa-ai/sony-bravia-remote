@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/3] 安装依赖...
python -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller || goto :fail
echo [2/3] 生成图标...
python tools\make_icon.py || goto :fail
echo [3/3] 打包单文件 exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name SonyTVRemote ^
  --icon assets\app.ico ^
  --paths . ^
  --add-data "assets;assets" ^
  run_app.py || goto :fail
echo.
echo 打包完成：dist\SonyTVRemote.exe
pause
exit /b 0
:fail
echo.
echo 打包失败，请检查上面的错误信息。
pause
exit /b 1
