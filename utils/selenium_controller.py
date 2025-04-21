import docker
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

class SeleniumController:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            print(f"Error initializing Docker client: {e}")
            self.client = None
        self.port_list = []
        self.used_ports = set()
        self.browser_list = []

    def __del__(self):
        """
        Destructor to ensure all containers are stopped and removed.
        """
        try:
            print("Cleaning up all containers...")
            containers = self.client.containers.list()
            print(f"Found {len(containers)} containers.")
            for container in containers:
                if "selenium/standalone-firefox:latest" in container.image.tags:
                    container.stop()
                    container.remove()
                    print(f"Container {container.name} has been stopped and removed.")
            self.port_list.clear()
            self.used_ports.clear()
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def create_container(self, user_id):
        """
        Creates a container for the given user_id using selenium/standalone-firefox image.
        The port will be assigned from the range 10001 to 10100.
        """
        print(f"Creating container for user_id {user_id}...")
        # Find an available port
        available_ports = [port for port in range(10001, 10101) if port not in self.used_ports]
        if not available_ports:
            raise Exception("No available ports in the range 10001-10100.")
        
        port = random.choice(available_ports)
        self.used_ports.add(port)

        # Create the container
        container = self.client.containers.run(
            "selenium/standalone-firefox",
            ports={'4444/tcp': port},
            detach=True
        )
        print(f"Container {container.name} created on port {port}")
        # Store the user_id and port mapping
        self.port_list.append({"user_id": user_id, "port": port})
        print(f"Container created for user_id {user_id} on port {port}")
        return container

    def get_port_by_user_id(self, user_id):
        """
        Retrieves the port number assigned to the given user_id.
        """
        for record in self.port_list:
            if record["user_id"] == user_id:
                return record["port"]
        return None

    def stop_and_remove_container(self, user_id):
        """
        Stops and removes the container associated with the given user_id.
        """
        port = self.get_port_by_user_id(user_id)
        if port is None:
            print(f"No container found for user_id {user_id}")
            return

        # Find and stop the container using the port
        containers = self.client.containers.list()
        for container in containers:
            if container.attrs['NetworkSettings']['Ports']['4444/tcp'][0]['HostPort'] == str(port):
                container.stop()
                container.remove()
                self.used_ports.remove(port)
                self.port_list = [record for record in self.port_list if record["user_id"] != user_id]
                print(f"Container for user_id {user_id} on port {port} has been stopped and removed.")
                return

        print(f"No running container found for user_id {user_id}")

    def connect_to_container(self, user_id):
        """
        Connects to the Selenium container for the given user_id using Selenium WebDriver.
        """
        port = self.get_port_by_user_id(user_id)
        if port is None:
            raise Exception(f"No container found for user_id {user_id}")

        # Connect to the Selenium container
        browser = webdriver.Remote(
            command_executor=f'http://localhost:{port}/wd/hub',
            options=webdriver.FirefoxOptions()
        )
        print(f"Connected to Selenium container for user_id {user_id} on port {port}")
        return browser
    
    def create_browser(self, user_id):
        """
        Creates a browser instance for the given user_id.
        """
        self.create_container(user_id)
        # wait for the container to start
        time.sleep(5)
        browser = self.connect_to_container(user_id)
        self.browser_list.append({"user_id": user_id, "browser": browser})
        # return browser
        return f"Browser created for user_id {user_id}"
    
    def remove_browser(self, user_id):
        """
        Removes the browser instance associated with the given user_id.
        """
        self.stop_and_remove_container(user_id)
        self.browser_list = [record for record in self.browser_list if record["user_id"] != user_id]
        print(f"Browser for user_id {user_id} has been removed.")
    
    def get_browser_by_user_id(self, user_id):
        """
        Retrieves the browser instance associated with the given user_id.
        """
        for record in self.browser_list:
            if record["user_id"] == user_id:
                return record["browser"]
        return None

    def screen_shot(self, user_id, file_name):
        """
        Takes a screenshot of the browser window for the given user_id and saves it to the specified file path.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")
        
        file_path = "screenshots/" + file_name + ".png"
        browser.save_screenshot(file_path)
        print(f"Screenshot saved for user_id {user_id} at {file_path}")
        return f"Screenshot saved for user_id {user_id} at {file_path}"

    def scroll_to_middle(self, user_id):
        """
        Scrolls the page down to the middle for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        browser.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
        print(f"Scrolled to middle for user_id {user_id}")

    def scroll_to_bottom(self, user_id):
        """
        Scrolls the page down to bottom for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        print(f"Scrolled down for user_id {user_id}")

    def click_button_with_text(self, user_id, text):
        """
        Clicks the button specified by the Text for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            button = browser.find_element(By.XPATH, f"//button[text()='{text}']")
            button.click()
        except:
            print(f"Failed to click button with Text {text} for user_id {user_id}")
            return f"Failed to click button with Text {text} for user_id {user_id}"
        print(f"Clicked button with Text {text}  for user_id {user_id}")
        return f"Clicked button with Text {text}  for user_id {user_id}"

    def click_input_with_value(self, user_id, value):
        """
        Clicks the input specified by the Value for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            input = browser.find_element(By.XPATH, f"//input[@value='{value}']")
            input.click()
        except:
            print(f"Failed to click input with Value {value} for user_id {user_id}")
            return f"Failed to click input with Value {value} for user_id {user_id}"
        print(f"Clicked input with Value {value}  for user_id {user_id}")
        return f"Clicked input with Value {value}  for user_id {user_id}"

    def click_input_with_label(self, user_id, label_text):
        """
        Clicks the input specified by the text of the label for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            label = browser.find_element(By.XPATH, f"//label[text()='{label_text}']")
            for_attribute = label.get_attribute("for")
            if for_attribute:
                print("for attribute: ", for_attribute)
                input = browser.find_element(By.ID, for_attribute) # 使用 for 屬性值定位對應的 <input>
            else:
                input = label.find_element(By.TAG_NAME, "input") # 若沒有 for 屬性，查找 <label> 的子元素 <input>                
            input.click()
        except Exception as e:
            print("Exception: ", e)
            print(f"Failed to click input with Label {label_text} for user_id {user_id}")
            return f"Failed to click input with Label {label_text} for user_id {user_id}"
        print(f"Clicked input with Label {label_text}  for user_id {user_id}")
        return f"Clicked input with Label {label_text}  for user_id {user_id}"

    def click_input_with_id(self, user_id, id):
        """
        Clicks the input specified by the ID for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            input = browser.find_element(By.ID, id)
            input.click()
        except:
            print(f"Failed to click input with ID {id} for user_id {user_id}")
            return f"Failed to click input with ID {id} for user_id {user_id}"
        print(f"Clicked input with ID {id}  for user_id {user_id}")
        return f"Clicked input with ID {id}  for user_id {user_id}"

    def click_span_with_aria_label(self, user_id, aria_label, index=1):
        """
        Clicks the span specified by the Aria Label for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            spans = browser.find_elements(By.XPATH, f"//span[@aria-label='{aria_label}']")
            print("spans: ", len(spans))
            spans[index-1].click()
        except:
            print(f"Failed to click span with Aria Label {aria_label} for user_id {user_id}")
            return f"Failed to click span with Aria Label {aria_label} for user_id {user_id}"
        print(f"Clicked span with Aria Label {aria_label}  for user_id {user_id}")
        return f"Clicked span with Aria Label {aria_label}  for user_id {user_id}"

    def click_element(self, user_id, xpath):
        """
        Clicks the element specified by the XPath for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            element = browser.find_element(By.XPATH, xpath)
            element.click()
        except:
            print(f"Failed to click element with Xpath {xpath} for user_id {user_id}")
            return
        print(f"Clicked element with Xpath {xpath} for user_id {user_id}")

    def navigate_with_url(self, user_id, url):
        """
        Navigates the browser to the specified URL for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        browser.get(url)
        print(f"Browser for user_id {user_id} navigated to {url}")
        return f"Browser for user_id {user_id} navigated to {url}"

    def get_content(self, user_id):
        """
        Retrieves the content of the current page for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        content = browser.page_source
        print(f"Content retrieved for user_id {user_id}")
        return content
    
    def input_text_with_label(self, user_id, label_text, text, privacy = "None"):
        """
        Inputs text into the input element specified by the text of the label for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            label = browser.find_element(By.XPATH, f"//label[text()='{label_text}']")
            for_attribute = label.get_attribute("for")
            if for_attribute:
                print("for attribute: ", for_attribute)
                input = browser.find_element(By.ID, for_attribute) # 使用 for 屬性值定位對應的 <input>
            input.send_keys(text)
        except Exception as e:
            print("Exception: ", e)
            print(f"Failed to input text into input with Label {label_text} for user_id {user_id}")
            return f"Failed to input text into input with Label {label_text} for user_id {user_id}"
        if privacy == "None":
            print(f"Text input '{text}' for input with Label {label_text} for user_id {user_id}")
            return f"Text input '{text}' for input with Label {label_text} for user_id {user_id}"
        else:
            print(f"Text input '{privacy}' for input with Label {label_text} for user_id {user_id}")
            return f"Text input '{privacy}' for input with Label {label_text} for user_id {user_id}"

    def input_text_with_name(self, user_id, name, text, privacy = "None"):
        """
        Inputs text into the input element specified by the Name for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:    
            input = browser.find_element(By.NAME, name)
            input.send_keys(text)
        except:
            print(f"Failed to input text into input with Name {name} for user_id {user_id}")
            return f"Failed to input text into input with Name {name} for user_id {user_id}"
        
        if privacy == "None":
            print(f"Text input '{text}' for input with Name {name} for user_id {user_id}")
            return f"Text input '{text}' for input with Name {name} for user_id {user_id}"
        else:
            print(f"Text input '{privacy}' for input with Name {name} for user_id {user_id}")
            return f"Text input '{privacy}' for input with Name {name} for user_id {user_id}"

    def input_text(self, user_id, xpath, text):
        """
        Inputs text into the element specified by the XPath for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        element = browser.find_element(By.XPATH, xpath)
        element.send_keys(text)
        print(f"Text input '{text}' for element with XPath {xpath} for user_id {user_id}")

    def upload_file_with_id(self, user_id, id, file_path):
        """
        Uploads a file to the element specified by the ID for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        try:
            element = browser.find_element(By.ID, id)
            element.send_keys(file_path)
        except:
            print(f"Failed to upload file to element with ID {id} for user_id {user_id}")
            return f"Failed to upload file to element with ID {id} for user_id {user_id}"
        print(f"File uploaded to element with ID {id} for user_id {user_id}")
        return f"File uploaded to element with ID {id} for user_id {user_id}"

    # def solve_captcha(self, user_id):
    #     """
    #     Solves the Captcha for the given user_id using 2Captcha service.
    #     """
    #     browser = self.get_browser_by_user_id(user_id)
    #     if browser is None:
    #         raise Exception(f"No browser found for user_id {user_id}")
        
    #     element = browser.find_element(By.CLASS_NAME, "g-recaptcha")
    #     site_key = element.get_attribute("data-sitekey")
    #     print(f'Get Site key: {site_key}')

    #     current_url = browser.current_url
    #     print(f'Get Current URL: {current_url}')
        
    #     print("Solving Captcha...")
    #     two_captcha_api_key = "53eb2deb57f6d307bd1ee3ac6a4c822b" # 之後寫進 .env
    #     solver = TwoCaptcha(two_captcha_api_key)
    #     start_time = time.time()
    #     response = solver.solve_captcha(site_key=site_key, page_url=current_url)
    #     end_time = time.time()
    #     elapsed_time = end_time - start_time
    #     print(f"Successfully solved the Captcha. The solve code is {response}")
    #     print(f"Captcha solving took {elapsed_time:.2f} seconds")

    #     recaptcha_response_element = browser.find_element(By.ID, 'g-recaptcha-response')
    #     browser.execute_script(f'arguments[0].value = "{response}";', recaptcha_response_element)
    #     print("Captcha response successfully inserted")

    def select_dropdown_option(self, user_id, option_text):
        """
        Selects the dropdown option specified by its text for the given user_id.
        """
        browser = self.get_browser_by_user_id(user_id)
        if browser is None:
            raise Exception(f"No browser found for user_id {user_id}")

        xpath = "/html/body/div[4]/div/div[2]/div[2]/form/table/tbody/tr[3]/td/select"
        try:
            select_element = browser.find_element(By.XPATH, xpath)
            dropdown = Select(select_element)
            dropdown.select_by_visible_text(option_text)
        except Exception as e:
            print(f"Failed to select dropdown option: {e}")
            return f"Failed to select dropdown option: {e}"

        selected_option = dropdown.first_selected_option
        print(f"Selected dropdown option: '{selected_option.text}'")
        return f"(Selected dropdown option: '{selected_option.text}'"