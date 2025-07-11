@echo off
echo 安装游戏自动化脚本依赖项...
echo.

echo 正在安装必要的Python包...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo 依赖项安装失败！
    echo 请检查网络连接和Python环境
    echo.
    pause
    exit /b 1
)

echo.
echo 依赖项安装完成！
echo 现在可以运行 启动GUI.bat 来启动程序
echo.
pause
