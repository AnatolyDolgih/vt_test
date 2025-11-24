import json
import requests


while True:
    print ("Input your text")
    text = input()
    re = requests.post(url="http://127.0.0.1:5000/console", json={"text": text})
    print(re.json()["text"])
            