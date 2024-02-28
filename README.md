# Box_Backup_App

This is a desktop app to automate Box backup for the Biological Sciences Department at the University of Chicago. It uses the boxsdk library and tkinter to backup local files and folders to a selected online box directory. 

Interesting features include:
  - OAuth2 authentication using a local server running on a separate thread.
  - Navigation of online Box folder structure locally.
  - Custom recursive backing up of local folders checking for existing version of sub files and sub directories.
  - Live log dialog box while backing up showing progress and results of each backup.
    
