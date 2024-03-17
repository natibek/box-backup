@ECHO OFF

if exist venv\ (
    venv\Scripts\activate
    ECHO Enivornment Found
    python src\box_backup_app.py
) else (
    ECHO Enivornment Not Found

    python -m venv venv
    venv\Scripts\activate
    ECHO Enivornment Created

    pip install -r requirements.txt
    ECHO Dependencies Installed

    python src\box_backup_app.py
)