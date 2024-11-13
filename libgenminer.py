import logging
import time
import random
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

@dataclass
class BookData:
    title: str
    author: str
    year: str
    format: str
    size: str
    language: str
    pages: str
    publisher: str
    isbn: str = ""
    download_link: str = ""

class ConfigManager:
    DEFAULT_CONFIG = {
        "max_results": 20,
        "timeout": 10,
        "download_path": "downloads",
        "search_history_file": "search_history.json",
        "max_retries": 3,
        "wait_time": (1, 3),
        "browser_options": {
            "headless": False,
            "disable_images": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        try:
            with open(self.config_file, 'r') as f:
                return {**self.DEFAULT_CONFIG, **json.load(f)}
        except FileNotFoundError:
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
            
    def _save_config(self, config: Dict) -> None:
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
            
    def get(self, key: str) -> any:
        return self.config.get(key)

class BookSearcher:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.logger = self._setup_logger()
        self.driver = None
        self.wait = None
        self._setup_directories()
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('BookSearcher')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            fh = logging.FileHandler('book_searcher.log')
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            
        return logger
        
    def _setup_directories(self) -> None:
        Path(self.config.get("download_path")).mkdir(parents=True, exist_ok=True)
        
    def _initialize_driver(self) -> None:
        options = Options()
        browser_options = self.config.get("browser_options")
        
        if browser_options["headless"]:
            options.add_argument('--headless')
        if browser_options["disable_images"]:
            options.add_argument('--blink-settings=imagesEnabled=false')
        
        options.add_argument(f'user-agent={browser_options["user_agent"]}')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, self.config.get("timeout"))
        
    def _random_delay(self) -> None:
        min_time, max_time = self.config.get("wait_time")
        time.sleep(random.uniform(min_time, max_time))
        
    def search_books(self, search_term: str, search_type: str = "title") -> pd.DataFrame:
        try:
            if not self.driver:
                self._initialize_driver()
                
            self.driver.get("https://libgen.is/")
            self._random_delay()
            
            search_input = self.wait.until(EC.presence_of_element_located((By.NAME, "req")))
            search_input.clear()
            search_input.send_keys(search_term)
            
            search_type_select = self.driver.find_element(By.NAME, "column")
            for option in search_type_select.find_elements(By.TAG_NAME, "option"):
                if search_type.lower() in option.text.lower():
                    option.click()
                    break
                    
            search_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='submit']")))
            search_button.click()
            self._random_delay()
            
            books = self._extract_book_data()
            self._save_search_history(search_term, len(books))
            
            return self._create_dataframe(books)
            
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            raise
            
    def _extract_book_data(self) -> List[BookData]:
        books = []
        try:
            table = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "c")))
            rows = table.find_elements(By.TAG_NAME, "tr")[1:self.config.get("max_results") + 1]
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 9:
                    book = BookData(
                        title=cols[2].text.strip(),
                        author=cols[1].text.strip(),
                        year=cols[4].text.strip(),
                        format=cols[8].text.strip(),
                        size=cols[7].text.strip(),
                        language=cols[6].text.strip(),
                        pages=cols[5].text.strip(),
                        publisher=cols[3].text.strip(),
                        isbn=cols[9].text.strip() if len(cols) > 9 else "",
                        download_link=cols[2].find_element(By.TAG_NAME, "a").get_attribute("href")
                    )
                    books.append(book)
                    
        except Exception as e:
            self.logger.error(f"Data extraction error: {str(e)}")
            
        return books
        
    def _create_dataframe(self, books: List[BookData]) -> pd.DataFrame:
        return pd.DataFrame([vars(book) for book in books])
        
    def _save_search_history(self, search_term: str, results_count: int) -> None:
        history_file = self.config.get("search_history_file")
        try:
            if Path(history_file).exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
                
            history.append({
                "timestamp": datetime.now().isoformat(),
                "search_term": search_term,
                "results_count": results_count
            })
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving search history: {str(e)}")
            
    def export_results(self, df: pd.DataFrame, format: str = "csv") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_results_{timestamp}.{format}"
        
        try:
            if format == "csv":
                df.to_csv(filename, index=False)
            elif format == "excel":
                df.to_excel(filename, index=False)
            elif format == "json":
                df.to_json(filename, orient="records", indent=4)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
            return filename
            
        except Exception as e:
            self.logger.error(f"Export error: {str(e)}")
            raise
            
    def close(self) -> None:
        if self.driver:
            self.driver.quit()

def main():
    config_manager = ConfigManager()
    searcher = BookSearcher(config_manager)
    
    try:
        while True:
            print("\n=== Book Search Tool ===")
            print("1. Search by Title")
            print("2. Search by Author")
            print("3. Search by ISBN")
            print("4. Export Last Results")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == "5":
                break
                
            if choice in ["1", "2", "3"]:
                search_term = input("Enter search term: ")
                search_type = {"1": "title", "2": "author", "3": "isbn"}[choice]
                
                print("\nSearching... Please wait...\n")
                results = searcher.search_books(search_term, search_type)
                
                if not results.empty:
                    pd.set_option('display.max_columns', None)
                    pd.set_option('display.width', None)
                    print("\nSearch Results:")
                    print(results[['title', 'author', 'year', 'format', 'size']].to_string(index=False))
                    
                    export = input("\nWould you like to export results? (y/n): ")
                    if export.lower() == 'y':
                        format_choice = input("Enter export format (csv/excel/json): ")
                        filename = searcher.export_results(results, format_choice)
                        print(f"Results exported to {filename}")
                else:
                    print("No results found.")
                    
            elif choice == "4":
                if 'results' in locals():
                    format_choice = input("Enter export format (csv/excel/json): ")
                    filename = searcher.export_results(results, format_choice)
                    print(f"Results exported to {filename}")
                else:
                    print("No results available to export.")
                    
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        searcher.close()

if __name__ == "__main__":
    main()
