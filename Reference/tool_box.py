from utils.selenium_controller import SeleniumController
from langchain_core.tools import tool


class ToolBox():
    def __init__(self):
        self.selenium_controller = SeleniumController()
        self.account = "111502026"
        self.password = "Georgeshiue1107"

        @tool 
        def create_browser(user_id: str) -> str:
            """Create a new browser session."""
            result = self.selenium_controller.create_browser(user_id)
            return result

        @tool
        def screen_shot(user_id: str, file_path: str) -> str:
            """Take a screenshot of the current page and save it to the file path."""
            result = self.selenium_controller.screen_shot(user_id, file_path)
            return result

        @tool
        def navigate(user_id: str, url: str) -> str:
            """Navigate to the specified URL."""
            result = self.selenium_controller.navigate(user_id, url)
            return result

        @tool
        def get_html_content(user_id: str) -> str:
            """Get the HTML content of the current page."""
            result = self.selenium_controller.get_content(user_id)
            return result

        @tool
        def input_text_with_label(user_id: str, label_text: str, text: str, privacy: str = "None") -> str:
            """
            Inputs text into the input element specified by the text of the label for the given user_id.
            Replace the text argument with the external information when the privacy parameter is not "None".
            """
            if privacy == "Account":
                text = self.account
            if privacy == "Password":
                text = self.password
            result = self.selenium_controller.input_text_with_label(user_id, label_text, text, privacy)
            return result

        @tool
        def input_text_with_name(user_id: str, name: str, text: str, privacy: str = "None") -> str:
            """
            Inputs text into the input element specified by the text of the label for the given user_id.
            Replace the text argument with the external information when the privacy parameter is not "None".
            """
            if privacy == "Account":
                text = self.account
            if privacy == "Password":
                text = self.password
            result = self.selenium_controller.input_text_with_name(user_id, name, text, privacy)
            return result

        @tool
        def click_button_with_text(user_id: str, text: str) -> str:
            """Clicks the button specified by the Text for the given user_id."""
            result = self.selenium_controller.click_button_with_text(user_id, text)
            return result

        @tool
        def click_input_with_label(user_id: str, label_text: str) -> str:
            """
            Clicks the input specified by the text of the label for the given user_id.
            Use case: clicking the checkbox with label.
            """
            result = self.selenium_controller.click_input_with_label(user_id, label_text)
            return result

        @tool 
        def click_input_with_value(user_id: str, value: str) -> str:
            """Clicks the input specified by the Value for the given user_id."""
            result = self.selenium_controller.click_input_with_value(user_id, value)
            return result

        @tool
        def click_input_with_id(user_id: str, id: str) -> str:
            """
            Clicks the input specified by the ID for the given user_id.
            Use case: clicking the input box without label.
            """
            result = self.selenium_controller.click_input_with_id(user_id, id)
            return result

        @tool
        def select_dropdown_option(user_id: str, option_text: str) -> str:
            """Selects the dropdown option specified by its text for the given user_id."""
            result = self.selenium_controller.select_dropdown_option(user_id, option_text)
            return result

        @tool
        def click_span_with_aria_label(user_id: str, aria_label: str, index: str = "1") -> str:
            """
            Clicks the span specified by the Aria Label for the given user_id.
            Use case: clicking date inside the calendar.
            index: the index of the span element to click, set index value based on user's instruction such as "第{index}個".
            """
            result = self.selenium_controller.click_span_with_aria_label(user_id, aria_label, int(index))
            return result

        @tool
        def upload_file_with_id(user_id: str, id: str, file_path: str) -> str:
            """Uploads a file to the element specified by the ID for the given user_id."""
            self.selenium_controller.scroll_to_middle(user_id)
            result = self.selenium_controller.upload_file_with_id(user_id, id, file_path)
            return result

        @tool
        def save_pipeline_instruction(file_name: str) -> str:
            """Save the pipeline instruction as txt file."""
            file_path = "pipelines/" + file_name
            # with open(file_path, "w", encoding='utf-8') as file:
            #     file.write(pipeline_instructions)
            # return pipeline_instructions
            file_name = file_name.replace(".txt", "")
            return f"{file_name} pipeline saved successfully."

        @tool
        def pipeline_instruction_extractor(file_name: str) -> str:
            """Extract instructions from a pipeline given by its name."""
            with open("pipelines/" + file_name + ".txt", "r", encoding='utf-8') as file:
                instruction = file.read()
            return instruction
        
        self.tools = {
            'create_browser': create_browser,
            'screen_shot': screen_shot,
            'navigate': navigate,
            'input_text_with_label': input_text_with_label,
            'get_html_content': get_html_content,
            'input_text_with_name': input_text_with_name,
            'click_button_with_text': click_button_with_text,
            'click_input_with_label': click_input_with_label,
            'select_dropdown_option': select_dropdown_option,
            'click_input_with_id': click_input_with_id,
            'click_span_with_aria_label': click_span_with_aria_label,
            'upload_file_with_id': upload_file_with_id,
            'save_pipeline_instruction': save_pipeline_instruction,
            'pipeline_instruction_extractor': pipeline_instruction_extractor,
            'click_input_with_value': click_input_with_value
        }

    def __str__(self):
        return f"ToolBox with {len(self.tools)} tools"