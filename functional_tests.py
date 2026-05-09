from webdriver_settings import driver

browser = driver()
browser.get("http://localhost:8000")

assert "Congratulations!" in browser.title
print("OK")