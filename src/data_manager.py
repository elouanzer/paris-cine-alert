import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SheetManager:

    def __init__(self, sheet_name: str, credentials_file: str = "credentials.json"):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open(sheet_name).sheet1

    def get_users(self) -> list[dict]:
        """
        Get user data from the Google Sheet.
        
        Returns:
            user_data (dict): user data.
        """
        return self.sheet.get_all_records()