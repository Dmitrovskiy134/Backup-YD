import requests
import json
import argparse
from tqdm import tqdm
from datetime import datetime
import time
from urllib.parse import quote


class YDConnector:
    """Класс для работы с API Яндекс.Диска."""
    
    base_url = 'https://cloud-api.yandex.net'

    def __init__(self, token):
        """Инициализация с OAuth-токеном."""
        self.headers = {'Authorization': f'OAuth {token}'}

    def create_folder(self, folder_name):
        """Создание папки на Яндекс.Диске."""
        params = {'path': folder_name}
        response = requests.put(
            f'{self.base_url}/v1/disk/resources',
            headers=self.headers,
            params=params
        )
        return response.status_code in [201, 409]  # 409 - папка уже существует

    def upload_from_url(self, file_url, file_path):
        """Загрузка файла на Яндекс.Диск по URL."""
        url = f"{self.base_url}/v1/disk/resources/upload"
        params = {
            "path": file_path,
            "url": file_url
        }
        
        try:
            response = requests.post(url, headers=self.headers, params=params)
            if response.status_code != 202:
                return None
                
            operation_id = response.json().get("href", "").split("operation_id=")[-1]
            return operation_id
            
        except Exception:
            return None

    def check_upload_status(self, operation_id):
        """Проверка статуса загрузки."""
        url = f"{self.base_url}/v1/disk/operations/{operation_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def get_file_info(self, file_path):
        """Получение информации о файле."""
        url = f"{self.base_url}/v1/disk/resources"
        params = {"path": file_path}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def check_token(self):
        """Проверка валидности токена."""
        url = f"{self.base_url}/v1/disk/"
        try:
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False


class CatImageAPI:
    """Класс для работы с API картинок кошек."""
    
    @staticmethod
    def get_cat_with_text(text):
        """Получение URL картинки кота с текстом."""
        try:
            encoded_text = quote(text)
            return f"https://cataas.com/cat/says/{encoded_text}"
        except Exception:
            return None


def main():
    """Основная функция программы."""
    parser = argparse.ArgumentParser(
        description="Загрузка картинок кошек на Яндекс.Диск"
    )
    parser.add_argument("--text", required=True, help="Текст для картинки")
    parser.add_argument("--token", required=True, help="OAuth-токен Яндекс.Диска")
    parser.add_argument("--group", required=True, help="Название группы (папки)")
    
    args = parser.parse_args()
    
    print("=== Загрузка картинки кота на Яндекс.Диск ===")
    print(f"Текст на картинке: {args.text}")
    print(f"Группа (папка): {args.group}")
    print("=" * 50)
    
    # Инициализация
    yandex = YDConnector(args.token)
    cat_api = CatImageAPI()
    
    # Проверяем токен
    print("Проверяем токен Яндекс.Диска...")
    if not yandex.check_token():
        print("ОШИБКА: Неверный токен Яндекс.Диска")
        return
    print("OK: Токен действителен")
    
    # Создаем папку
    print("Создаем папку на Яндекс.Диске...")
    if not yandex.create_folder(args.group):
        print("ОШИБКА: Не удалось создать папку, завершаем работу")
        return
    print("OK: Папка создана/существует на Яндекс.Диске")
    
    # Получаем URL картинки кота
    print("Получаем картинку кота с текстом...")
    cat_url = cat_api.get_cat_with_text(args.text)
    if not cat_url:
        print("ОШИБКА: Не удалось получить картинку кота, завершаем работу")
        return
    
    print(f"OK: Картинка получена: {cat_url}")
    
    # Формируем путь к файлу
    file_name = f"{args.text}.jpg"
    file_path = f"{args.group}/{file_name}"
    
    print(f"Имя файла на Яндекс.Диске: {file_name}")
    print(f"Полный путь: {file_path}")
    
    # Загружаем на Яндекс.Диск
    print("Запускаем загрузку на Яндекс.Диск...")
    operation_id = yandex.upload_from_url(cat_url, file_path)
    
    if not operation_id:
        print("ОШИБКА: Ошибка при запуске загрузки")
        return
    
    # Отслеживаем прогресс загрузки
    print("Отслеживаем прогресс загрузки...")
    with tqdm(total=100, desc="Загрузка файла", unit="%") as pbar:
        for _ in range(20):  # 20 проверок (40 секунд)
            status_info = yandex.check_upload_status(operation_id)
            
            if not status_info:
                time.sleep(2)
                continue
            
            status = status_info.get("status")
            
            if status == "success":
                pbar.update(100 - pbar.n)
                break
            elif status == "failed":
                pbar.set_description("Ошибка загрузки")
                print(f"ОШИБКА: Ошибка при загрузке: {status_info}")
                break
            
            progress = int(status_info.get("progress", 0) * 100)
            pbar.update(max(0, progress - pbar.n))
            time.sleep(2)
    
    # Проверяем результат загрузки
    file_info = yandex.get_file_info(file_path)
    
    if file_info:
        # Сохраняем информацию о загрузке
        backup_info = {
            "timestamp": datetime.now().isoformat(),
            "group_name": args.group,
            "text": args.text,
            "file_name": file_name,
            "file_size": file_info.get("size", 0),
            "file_path": file_info.get("path", ""),
            "yandex_disk_url": f"https://disk.yandex.ru/client/disk/{args.group}",
            "source_url": cat_url
        }
        
        # Сохраняем в JSON файл
        json_filename = f"backup_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        print("\n=== ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО! ===")
        print(f"Текст на картинке: {args.text}")
        print(f"Имя файла: {file_name}")
        print(f"Размер файла: {backup_info['file_size']} байт")
        print(f"Путь на Яндекс.Диске: {file_path}")
        print(f"Посмотреть на Яндекс.Диске: {backup_info['yandex_disk_url']}")
        print(f"Информация сохранена в файл: {json_filename}")
    else:
        print("\nОШИБКА: Не удалось загрузить файл на Яндекс.Диск")


if __name__ == "__main__":
    main()
