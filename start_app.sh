echo Starting ...

if [ -d "venv" ]; then
    venv/Scripts/activate
    echo Enviormnet Found
else
    echo Enviormnet Not Found
    python3 -m venv venv
    echo  Enviormnet Created
    source venv/bin/activate
    pip3 install -r requirements.txt
    echo Dependencies Installed
fi

python3 src/box_backup_app.py

