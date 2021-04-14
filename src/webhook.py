import requests
import json

webhook_url= 'https://webhook.site/cc20fa17-b9e8-42bc-a957-9d2396b68ac2'

data = { 'name': 'prueba', 
         'info': 'quiubole' }

r = requests.post(webhook_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
