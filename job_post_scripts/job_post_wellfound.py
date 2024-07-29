from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# Wellfound Job Posting Script
# Login credentials for Wellfound
email = "wapotar802@ikangou.com"
password = "Wg%8zL*jCbj7J-4"
login_url = "https://wellfound.com/login"
job_post_url = "https://wellfound.com/recruit/jobs/new"

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options)
    return driver

def login_to_wellfound(driver):
    driver.get(login_url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "user[email]")))
        driver.find_element(By.NAME, "user[email]").send_keys(email)
        driver.find_element(By.NAME, "user[password]").send_keys(password)
        driver.find_element(By.NAME, "user[password]").send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until(EC.url_changes(login_url))
        print("Logged in successfully!")
    except Exception as e:
        print("Failed to login.", str(e))
        driver.quit()

def post_job(driver, job_data):
    try:
        driver.get(job_post_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        driver.find_element(By.NAME, "job_title").send_keys(job_data['title'])
        driver.find_element(By.NAME, "job_description").send_keys(job_data['description'])
        driver.find_element(By.NAME, "company_name").send_keys(job_data['company'])
        driver.find_element(By.NAME, "location").send_keys(job_data['location'])
        driver.find_element(By.XPATH, "//button[contains(text(), 'Post Job')]").click()
        print("Job posted successfully!")
    except Exception as e:
        print("Failed to post job.", str(e))
    finally:
        driver.quit()

# Example job data
job_data = {
    'title': 'Software Engineer',
    'description': 'Develop and maintain software solutions.',
    'company': 'Tech Innovations Inc.',
    'location': 'San Francisco, CA'
}

# Execute functions
driver = get_driver()
login_to_wellfound(driver)
post_job(driver, job_data)
