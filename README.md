# PaperSearch

This repository provides a simple GUI tool to search for files by keywords and copy them to a new folder.

## Usage

Run the GUI script:

```bash
python file_search_gui.py
```

Choose a source directory and a CSV file that maps keywords to file names. Enter keywords separated by spaces or commas and click **Search** to list files whose keywords match.
Use your mouse or keyboard to select multiple entries from the result list. If you leave the selection empty, all results will be copied.
Specify a destination root directory and new folder name, then click **Copy Files** to copy the selected files to the new folder.

The CSV file should have the filename in the first column and its keywords in the second column (multiple keywords can be separated by commas or spaces).

