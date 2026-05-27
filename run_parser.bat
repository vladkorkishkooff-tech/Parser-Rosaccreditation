@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ==========================================================
echo       Быстрый запуск Парсера Росаккредитации
echo ==========================================================
echo.

:: Проверка наличия виртуального окружения
if not exist ".venv\Scripts\python.exe" (
    color 0c
    echo [ОШИБКА] Не найдено виртуальное окружение .venv!
    echo Пожалуйста, убедитесь, что папка .venv находится в той же директории, что и этот файл.
    echo Для установки запустите:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Проверка перетаскивания файла (Drag-and-Drop)
set "INPUT_FILE=%~1"
set "LATEST_MODE=N"

if "%INPUT_FILE%"=="" (
    echo [ИНФО] Вы можете просто перетащить ваш Excel/CSV файл мышкой на этот ярлык!
    echo.
    set /p "INPUT_FILE=Шаг 1: Введите имя файла с номерами (или нажмите ENTER для автосбора последних документов): "
) else (
    echo [ИНФО] Обнаружен перетащенный файл: %INPUT_FILE%
)

:: Убираем кавычки, если они есть
set "INPUT_FILE=%INPUT_FILE:"=%"

if "%INPUT_FILE%"=="" (
    echo [ИНФО] Входной файл не указан. Запускается режим автоматического сбора последних документов.
    set "LATEST_MODE=Y"
) else (
    if not exist "%INPUT_FILE%" (
        color 0c
        echo [ОШИБКА] Файл "%INPUT_FILE%" не найден!
        echo Убедитесь, что файл лежит в этой папке или вы указали правильный путь.
        echo.
        pause
        exit /b 1
    )
)

echo.
set /p "OUTPUT_FILE=Шаг 2: Введите имя выходного Excel-файла (по умолчанию result.xlsx): "
if "%OUTPUT_FILE%"=="" set "OUTPUT_FILE=result.xlsx"
set "OUTPUT_FILE=%OUTPUT_FILE:"=%"

echo.
echo ==========================================================
echo       НАЧАЛО РАБОТЫ ПАРСЕРА
echo ==========================================================
if "%LATEST_MODE%"=="Y" (
    echo Режим работы:  Автоматический сбор последних документов (50 серт. + 50 декл.)
) else (
    echo Входной файл:  %INPUT_FILE%
)
echo Выходной файл: %OUTPUT_FILE%
echo.
echo Идет запуск фонового браузера Chromium для авторизации...
echo Пожалуйста, подождите, парсер делает запросы напрямую к API Росаккредитации...
echo.

if "%LATEST_MODE%"=="Y" (
    .\.venv\Scripts\python main.py -o "%OUTPUT_FILE%" -l 50
) else (
    .\.venv\Scripts\python main.py -i "%INPUT_FILE%" -o "%OUTPUT_FILE%"
)

if %ERRORLEVEL% equ 0 (
    color 0a
    echo.
    echo ==========================================================
    echo [УСПЕХ] Парсинг успешно завершен!
    echo Результаты сохранены в файл: %OUTPUT_FILE%
    echo ==========================================================
    echo.
    echo Открываем полученный файл в Excel...
    start "" "%OUTPUT_FILE%"
) else (
    color 0c
    echo.
    echo ==========================================================
    echo [ОШИБКА] Произошел сбой при выполнении парсера.
    echo Убедитесь, что выходной файл не открыт в Excel в данный момент!
    echo ==========================================================
)

echo.
pause
