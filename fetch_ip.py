import os
import requests

JSON_URL = " https://api.jsonbin.io/b/5f526b43993a2e110d3e53d6/4"

def main():
    r = requests.get(JSON_URL)
    content = r.json()
    ip_server = content["ip_server"]
    print(ip_server)
    os.environ["LOCAL_SERVER_IP_ADDRESS"] = ip_server
    print(os.environ["LOCAL_SERVER_IP_ADDRESS"])


if __name__ == '__main__':
    main()