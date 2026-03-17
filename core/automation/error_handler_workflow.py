
import re
import time
from playwright.sync_api import Page, expect
import re
from playwright.sync_api import Page, expect
from core.automation.login_workflow import LoginWorkflow


class ErrorHandlerWorkflow:
    def __init__(self, gui, delay):
        self.gui = gui
        self.delay = delay

    def _logout(self, page: Page):
        """
        Handles errors by logging out and preparing for a restart with the next fiscal note.
        - Clicks on the user menu to open the dropdown.
        - Clicks on 'Sair' to log out.
        - Waits for the session to be finalized and the login page to load.
        """
        try:
            self.gui.log("An error occurred. Initiating logout and restart procedure.", level='warning')
            
            # Open user menu dropdown
            dropdown_selector = 'i.fas.fa-chevron-down.chevronicon'
            self.gui.log("Opening user menu...")
            page.locator(dropdown_selector).click()
            page.wait_for_timeout(1000)

            # Click on 'Sair' to logout
            logout_selector = 'p.regular-small-text:has-text("Sair")'
            self.gui.log("Clicking 'Sair' to log out...")
            page.locator(logout_selector).click()

            # Wait for the login page to be rendered by checking for the username field
            self.gui.log("Waiting for logout to complete and login page to appear.")
            expect(page.locator('input[name="usuario"]')).to_be_visible(timeout=60000)
            self.gui.log("Logout successful. Ready to restart.", level='success')

        except Exception as e:
            self.gui.log(f"FATAL: Could not execute the logout and restart procedure. Error: {e}", level='error')
            raise

    def handle_recovery(self, page: Page, login_workflow: LoginWorkflow, login_settings: dict):
        self.gui.log("Starting error recovery process...", level='info')
        self._logout(page)
        
        self.gui.log("Attempting to log back in...", level='info')
        login_workflow.execute(page, login_settings)
        self.gui.log("Login re-established successfully.", level='success')
