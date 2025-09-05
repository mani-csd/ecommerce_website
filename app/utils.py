import os
from werkzeug.utils import secure_filename

ALLOWED = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

def save_image(file, upload_folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(upload_folder, filename)
        # If filename exists, append number to avoid overwrite
        base, ext = os.path.splitext(filename)
        i = 1
        while os.path.exists(path):
            filename = f"{base}_{i}{ext}"
            path = os.path.join(upload_folder, filename)
            i += 1
        file.save(path)
        return filename
    return None
