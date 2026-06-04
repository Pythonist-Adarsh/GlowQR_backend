import requests

token = 'your_token_here'

# First login to get a token
login_res = requests.post('http://localhost:10000/api/auth/login', data={'username': 'Adarshtiwari2412@gmail.com', 'password': 'password'})
if login_res.status_code == 200:
    token = login_res.json()['access_token']
    print("Token fetched")
    
    res = requests.get('http://localhost:10000/api/analytics/summary', headers={'Authorization': f'Bearer {token}'})
    print(res.status_code)
    if res.status_code != 200:
        print(res.text)
else:
    print("Login failed", login_res.text)
