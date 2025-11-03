📄 README — DOC to PDF Converter Tool

🧩 Overview
This tool converts Microsoft Word `.docx` files into high-quality `.pdf` documents using Python.
It’s designed for quick, offline conversion with minimal setup and no paid software required.

⚙️ Dependencies
Make sure the following Python libraries are installed before running the script:

    python-docx
    reportlab
    pypandoc

You can install all of them at once using:
    pip install python-docx reportlab pypandoc

🖥️ System Requirements
- Python version: 3.8 or higher
- Operating Systems:
  - ✅ Windows 10 / 11
  - ✅ macOS
  - ✅ Linux (Ubuntu / Fedora tested)

🚀 How to Use

🪟 Windows Users
1. Install Python from https://python.org and ensure you check “Add Python to PATH” during setup.
2. Download or copy the converter script (doc_to_pdf.py) into any folder.
3. Open Command Prompt in that folder.
4. Run the command:
       python doc_to_pdf.py input.docx output.pdf
5. Your converted PDF will appear in the same directory.

🍏 macOS / 🐧 Linux Users
1. Make sure Python is installed (usually preinstalled on macOS/Linux).
2. Open a terminal in the script’s directory.
3. Run:
       python3 doc_to_pdf.py input.docx output.pdf
4. The new PDF file will be created in the same folder.

🧠 Notes & Tips
- If you get a “ModuleNotFoundError”, reinstall the missing library using `pip install <library_name>`.
- You can drag and drop your `.docx` file into the terminal to auto-fill its path.
- Works offline — no internet connection required after setup.
- Ensure your `.docx` file is not corrupted or locked (close Word before converting).

📞 Support
If you face any issues:
- Check that Python and all dependencies are installed properly.
- Verify that the file path has no spaces or special characters.
- You can re-install dependencies using:
       pip install --upgrade --force-reinstall python-docx reportlab pypandoc
