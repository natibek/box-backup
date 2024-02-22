from base_gui import BaseGui
from backup import Backup

if __name__ == "__main__":
    '''
    Creates an instance of the Backup object and uses it when creating an instance of the BaseGui that is used for 
    the app interface.
    '''
    backup = Backup()
    app_gui = BaseGui(backup)