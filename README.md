# box-backup

This is a desktop app to automate Box backup for the Biological Sciences Department at the University of Chicago. It uses the boxsdk library and tkinter to back up local files and folders to a selected online box directory. 

Interesting features include:
  - OAuth2 authentication using a local server running on a separate thread.
  - Navigation of online Box folder structure locally.
  - Custom recursive backing up of local folders checking for existing versions of local sub files and subdirectories.
  - Live log dialog box while backing up showing progress and results of each backup.

To reuse, replace `self.BACKUPFOLDERID = credentials.readline().strip()` to `self.BACKUPFOLDERID = #the box folder you want as the root for back ups`.

    
