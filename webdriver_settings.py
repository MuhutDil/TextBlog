from selenium import webdriver

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

def driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(executable_path="/snap/bin/firefox.geckodriver")
    driver = webdriver.Firefox(options=options, service=service)
    return driver
