import os
import uuid
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_securely(file_obj, upload_folder):
    """Saves a file with a unique UUID name to prevent overwrites."""
    if not file_obj or file_obj.filename == '':
        return None
    
    if not allowed_file(file_obj.filename):
        raise ValueError("File type not allowed")

    # Generate unique name
    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # Create folder if not exists
    os.makedirs(upload_folder, exist_ok=True)
    
    save_path = os.path.join(upload_folder, unique_filename)
    file_obj.save(save_path)
    logger.info(f"File saved: {save_path}")
    return save_path

def validate_profile_data(form_data):
    """Ensures input data is valid and safe."""
    try:
        age = int(form_data.get('age', 0))
        if not (18 <= age <= 100):
            return None, "Возраст должен быть от 18 до 100 лет."
            
        gender = form_data.get('gender')
        if gender not in ['male', 'female']:
            return None, "Некорректный пол."

        smoking = form_data.get('smoking_status')
        if smoking not in ['smoker', 'non-smoker']:
            return None, "Некорректный статус курения."
            
        activity = form_data.get('activity_level')
        if activity not in ['sedentary', 'moderate', 'active']:
            return None, "Некорректный уровень активности."

        return {
            "age": age,
            "gender": gender,
            "smoking_status": smoking,
            "activity_level": activity
        }, None
    except ValueError:
        return None, "Ошибка формата данных."