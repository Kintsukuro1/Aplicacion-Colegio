import urllib.request
import json

url = 'http://127.0.0.1:8000/api/v1/auth/token/'
headers_opt = {'Origin': 'http://localhost:5175', 'Access-Control-Request-Method': 'POST'}
try:
    req = urllib.request.Request(url, headers=headers_opt, method='OPTIONS')
    with urllib.request.urlopen(req, timeout=5) as r:
        print('OPTIONS', r.status)
        print('ACAO:', r.getheader('Access-Control-Allow-Origin'))
        print('ACAM:', r.getheader('Access-Control-Allow-Methods'))
        print('ACAH:', r.getheader('Access-Control-Allow-Headers'))
except Exception as e:
    print('OPTIONS ERROR', e)

headers_post = {'Origin': 'http://localhost:5175', 'Content-Type': 'application/json'}
payload = {'email': 'alumno1@colegio.cl', 'password': 'Estud#2025*01!'}
try:
    data = json.dumps(payload).encode('utf-8')
    req2 = urllib.request.Request(url, data=data, headers=headers_post, method='POST')
    with urllib.request.urlopen(req2, timeout=5) as r2:
        body = r2.read().decode('utf-8')
        print('POST', r2.status)
        print('ACAO:', r2.getheader('Access-Control-Allow-Origin'))
        print('Body:', body)
except Exception as e:
    print('POST ERROR', e)
