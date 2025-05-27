import os
import threading
import time

def cleanup_temp_files(*folders):
    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Nepavyko ištrinti failo: {file_path}. Klaida: {e}")

def schedule_file_deletion(file_path, delay=60):
    def delete_file():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Failas {file_path} ištrintas po {delay} sekundžių.")
        except Exception as e:
            print(f"Nepavyko ištrinti failo {file_path}: {e}")

    t = threading.Thread(target=delete_file)
    t.daemon = True
    t.start()