@echo off
rem Gündelik kullanım: çift tıklayınca konsol penceresi olmadan başlar.
rem Kontrol paneli tarayıcıda açılır, kapatmak için paneldeki "Servisi kapat" düğmesi kullanılır.
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" gundelik.py %*
) else (
    start "" pythonw gundelik.py %*
)
