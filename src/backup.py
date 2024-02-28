from boxsdk import Client, OAuth2, folder, file
import hashlib, os

class Backup():
    '''
    Class to handle interactions with the boxapi to 
     - authenticate a client
     - upload/updates folders/files
    '''
    oauth2: OAuth2
    auth_url: str
    csrf_token: str


    def __init__(self):
        '''
        - Intilizes the backup file with the proper values for the client id, secret token, and base box backup folder id.
        - Creates OAuth2 object to generate the authorization url and associated csrf token.
        - Sets the redirect url to localhost
        '''
        with open('src/credential.txt', 'r') as credentials:
            CLIENT_ID = credentials.readline().strip()
            CLIENT_SECRET = credentials.readline().strip()
            self.BACKUPFOLDERID = credentials.readline().strip()
            REDIRECT_URL = credentials.readline().strip()
        
        self.oauth2 = OAuth2(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
            )
                
        self.auth_url, self.csrf_token = self.oauth2.get_authorization_url(REDIRECT_URL)
        # print(self.csrf_token,'inner')
        self.authorized = False


    def authenticate(self, code: str, csrf: str):
        '''
        Handles authentication with the code and csrf token from the oath_server thread.
        - Asserts that the csrf token from the authenication request matches the csrf token of the oauth instance.
        - Creates a client if the code and crsf tokens are matched.
        '''
        try:
            if not self.authorized:
                assert csrf == self.csrf_token
                access_token, refresh_token = self.oauth2.authenticate(code)
                self.client = Client(self.oauth2)
                self.backup_folder = self.client.folder(self.BACKUPFOLDERID)
                self.base_backup = self.client.folder(self.BACKUPFOLDERID)
                self.authorized = True
                return True
            return True
        except AssertionError:
            self.authorized = False
            return False

    def sha1_hash(self, file_path: str) -> str:
        '''
        Generates a sha1 hash of a file using the bytes of a file.
        '''
        sha1 = hashlib.sha1()
        
        with open(file_path, 'rb') as file:
            for byte_block in iter(lambda: file.read(4096), b''):
                sha1.update(byte_block)

        return sha1.hexdigest()

    def is_same_version(self, file_path: str, item: file.File) -> bool:
        '''
        Checks if two files are the same by comparing their sha1 hashes.
        '''
        file_sha1 = self.sha1_hash(file_path)
        return file_sha1 == item.sha1

    def file_exists(self, path: str):
        '''
        Recursively checks a file exists in box starting at the set backup directory by matching names
        '''
        if os.path.exists(path):
            file_name = os.path.split(path)[-1]
        else:
            return "File not found in local drive"
        
        def find_file(cur_item):
            if cur_item.get().type == 'file':
                if cur_item.get().name == file_name:
                    return cur_item
            elif cur_item.get().type == 'folder':
                for child_item in cur_item.get_items():
                    result = find_file(child_item)
                    if result:
                        return result
            return False        

        return find_file(self.backup_folder)

    def backup_files(self, path: str):
        '''
        Backs up files:
            1) If file exists with the same version, does nothing.
            2) If file exists with a different version, updates it.
            3) If file does not exist, uploads it to the box backup directory. 
        '''
        file = self.file_exists(path)
        if file == "file not found in local drive":
            return file
        elif file:
            if self.is_same_version(path, file):
                return("Already backed up with same version.")
            else:
                file.update_contents(path)
                return("Updated version.")
        else:
            self.backup_folder.upload(path)
            return("Backed up.")
        
    def folder_exists(self, path: str):
        '''
        Recursively checks a folder exists in box starting at the set backup directory by matching names
        '''
        if os.path.exists(path):
            dir_name = os.path.split(path)[-1]
        else:
            return "Folder not found in local drive"
        
        def find_folder(cur_item):
            if cur_item.get().name == dir_name:
                return cur_item
            
            for child_item in cur_item.get_items():
                if child_item.get().type == "folder":
                    result = find_folder(child_item)
                    if result:
                        return result
            return False        

        return find_folder(self.backup_folder)
    
    def recursive_folder_backup(self, box_folder: folder.Folder, cur_path: str):
        '''
        If the folder exists, recursively 
            1) Update all the contents of the local folder are found with different version online
            2) Upload all the contents of the local folder not found in the online version

        This is done in a BFS fashion to ensure the hierarchical structure of the local folder is kept.
        '''
        root, dirs, files = next(os.walk(cur_path))
    
        box_files = {item.get().name: item for item in box_folder.get_items() if item.get().type == "file"}
        
        for file in files:
            box_file = box_files.get(file, None)
            if box_file:
                if not self.is_same_version(os.path.join(root, file), box_file):
                    box_file.update_contents(os.path.join(root, file))
            else:
                box_folder.upload(os.path.join(root, file))

        sub_folders = {item.get().name: item for item in box_folder.get_items() if item.get().type == "folder"}
    
        for dir in dirs:

            sub_folder = sub_folders.get(dir, None)

            if sub_folder:
                self.recursive_folder_backup(sub_folder, os.path.join(root, dir))
            else:
                new_folder = box_folder.create_subfolder(dir)
                self.recursive_folder_backup(new_folder, os.path.join(root, dir))

    def new_folder_backup(self, box_folder: folder.Folder, cur_path: str):
        '''
        When a folder is not in the box backup directory, creates a new folder at the box backup directory and 
        recursively uploads all the contents of the local folder.
        '''
        root, dirs, files = next(os.walk(cur_path))
        new_folder = box_folder.create_subfolder(os.path.split(cur_path)[1])
        for file in files:
            new_folder.upload(os.path.join(root, file))

        for dir in dirs:
            self.new_folder_backup(new_folder, os.path.join(root, dir))


    def backup_folders(self, path: str):
        '''
        Checks if a folder exists in the box backup directory or any subfolders and chooses the appropriate upload method.
        '''
        folder = self.folder_exists(path)
        if folder == "Folder not found in local drive":
            return(folder)
        elif folder == False:
            self.new_folder_backup(self.backup_folder, path)
            return "New folder created"
        elif folder:
            self.recursive_folder_backup(folder, path)
            return "Existing folder updated"
        
