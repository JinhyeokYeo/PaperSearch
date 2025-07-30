import os
import shutil
import csv
import tkinter as tk
from tkinter import filedialog, messagebox


class FileSearchGUI:
    """GUI application to search for files by keywords and copy them."""

    def __init__(self, root):
        self.root = root
        self.root.title("File Search and Copy")

        # Source directory selection
        self.src_dir = tk.StringVar()
        tk.Label(root, text="Source Directory:").grid(row=0, column=0, sticky="w")
        self.src_entry = tk.Entry(root, textvariable=self.src_dir, width=40, state="readonly")
        self.src_entry.grid(row=0, column=1, padx=5)
        tk.Button(root, text="Browse", command=self.browse_src).grid(row=0, column=2, padx=5)

        # CSV file selection
        self.csv_file = tk.StringVar()
        tk.Label(root, text="CSV File:").grid(row=1, column=0, sticky="w")
        self.csv_entry = tk.Entry(root, textvariable=self.csv_file, width=40, state="readonly")
        self.csv_entry.grid(row=1, column=1, padx=5)
        tk.Button(root, text="Browse", command=self.browse_csv).grid(row=1, column=2, padx=5)

        # Keyword input
        tk.Label(root, text="Keywords (comma or space separated):").grid(row=2, column=0, columnspan=3, sticky="w", pady=(5, 0))
        self.keyword_entry = tk.Entry(root, width=50)
        self.keyword_entry.grid(row=3, column=0, columnspan=3, pady=2)

        tk.Button(root, text="Search", command=self.search).grid(row=4, column=0, columnspan=3, pady=5)

        # Listbox to show results
        tk.Label(root, text="Matched Files:").grid(row=5, column=0, columnspan=3, sticky="w")
        self.listbox = tk.Listbox(root, width=60, height=10, selectmode=tk.EXTENDED)
        self.listbox.grid(row=6, column=0, columnspan=3, pady=(0, 5))

        # Destination directory selection
        self.dest_root = tk.StringVar()
        tk.Label(root, text="Destination Root:").grid(row=7, column=0, sticky="w")
        self.dest_entry = tk.Entry(root, textvariable=self.dest_root, width=40, state="readonly")
        self.dest_entry.grid(row=7, column=1, padx=5)
        tk.Button(root, text="Browse", command=self.browse_dest).grid(row=7, column=2, padx=5)

        tk.Label(root, text="New Folder Name:").grid(row=8, column=0, sticky="w")
        self.new_folder_entry = tk.Entry(root, width=40)
        self.new_folder_entry.grid(row=8, column=1, padx=5, pady=2)

        tk.Button(root, text="Copy Files", command=self.copy_files).grid(row=9, column=0, columnspan=3, pady=5)

        self.matches = []

    def browse_src(self):
        directory = filedialog.askdirectory()
        if directory:
            self.src_dir.set(directory)

    def browse_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            self.csv_file.set(file_path)

    def browse_dest(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dest_root.set(directory)

    def search(self):
        src = self.src_dir.get()
        csv_path = self.csv_file.get()
        if not src or not os.path.isdir(src):
            messagebox.showerror("Error", "Select a valid source directory")
            return
        if not csv_path or not os.path.isfile(csv_path):
            messagebox.showerror("Error", "Select a valid CSV file")
            return
        keywords = [kw.lower() for kw in self.keyword_entry.get().replace(',', ' ').split()]
        if not keywords:
            messagebox.showerror("Error", "Enter at least one keyword")
            return

        filenames = set()
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header and ('keyword' in header[0].lower() or 'file' in header[0].lower() or 'keyword' in header[1].lower()):
                    pass
                else:
                    if header:
                        f.seek(0)
                    reader = csv.reader(f)
                for row in reader:
                    if len(row) < 2:
                        continue
                    file_name = row[0].strip()
                    kw_str = row[1]
                    kw_list = [k.strip().lower() for k in kw_str.replace(',', ' ').split()]
                    if any(kw in kw_list for kw in keywords):
                        filenames.add(file_name)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to read CSV: {exc}")
            return

        self.matches = []
        for root_dir, _, files in os.walk(src):
            for file in files:
                if file in filenames:
                    self.matches.append(os.path.join(root_dir, file))

        self.update_listbox()

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        for path in self.matches:
            self.listbox.insert(tk.END, path)
        if not self.matches:
            self.listbox.insert(tk.END, "No matches found")

    def copy_files(self):
        if not self.matches:
            messagebox.showinfo("Info", "No files to copy")
            return

        # Determine which files are selected in the listbox. If none are
        # selected, default to copying all matched files.
        selected_indices = self.listbox.curselection()
        if selected_indices:
            files_to_copy = [self.listbox.get(i) for i in selected_indices]
        else:
            files_to_copy = self.matches

        dest_root = self.dest_root.get()
        if not dest_root or not os.path.isdir(dest_root):
            messagebox.showerror("Error", "Select a valid destination root")
            return
        folder_name = self.new_folder_entry.get().strip()
        if not folder_name:
            messagebox.showerror("Error", "Enter a folder name")
            return
        dest_dir = os.path.join(dest_root, folder_name)
        os.makedirs(dest_dir, exist_ok=True)
        for file_path in files_to_copy:
            shutil.copy2(file_path, dest_dir)
        messagebox.showinfo("Success", f"Copied {len(files_to_copy)} files to {dest_dir}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileSearchGUI(root)
    root.mainloop()
