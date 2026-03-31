import requests

def test_api():
    try:
        # Peticion a la api sin auth para coger los datos crudos
        print("Pinging /api/hvac_data")
        res = requests.get("http://localhost:8000/api/hvac_data")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Items en array records: {len(data['records'])}")
            if data['records']:
                print(f"Record 0: {data['records'][0]}")
        else:
            print(res.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == '__main__':
    test_api()
