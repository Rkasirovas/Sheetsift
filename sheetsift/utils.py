import os

def cleanup_temp_files(*folders):
    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Nepavyko ištrinti failo: {file_path}. Klaida: {e}")