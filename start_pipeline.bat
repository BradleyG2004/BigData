@echo off
echo ================================================
echo  Polymarket Data Pipeline - Demarrage
echo ================================================
echo.

REM Verifier que Docker est en cours d'execution
echo [1/4] Verification de Docker...
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Docker n'est pas en cours d'execution!
    echo Veuillez demarrer Docker Desktop et reessayer.
    pause
    exit /b 1
)
echo    - Docker OK
echo.

REM Demarrer Kafka avec Docker Compose
echo [2/4] Demarrage de Kafka...
docker-compose up -d
if errorlevel 1 (
    echo ERREUR: Impossible de demarrer Kafka
    pause
    exit /b 1
)
echo    - Kafka demarre
echo.

REM Attendre que Kafka soit pret
echo [3/4] Attente du demarrage de Kafka (10 secondes)...
timeout /t 10 /nobreak >nul
echo    - Kafka pret
echo.

REM Demarrer le consumer en arriere-plan
echo [4/4] Demarrage du consumer...
start "Polymarket Consumer" cmd /k python consumer.py
echo    - Consumer demarre dans une nouvelle fenetre
echo.

echo ================================================
echo  Pipeline pret!
echo ================================================
echo.
echo Pour lancer le producer, executez dans un terminal:
echo    python producer.py
echo.
echo Pour arreter le pipeline:
echo    1. Fermez la fenetre du consumer (Ctrl+C)
echo    2. Executez: docker-compose down
echo.
pause
