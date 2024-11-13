# Library Book Search Automation

An automated tool built with Python and Selenium for searching and extracting book information. This tool provides a convenient interface for searching books by title, author, or ISBN, with capabilities to export results in multiple formats.

## Features

- Search books by title, author, or ISBN
- Export results to CSV, Excel, or JSON formats
- Configurable search parameters via JSON config file
- Search history tracking
- Detailed logging system
- Random delay implementation to prevent rate limiting
- Browser automation with headless mode support

## Requirements

```
python 3.x
selenium
webdriver-manager
pandas
openpyxl
```

## Installation

```bash
# Clone the repository
git clone [your-repo-url]

# Install required packages
pip install -r requirements.txt
```

## Usage

```bash
python book_searcher.py
```

The program will present an interactive menu with the following options:
1. Search by Title
2. Search by Author
3. Search by ISBN
4. Export Last Results
5. Exit

## Configuration

Default settings can be modified in `config.json`:
- Maximum search results
- Timeout duration
- Download path
- Browser options
- Wait times between requests

## License

[Your chosen license]

## Disclaimer

This tool is for educational purposes only. Please respect copyright laws and terms of service when using this tool.
