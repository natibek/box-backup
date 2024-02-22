from tkinter import filedialog, Tk, Menu, ttk, Toplevel
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
        self.base.geometry("600x400")

        self.v_scroll = ttk.Scrollbar(self.base, orient='vertical')
        self.v_scroll.pack(side = 'right', fill = 'y')
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
        print(threading.current_thread())

        @Request.application
        def app(request: Request) -> Response:
            print("STARTED", self.backup.authorized, threading.current_thread())
            
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
                    print("INVALID TOKENS", code, csrf, 2)

                    return Response("Authorization Denied", 200)
            except:
                self.authorization_status = "Completed"
                print("INVALID TOKENS", code, csrf, 3)

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
                print("Failed Authorization")
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
        # frm.bind("<Configure>", on_configure)
        frm.pack()
        
        menu_bar = Menu(frm)
        self.base.config(menu = menu_bar)

        ttk.Label(frm, text='Backup Folder:' , padding=10).pack()
        selected_backup_folder = ttk.Label(frm, text= self.backup.backup_folder.get().name, padding=10)
        selected_backup_folder.pack()
        menu_bar.add_command(label="Set Box Backup Folder", command = lambda sbf = selected_backup_folder: self.set_box_folder(sbf))

        ttk.Label(frm, text='Selected Folders to back up:', padding=10).pack()
        folder_frm = ttk.Frame(frm)
        folder_frm.pack()
        folder_frm.config(height=0, padding=5)
        menu_bar.add_command(label="Select Folders to Backup", command=lambda: self.select_folder(folder_frm))

        ttk.Label(frm, text='Selected Files to back up:', padding=10).pack()
        file_frm = ttk.Frame(frm)
        file_frm.pack()
        file_frm.config(height=0, padding=5)
        menu_bar.add_command(label="Select Files to Backup", command=lambda: self.select_files(file_frm))
        
        backup_button = ttk.Button(frm, text="Backup", padding=5)
        backup_button['command'] = lambda : self.call_backup(file_frm, folder_frm, backup_button) 

        backup_button.pack()
    
    def set_box_folder(self, selected_backup_folder):
        '''
        Creates an instance of the BoxNav object to open a dialog box for navigating box and selecting a new backup directory.
        '''
        if self.state != "Backing Up":
            self.box_nav = BoxNav(self.backup, self.base, selected_backup_folder)
            self.box_nav.display_folders()

    def call_backup(self,folder_frm: ttk.Frame, file_frm: ttk.Frame, backup_button: ttk.Button):
        '''
        If there are any files/folders selected for backup, starts the backup_thread and updates the state of the app.
        '''
        if self.selected_files or self.selected_folders:
            backup_button['state'] = 'disabled'
            self.state = 'Backing Up'
            backup_thread = threading.Thread(target=self.handle_backup, args=(file_frm, folder_frm, backup_button))
            backup_thread.start()
        

    def handle_backup(self, folder_frm: ttk.Frame, file_frm: ttk.Frame, backup_button: ttk.Button):
        '''
        Uses the backup instance of the Backup class to back up each selected folder and file. Keeps track of the logs from 
        backing up in the logs list and displays them in a dialog window when completed.
        '''
        logs = []
        
        temp = self.selected_folders[:]
        for folder in temp:
            response = self.backup.backup_folders(folder)
            self.selected_folders.remove(folder)
            logs.append(os.path.split(folder)[-1] + ": " + response)
        
        if len(logs) > 0:
            logs.append("________________")
        
        temp = self.selected_files[:]
        for file in temp:
            response = self.backup.backup_files(file)
            self.selected_files.remove(file)
            logs.append(os.path.split(file)[-1] + ": " + response)

        self.display_logs(logs)
        backup_button['state'] = 'normal'

        for widget in folder_frm.winfo_children():
            widget.destroy()
        for widget in file_frm.winfo_children():
            widget.destroy()
        
        file_frm.config(height=0, padding=5)
        folder_frm.config(height=0, padding=5)
        file_frm.update_idletasks()
        folder_frm.update_idletasks()
        self.state = "Processing"
    
    def display_logs(self, logs):
        '''
        Displays the logs from backing up
        '''
        if logs:
            log_dialog = Toplevel(self.base)
            log_dialog.geometry('400x300')
            log_dialog.title('Log')
            log_frm = ttk.Frame(log_dialog)
            log_frm.pack()
            for log in logs:
                ttk.Label(log_frm, text=log, padding=5).pack()

    def select_folder(self, folder_frm: ttk.Frame):
        '''
        Opens the windows dialog for selecting a folder and adds any selected folder to the selected_folders list.
        Displays each folder's name along with a button to remove it from the list of folders to be backedup.
        '''
        if self.state != "Backing Up":
            backup_folder = filedialog.askdirectory()
            
            def remove_folder(sub_frm: ttk.Frame, backup_folder: str):
                if self.state != 'Backing Up':
                    print(backup_folder, self.selected_folders)
                    sub_frm.destroy()
                    self.selected_folders.remove(backup_folder)

            if backup_folder:
                if backup_folder not in self.selected_folders:
                    self.selected_folders.append(backup_folder)
                    sub_frm = ttk.Frame(folder_frm)
                    sub_frm.pack()

                    ttk.Label(sub_frm, text=os.path.split(backup_folder)[1], padding = 5).pack(side="left")
                    ttk.Button(sub_frm, text="x", 
                            command = lambda cur_folder = backup_folder, cur_frm = sub_frm: remove_folder(cur_frm, cur_folder), 
                            width=2, padding = 2).pack(side="right")

    def select_files(self, file_frm: ttk.Frame):
        '''
        Opens the windows dialog for selecting multiple files and adds any selected files to the selected_files list.
        Displays each files's name along with a button to remove it from the list of files to be backedup.
        '''
        if self.state != "Backing Up":
            backup_files = filedialog.askopenfilenames()
            
            def remove_file(sub_frm: ttk.Frame, file: str):
                if self.state != 'Backing Up':
                    print(file)
                    sub_frm.destroy()
                    self.selected_files.remove(file)

            for file in backup_files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    sub_frm = ttk.Frame(file_frm)
                    sub_frm.pack()

                    ttk.Label(sub_frm, text=os.path.split(file)[1], padding=5).pack(side="left")    
                    ttk.Button(sub_frm, text="x", 
                            command= lambda cur_file= file, cur_frm = sub_frm: remove_file(cur_frm, cur_file), 
                            width=2, padding = 2).pack(side="right")

    def _on_closing(self):
        '''
        When the app is closed, ensures that all the threads are closed.
        '''
        for active_thread in threading.enumerate():
            if active_thread.name != "MainThread":
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(active_thread), ctypes.py_object(SystemExit))
            
        self.base.destroy()
    