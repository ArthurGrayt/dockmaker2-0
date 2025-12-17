import os
import shutil
import vercel_blob
import requests

class StorageInterface:
    def save(self, file_storage, folder, filename):
        raise NotImplementedError
    
    def list_files(self, folder):
        raise NotImplementedError
    
    def get_file_url(self, filename, folder):
        raise NotImplementedError
        
    def download_to_path(self, filename, folder, local_path):
        raise NotImplementedError
        
    def upload_from_path(self, local_path, folder, filename):
        raise NotImplementedError

class LocalStorage(StorageInterface):
    def __init__(self, base_path):
        self.base_path = base_path
    
    def _get_path(self, folder, filename=""):
        return os.path.join(self.base_path, folder, filename)

    def save(self, file_storage, folder, filename):
        target = self._get_path(folder, filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        file_storage.save(target)
        return filename

    def list_files(self, folder):
        target = self._get_path(folder)
        if not os.path.exists(target):
            return []
        return os.listdir(target)

    def get_file_url(self, filename, folder):
        # Local files are served via a specific route or static, 
        # but in this app architecture, we usually download via /api/download
        # We'll return just the filename as the identifier
        return filename
        
    def download_to_path(self, filename, folder, local_path):
        source = self._get_path(folder, filename)
        if not os.path.exists(source):
            raise FileNotFoundError(f"File {filename} not found in {folder}")
        shutil.copy(source, local_path)
        
    def upload_from_path(self, local_path, folder, filename):
        target = self._get_path(folder, filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy(local_path, target)
        return filename

class BlobStorage(StorageInterface):
    def save(self, file_storage, folder, filename):
        # vercel_blob.put returns { url: str, ... }
        # content must be bytes or file-like
        # We add folder as prefix: "folder/filename"
        path = f"{folder}/{filename}"
        # file_storage from flask is file-like
        resp = vercel_blob.put(path, file_storage.read(), options={'access': 'public'})
        # Reset stream just in case?
        file_storage.seek(0)
        return resp['url']

    def list_files(self, folder):
        # vercel_blob.list(options={'prefix': folder})
        resp = vercel_blob.list(options={'prefix': folder + '/'})
        # Extract filenames from blobs. 
        # Blob pathname is "folder/filename". We want just "filename".
        files = []
        for blob in resp.get('blobs', []):
            name = blob['pathname'].split('/')[-1]
            if name: # filter empty
                files.append(name)
        return files

    def get_file_url(self, filename, folder):
        # If we have the full URL stored, return it? 
        # Since we don't store a DB, we reconstruct or find it.
        # But we can just construct valid blob URL or find it in list.
        # For simplicity, we just return the 'filename' to the frontend, 
        # and when processing, we look it up.
        # Ideally, we should return the Public URL.
        # But let's check 'list' again to find the URL? Expensive.
        # Standard approach: The filename IS the identifier.
        # The URL is needed for download? 
        return filename 

    def download_to_path(self, filename, folder, local_path):
        # 1. Find the URL (or construct it if predictable? Blob URLs are random-ish)
        # We must list to find the URL for the given filename
        resp = vercel_blob.list(options={'prefix': f"{folder}/{filename}", 'limit': 1})
        blobs = resp.get('blobs', [])
        if not blobs:
            raise FileNotFoundError(f"File {filename} not found in blob {folder}")
        
        url = blobs[0]['url']
        
        # 2. Download via requests
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        else:
            raise Exception(f"Failed to download blob: {r.status_code}")

    def upload_from_path(self, local_path, folder, filename):
        path = f"{folder}/{filename}"
        with open(local_path, 'rb') as f:
            resp = vercel_blob.put(path, f.read(), options={'access': 'public'})
        return resp['url']

def get_storage():
    # If BLOB_READ_WRITE_TOKEN is present, use Blob
    if os.environ.get('BLOB_READ_WRITE_TOKEN'):
        return BlobStorage()
    
    # Fallback to Local
    base_dir = os.path.abspath('')
    # Handle Vercel without Blob (the /tmp case) purely for temp storage?
    # No, we want persistence.
    # If user didn't set token, we default to local 
    # (which fails on Vercel unless patched to /tmp, but we want Persistence now).
    import tempfile
    if os.environ.get('VERCEL'):
         # If on vercel but no token, we revert to /tmp specific behavior 
         # (which we know is non-persistent) or just use /tmp
         return LocalStorage(tempfile.gettempdir())
         
    return LocalStorage(base_dir)
