from tkinter import filedialog, Tk, Menu, ttk, Toplevel, Listbox, Text, scrolledtext
from tkinter.constants import *
from backup import Backup
from werkzeug import Request, Response, run_simple
import threading, time, os, webbrowser, ctypes
from box_dialog_gui import BoxNav

class BaseGui:
    '''
    Class for the Window of the App. 
    '''
    backup: Backup
    authorization_status: str
    state: str
    oauth_server: threading.Thread
    selected_files: list[str]
    selected_folders: list[str]
    base: Tk
    v: ttk.Scrollbar
    frm: ttk.Frame
    auth_button: ttk.Button
    retry: ttk.Label
    box_nav: BoxNav

    def __init__(self, backup: Backup) -> None:
        '''
        - backup -> the Backup object used for BOX functions such as backing up files/folders, setting the backup directory, and oauth authentication
        - authorization_status -> keeps track of the authorization status of the app. check method waits for it to be changed (helps with checking completion of the localsever thread)
        - state -> keeps track of the state of the window. 
            - either "Processing" or "Backing Up"
        - oauth_server -> the thread for handling oauth authentication
        - selected_folders -> keeps track of the folders that are to be backedup 
        - selected_files -> keeps track of the files that are to be backedup
        - base -> Base Window
        - v_scroll -> the vertical scroll bar
        - auth_button -> the authentication button that triggers the start of the oauth_server thread and open authentication website
        '''

        self.backup = backup
        self.authorization_status = 'Not Started'
        self.state = 'Processing'
        self.oauth_server = threading.Thread(target=self.handle_redirect)
        self.oauth_server.daemon = True
        self.selected_folders = []
        self.selected_files = []

        self.base = Tk('BSci Backup')
        self.base.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.base.title('BSci Backup Application')
        self.base.geometry("600x510")
        self.base.minsize(600,510)
    
        self.frm = ttk.Frame(self.base, padding=10)
        self.frm.pack()

        self.auth_button = ttk.Button(self.frm,text="Authenticate", command=self.open_link, padding=5)
        self.auth_button.pack()

        self.retry = ttk.Label(self.frm, text="Retry Authorization")
        self.retry.pack_forget()

        self.base.mainloop()

    def handle_redirect(self) -> None:
        '''
        Method that will run the oauth_server thread. Receives the csrf and code tokens, uses the backup object instance
        to authorize the user to use the BOX app.
        '''
        # print(threading.current_thread())

        @Request.application
        def app(request: Request) -> Response:
            # print("STARTED", self.backup.authorized, threading.current_thread())
            
            if self.backup.authorized:
                return Response("Already Authorized", 200)
            
            try:
                code = request.args.get('code')
                csrf = request.args.get('state')
                if code and csrf:
                    if self.backup.authenticate(code, csrf):
                        self.authorization_status = "Completed"
                        return Response("Authorized", 200)
                    else:
                        self.authorization_status = "Completed"
                        return Response("Authorization Denied", 200)
                else:
                    self.authorization_status = "Completed"
                    # print("INVALID TOKENS", code, csrf, 2)

                    return Response("Authorization Denied", 200)
            except:
                self.authorization_status = "Completed"
                # print("INVALID TOKENS", code, csrf, 3)

                return Response("Authorization Denied", 200)

        run_simple("localhost", 7000, app)

    def open_link(self):
        '''
        Opens the link, starts the oauth_server thread if it hasn't been started already, and triggers the check_thread method
        to check if the oauth_server thread has received a response from the authentication site.
        '''
        time.sleep(0.05)
        webbrowser.open(self.backup.auth_url)
        self.base.clipboard_append(self.backup.auth_url)

        self.auth_button['state'] = 'disabled'
        self.retry.pack_forget()

        if self.oauth_server.ident not in [thread[0] for thread in threading._active.items()]:
            self.oauth_server.start()
        self.check_thread()

    def check_thread(self):
        '''
        Every second checks the status of the thread. If the authentication was sucessful and the application
        was authorized, closes the thread and opens the backup_page(). Otherwises, displays the retry label and enables
        the authentication button.
        '''

        if self.authorization_status == "Completed":
            self.authorization_status = 'Not Started'

            if self.backup.authorized:
                self.frm.destroy()
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.oauth_server.ident), ctypes.py_object(SystemExit))
                self.backup_page()
            else:
                self.retry.pack()
                self.auth_button["state"] = 'normal'
        else:
            self.base.after(1000, self.check_thread)
    
    def backup_page(self):
        '''
        Handles displaying the main page of the app. 
        - Has menu bar to navigate the box directory with the base at BSCi Backup, select folders to backup, select files to backup
        - Displays selected folders and files that are to be backedup with a button to remove any specific ones.
        - Backup button to trigger the backup. This diables all other buttons.
        '''
        frm = ttk.Frame(self.base, padding=10)
        frm.pack()
        
        menu_bar = Menu(frm)
        self.base.config(menu = menu_bar)

        ttk.Label(frm, text='Backup Folder:' , padding=10).pack()
        selected_backup_folder = ttk.Label(frm, text= self.backup.backup_folder.get().name, padding=10)
        selected_backup_folder.pack()
        menu_bar.add_command(label="Set Box Backup Folder", command = lambda sbf = selected_backup_folder: self.set_box_folder(sbf))

        ttk.Label(frm, text='Selected Folders to back up:', padding=10).pack()
        folder_frm = ttk.Frame(frm, padding=5)
        folder_frm.pack()

        self.folder_list = Listbox(folder_frm, height=7, selectmode='multiple')
        self.folder_list.pack(side='left', fill='both', expand=True, ipadx=2, ipady=2)
        sb_folder= ttk.Scrollbar(folder_frm)
        sb_folder.pack(side='right', fill='y')
        self.folder_list.config(yscrollcommand=sb_folder.set)
        sb_folder.config(command=self.folder_list.yview)

        menu_bar.add_command(label="Select Folders to Backup", command= self.select_folder)

        ttk.Label(frm, text='Selected Files to back up:', padding=10).pack()
        file_frm = ttk.Frame(frm, padding=5)
        file_frm.pack()
    
        self.file_list = Listbox(file_frm, height=9, selectmode='multiple')
        self.file_list.pack(side='left', fill='both', expand=True, ipadx=2, ipady=2)
        sb_file= ttk.Scrollbar(file_frm)
        sb_file.pack(side='right', fill='y')
        self.file_list.config(yscrollcommand=sb_file.set)
        sb_file.config(command=self.file_list.yview)

        menu_bar.add_command(label="Select Files to Backup", command= self.select_files)
        
        frm_buttons = ttk.Frame(frm)
        frm_buttons.pack()
        self.remove_button = ttk.Button(frm_buttons, text="Delete", padding=5, command= self.remove_selected)
        self.remove_button.pack(side='right', pady=5)

        self.backup_button = ttk.Button(frm_buttons, text="Backup", padding=5, command=self.call_backup)
        self.backup_button.pack(side='left', pady=5)
    
    def remove_selected(self):
        '''
        Method to remove selected files or folders from the Listbox and selected folder/file lists.
        '''
        if self.folder_list.curselection() != "" and self.selected_folders:
            for ind in self.folder_list.curselection()[::-1]:
                del self.selected_folders[ind]
                self.folder_list.delete(ind)
    
        if self.file_list.curselection() != "" and self.selected_files:
            for ind in self.file_list.curselection()[::-1]:
                del self.selected_files[ind]
                self.file_list.delete(ind)

    def select_folder(self):
        '''
        Opens the windows dialog for selecting a folder and adds any selected folder to the selected_folders list.
        Displays each folder's name along with a button to remove it from the list of folders to be backedup.
        '''
        if self.state != "Backing Up":
            backup_folder = filedialog.askdirectory()
            
            def remove_folder(sub_frm: ttk.Frame, backup_folder: str):
                if self.state != 'Backing Up':
                    # print(backup_folder, self.selected_folders)
                    sub_frm.destroy()
                    self.selected_folders.remove(backup_folder)

            if backup_folder:
                if backup_folder not in self.selected_folders:
                    self.selected_folders.append(backup_folder)
                    sub_frm = ttk.Frame(self.folder_list)
                    ttk.Label(sub_frm, text=os.path.split(backup_folder)[1], padding = 5).pack(side="left")
                    ttk.Button(sub_frm, text="x", 
                            command = lambda cur_folder = backup_folder, cur_frm = sub_frm: remove_folder(cur_frm, cur_folder), 
                            width=2, padding = 2).pack(side="right")
                    
                    self.folder_list.insert(len(self.selected_folders) - 1, os.path.split(backup_folder)[1])

    def select_files(self):
        '''
        Opens the windows dialog for selecting multiple files and adds any selected files to the selected_files list.
        Displays each files's name along with a button to remove it from the list of files to be backedup.
        '''
        if self.state != "Backing Up":
            backup_files = filedialog.askopenfilenames()
            
            def remove_file(sub_frm: ttk.Frame, file: str):
                if self.state != 'Backing Up':
                    # print(file)
                    sub_frm.destroy()
                    self.selected_files.remove(file)

            for file in backup_files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    sub_frm = ttk.Frame(self.file_list)
                    

                    ttk.Label(sub_frm, text=os.path.split(file)[1], padding=5).pack(side="left")    
                    ttk.Button(sub_frm, text="x", 
                            command= lambda cur_file= file, cur_frm = sub_frm: remove_file(cur_frm, cur_file), 
                            width=2, padding = 2).pack(side="right")
                    self.file_list.insert(len(self.selected_files) - 1, os.path.split(file)[1])
    
    def set_box_folder(self, selected_backup_folder):
        '''
        Creates an instance of the BoxNav object to open a dialog box for navigating box and selecting a new backup directory.
        '''
        if self.state != "Backing Up":
            self.box_nav = BoxNav(self.backup, self.base, selected_backup_folder)
            self.box_nav.display_folders()

    def call_backup(self):
        '''
        If there are any files/folders selected for backup, starts the backup_thread and updates the state of the app.
        '''
        if self.selected_files or self.selected_folders:
            self.backup_button['state'] = 'disabled'
            self.remove_button['state'] = 'disabled'

            self.state = 'Backing Up'
            backup_thread = threading.Thread(target=self.handle_backup)
            backup_thread.start()
        

    def handle_backup(self):
        '''
        Uses the backup instance of the Backup class to back up each selected folder and file. 
        Updates the logs and prints the status of the latest backedup folder/file.
        '''
        log_dialog = Toplevel(self.base)
        log_dialog.geometry('500x400')
        log_dialog.title('Log')

        log_text = Text(log_dialog, height=250, wrap='none', padx=5, pady=5, font=("Arial", 11), state='disabled')
        log_text.pack(ipadx=5, ipady=5)

        temp_folders = self.selected_folders[:]
        if len(temp_folders) > 0:
            log_text.configure(state='normal')
            log_text.insert(END, "Folders:\n" )
            log_text.configure(state='disabled')

        for folder in temp_folders:
            response = self.backup.backup_folders(folder)
            self.selected_folders.remove(folder)
            log_text.configure(state='normal')
            log_text.insert(END, "\t- " + os.path.split(folder)[-1] + ": " + response + '\n')
            log_text.configure(state='disabled')

        
        temp_files = self.selected_files[:]
        if len(temp_files) > 0:
            log_text.configure(state='normal')
            log_text.insert(END, "Files:\n" )
            log_text.configure(state='disabled')
        
        for file in temp_files:
            response = self.backup.backup_files(file)
            self.selected_files.remove(file)
            log_text.configure(state='normal')
            log_text.insert(END, "\t- " + os.path.split(file)[-1] + ": " + response + '\n')
            log_text.configure(state='disabled')

        log_text.configure(state='normal')
        log_text.insert(END, "\n\t\tCOMPLETED!\n")
        log_text.configure(state='disabled')

        self.backup_button['state'] = 'normal'
        self.remove_button['state'] = 'normal'

        self.folder_list.delete(0, 'end')
        self.file_list.delete(0, 'end')
        
        self.state = "Processing"

    def _on_closing(self):
        '''
        When the app is closed, ensures that all the threads are closed.
        '''
        for active_thread in threading.enumerate():
            if active_thread.name != "MainThread":
                try:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(active_thread), ctypes.py_object(SystemExit))
                except:
                    pass
            
        self.base.destroy()
    