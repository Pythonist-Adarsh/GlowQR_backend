import requests

res = requests.delete('http://localhost:3000/api/admin-proxy/prospects/15')
print(res.status_code)
print(res.text)
