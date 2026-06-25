import requests

payload = { 'api_key': '37afb5a81e03dbb870776009f6c3d479', 'url': 'https://www.irishjobs.ie/jobs' }
r = requests.get('https://api.scraperapi.com/', params=payload)

with open("raw_html.html","w",encoding="utf-8") as f:
    f.write(r.text)