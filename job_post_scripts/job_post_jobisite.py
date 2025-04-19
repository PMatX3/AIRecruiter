from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
LOGIN_URL = "https://www.jobisite.com/employeeLoginPage.htm"
POST_JOB_URL = "https://www.jobisite.com/serviceJobPosting.htm?pFlag=normal"

# Credentials and job details
username = "test"
password = "Test@123"
job_details = {
    "title": "Example Job Title",
    "description": "Example Job Description",
    "location": "Example Location",
    "skills": "Example Skills"
}

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--disable-gpu")  # Applicable for windows os and graphics cards
    options.add_argument("--remote-debugging-port=9222")  # This is optional
    driver = webdriver.Chrome(options=options)
    return driver

# Login using Selenium
def login():
    driver = get_driver()
    driver.get(LOGIN_URL)
    try:
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "userName"))
        )
        password_input = driver.find_element(By.NAME, "password")
        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        return driver
    except:
        driver.quit()
        return None

# Post a job using Selenium
def post_job(driver):
    try:
        driver.get(POST_JOB_URL)
        # Wait for the page to be fully loaded
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # Using ID instead of NAME to locate the title input
        title_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "title"))
        )
        skills = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.NAME, "skill1"))
        )
        description_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "discription"))
        )
        location_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.NAME, "country"))
        )
        title_input.send_keys(job_details["title"])
        description_input.send_keys(job_details["description"])
        location_input.send_keys(job_details["location"])
        skills.send_keys(job_details["skills"])
        
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[text()='Submit']"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", submit_button)
        submit_button.click()
        print("Job posted successfully!")
    except Exception as e:
        import traceback
        print("Failed to post job.", str(e))
        print(traceback.format_exc())
    finally:
        driver.quit()

# Execute
driver = login()
if driver:
    print("Logged in successfully!")
    post_job(driver)
else:
    print("Login failed.")