# 51ylipwptv@rfcdrive.com
# Test@123
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def post_job_learn4good(username, password, job_title, company_name, job_description, location, salary=None):
    driver = None
    try:
        driver = initialize_driver()
        login(driver, username, password)
        navigate_to_job_posting_page(driver)
        fill_job_details(driver, job_title, company_name, job_description, location, salary)
        submit_job_posting(driver)
        logger.info("Job posted successfully on Learn4Good!")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        if driver:
            time.sleep(5)  # Wait a bit before closing to see the result
            driver.quit()

def initialize_driver():
    return uc.Chrome()

def login(driver, username, password):
    driver.get("https://www.learn4good.com/jobs/site-login.htm")
    wait_and_fill(driver, By.NAME, "email", username)
    wait_and_fill(driver, By.NAME, "password", password)
    click_element(driver, By.XPATH, "//input[@type='submit' and @value='LOG IN']")
    WebDriverWait(driver, 10).until(EC.url_contains("employer"))

def navigate_to_job_posting_page(driver):
    driver.get("https://www.learn4good.com/jobs/index.php?controller=job&action=display_add")

def fill_job_details(driver, job_title, company_name, job_description, location, salary):
    wait_and_fill(driver, By.NAME, "job_title", job_title)
    wait_and_fill(driver, By.NAME, "company_name", company_name)
    wait_and_fill(driver, By.NAME, "job_description", job_description)
    wait_and_fill(driver, By.NAME, "job_city", location)
    if salary:
        wait_and_fill(driver, By.NAME, "job_salary", salary)

def submit_job_posting(driver):
    click_element(driver, By.XPATH, "//input[@type='submit' and @value='Submit Job']")
    WebDriverWait(driver, 10).until(EC.url_contains("job_posted"))

def wait_and_fill(driver, by, locator, text):
    element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((by, locator)))
    element.clear()
    element.send_keys(text)

def click_element(driver, by, locator):
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, locator)))
    element.click()

# Example usage
job_description = """
We are looking for a talented Software Engineer to join our dynamic team at Tech Corp. 

Required skills:
1) Proficiency in Python and JavaScript
2) Experience with web development frameworks (e.g., Django, React)
3) Strong understanding of database systems (SQL and NoSQL)
4) Familiarity with version control systems (Git)

Optional skills that are good to have:
1) Experience with cloud platforms (AWS, Azure, or GCP)
2) Knowledge of containerization technologies (Docker, Kubernetes)
3) Understanding of CI/CD pipelines

Benefits we provide:
1) Competitive salary and performance bonuses
2) Comprehensive health, dental, and vision insurance
3) 401(k) matching
4) Flexible work hours and remote work options
5) Professional development opportunities and conference attendance

Join us in building cutting-edge software solutions that make a difference!
"""

if __name__ == "__main__":
    post_job_learn4good("51ylipwptv@rfcdrive.com", "Test@123", "Software Engineer", "Tech Corp", job_description, "New York, NY", "$100,000 - $150,000")
