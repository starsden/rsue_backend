import requests

API_URL = "http://127.0.0.1:8000/api/reestr/search?barcode={barcode}"

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyZmM5NTJmZS0zNDg3LTQyNTktOGVkNC01ZDA2MDQ1OTE4YjMiLCJyb2xlIjoiRm91bmRlciIsImV4cCI6MTc2MjgwNDMwMH0.s_2ILjMbUeADee535hkN2RxQfUeVUb8TSffyn8q-unE"

def check_barcode(barcode: str):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    try:
        url = API_URL.format(barcode=barcode)
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        if data:
            print("Найдено в БД:")
            for item in data:
                name = item.get("name") or "—"
                article = item.get("article") or "—"
                print(f"- {name} | Артикул: {article}")
        else:
            print("Штрихкод не найден в базе данных.")

    except requests.exceptions.RequestException as e:
        print("Ошибка запроса:", e)
    except ValueError:
        print("Ошибка обработки ответа сервера.")

def main():
    print("Сканер штрихкодов готов. Отсканируйте товар или введите штрихкод:")
    while True:
        barcode = input("> ").strip()
        if barcode.lower() in ["exit", "quit"]:
            print("Выход...")
            break
        if not barcode:
            continue
        check_barcode(barcode)

if __name__ == "__main__":
    main()
