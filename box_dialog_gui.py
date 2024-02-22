from tkinter import Tk, ttk, Toplevel
from typing import Optional
from backup import Backup
from boxsdk import folder

class BoxFolder():
    '''
    BoxFolder objects help navigate forward and backward. Act as linkedlist to go back to parent.
    '''
    def __init__(self, parent: Optional['BoxFolder'], cur_folder: folder.Folder) -> None:
        self.parent = parent
        self.folder = cur_folder

class BoxNav():
    '''
    Box Navigation dialog window class. 
     
    Methods: 
        - nav_back() -> navigates back to parent folder
        - nav_forward() -> navigates forward to double clicked folder's directory
        - display_folders() -> displays all the subfolders in a directory
        - highlight() -> highlights folders when clicked
        - set_backup_dir() -> sets the backup directory to the selected file
        - closing_box_dialog() -> ensures that highlighted is reset 
    '''
    backup: Backup
    highlighted: Optional[ttk.Label]
    selected_backup_folder: ttk.Label
    dialog: Toplevel
    dialog_frm: ttk.Frame
    cur_folder: list[BoxFolder]
    back: ttk.Button
    select: ttk.Button

    def __init__(self, backup: Backup, base: Tk, selected_backup_folder: ttk.Label) -> None:
        '''
        - backup -> passed by pointer from the base_gui object instance.
        - base -> the base window for the app
        - selected_backup_folder -> the label that displays the current box directory that files/folders will be backedup to
        - cur_folder -> list keeping track of all the folders in a directory
        - back -> button to navigate back
        - select -> button to set folder as the backup directory
        '''
        self.backup = backup
        self.highlighted = None
        self.selected_backup_folder = selected_backup_folder

        self.dialog = Toplevel(base)
        self.dialog.geometry('420x300')
        self.dialog.title('Set Box Backup Folder')

        self.dialog_frm = ttk.Frame(self.dialog)
        self.dialog_frm.grid()

        self.cur_folder = [BoxFolder(None, self.backup.base_backup)]

        self.back = ttk.Button(self.dialog_frm, text="Back", padding=2, width=10)
        self.back.grid(row=0, column=0, padx=2)
        
        self.select = ttk.Button(self.dialog_frm, text='Select', padding=2, width=10)
        self.select.grid(row = 0, column= 1) 
    
    def nav_back(self):
        '''
        Checks if the current folder is not the root BSCi folder, otherwise navigates back.
        '''
        if self.cur_folder[0].parent is not None and self.cur_folder[0].parent.parent is not None:
            parent = self.cur_folder[0].parent.parent.folder
            self.cur_folder = [BoxFolder(self.cur_folder[0].parent.parent, item) for item in parent.get_items() if item.get().type == 'folder']
        else: 
            self.cur_folder = [BoxFolder(None, self.backup.base_backup)]

        self.display_folders()

    def nav_forward(self, folder: BoxFolder):
        '''
        Navigates into the double clicked folder and updates the cur_folder to 
        '''
        self.cur_folder = [BoxFolder(folder, item) for item in folder.folder.get_items() if item.get().type == 'folder']
        if not self.cur_folder:
            self.cur_folder = [BoxFolder(folder, None)]
        self.display_folders()


    def display_folders(self):
        '''
        1) Destroys all the displayed folders if any are displayed.
        2) Iterates over all the folders in the current directory and prints them into a grid with 4 columns
            - each folder has a click (<Button-1>) and double-click (<Double-Button-1>) event bound to it
            
        '''
        for widget in self.dialog_frm.winfo_children():
            if isinstance(widget, ttk.Label):
                widget.destroy()

        self.back['command'] = lambda: self.nav_back()
        self.select['state'] = 'disabled'

        for ind, folder in enumerate(self.cur_folder):
            if folder.folder:
                folder_icon = ttk.Label(self.dialog_frm, text= folder.folder.get().name, padding=15, border=5, relief='solid')           
                folder_icon['width'] = max(10, len(folder.folder.get().name))
                # print((ind // 4) + 1, ind % 4)
                folder_icon.grid(row= (ind // 4) + 1, column = ind % 4, padx=5, pady=5)
                folder_icon.bind("<Button-1>", lambda e, folder = folder: self.highlight(e, folder))
                folder_icon.bind("<Double-Button-1>", lambda e, folder = folder: self.nav_forward(folder))

    def highlight(self, e, folder: BoxFolder):
        '''
        For the clicked foldder, highlights it if it wasn't already highlighted and unhiglightes any other folders that
        were highlighted.
        '''
        pressed = e.widget
        color = pressed.cget('background')

        if color != '':
            pressed['background'] = ''
            self.select['state'] = 'disabled'
            self.highlighted = None
        else:
            if isinstance(self.highlighted, ttk.Widget) and self.highlighted.winfo_exists() == 1:
                try:
                    self.highlighted['background'] = ''
                except Exception as e:
                    print("ERROR", e)

            pressed['background'] = 'light blue'
            self.highlighted = pressed
            self.select['state'] = 'normal'
            self.select['command'] = lambda: self.set_backup_dir(folder)

    def set_backup_dir(self, curfolder: BoxFolder):
        '''
        Sets the selected folder as the backup directory and updates the text for the label showing the box backup directory 
        '''
        if self.backup.backup_folder != curfolder.folder:
            self.backup.backup_folder = curfolder.folder
            self.selected_backup_folder['text'] = self.backup.backup_folder.get().name

        self.highlighted = None
        self.dialog.destroy()

