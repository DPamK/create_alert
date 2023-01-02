import requests
import json



if __name__ == '__main__':

    url = "47.102.201.236:18080/alert"

    payload = json.dumps({
      "data": [
        {
          "originText": "聪明得小孩",
          "correctText": "聪明的小孩"
        }
      ],
      "way": {
        "style": "correct",
        "fliter": "Normal"
      }
    })
    headers = {
      'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)