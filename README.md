# 📸 SnapShot Pro

A modern and professional **Screenshot Tool Desktop Application** built with **Python**, **Tkinter**, and **PyAutoGUI**.  
SnapShot Pro allows users to capture full-screen screenshots, selected regions, and manage screenshot history through a clean and responsive graphical interface.

---

# 🚀 Features

## 📷 Screenshot Capture
- Full-screen screenshot capture
- Select custom screen region
- Window capture support
- Delay timer before capture
- Minimize app while capturing

## 🖼 Live Preview
- Real-time screenshot preview
- Responsive preview panel
- Auto-refresh on resize

## 📂 File Management
- Automatically saves screenshots
- Custom save location support
- Timestamp-based unique filenames
- Screenshot history panel
- Open and delete screenshots directly

## ⚡ Productivity Features
- Keyboard shortcuts support
- Clipboard copy support
- Auto-open screenshot after capture
- Screenshot counter
- Status notifications

## 🎨 Modern UI
- Dark mode and light mode
- Clean modern interface
- Responsive layout
- Custom styled buttons

## ⚙ Settings System
- Persistent settings using JSON
- Stores theme preferences
- Stores save location
- Stores capture count

---

# 🛠 Technologies Used

- Python
- Tkinter
- PyAutoGUI
- Pillow (PIL)
- Keyboard

---

# 📁 Project Structure

```bash
Screenshot-Tool/
│
├── main.py
├── settings.json
├── requirements.txt
├── screenshots/
└── README.md
```

---

# 📦 Installation

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/screenshot-tool.git
cd screenshot-tool
```

---

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# ▶ Run the Application

```bash
python main.py
```

---

# ⌨ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + Shift + S` | Full Screen Capture |
| `Ctrl + Shift + R` | Region Capture |

---

# ⚙ Configuration

The application uses a `settings.json` file to store user preferences.

Example:

```json
{
    "theme": "dark",
    "save_location": "screenshots",
    "delay": 0,
    "auto_open": true,
    "sound_enabled": true,
    "screenshot_count": 0,
    "minimize_on_capture": true
}
```

---

# 📚 Required Libraries

```txt
pyautogui
pillow
keyboard
```

---

# 🧠 Core Functionalities

## Screenshot Engine
Handles:
- Fullscreen capture
- Region capture
- File saving
- Clipboard copy

## Settings Manager
Handles:
- Load/save settings
- Theme persistence
- Save location storage

## Region Selector
Provides:
- Transparent overlay
- Drag-to-select functionality

## Styled UI Components
Includes:
- Custom buttons
- Hover effects
- Theme-based styling

---

# 📸 Screenshots

## Main Dashboard
- Live preview section
- Screenshot history
- Capture controls

## Dark & Light Mode
- Easy theme switching
- Professional appearance

---

# 🔥 Future Improvements

- Screen recording support
- Cloud upload integration
- OCR text extraction
- Annotation tools
- Multi-monitor support
- Built-in image editor

---

# 🐞 Troubleshooting

## PyAutoGUI Error

Install required libraries:

```bash
pip install pyautogui
```

---

## Keyboard Shortcut Not Working

Run the application as administrator on Windows.

---

# 👨‍💻 Author

Developed by **Abdur Rahman**

Computer & Communication Engineering Student  
Passionate about Technology, UI Design, and Software Development.

---

# 📄 License

This project is open-source and free to use for learning and educational purposes.

---

# ⭐ Support

If you like this project:

- Give it a ⭐ on GitHub
- Share with your friends
- Improve and customize it further

---

# 🎯 Final Output

A fully functional professional Screenshot Tool application with:
- Modern GUI
- Fast screenshot capture
- Live preview
- Screenshot management
- Keyboard shortcuts
- Theme support
- Persistent settings
- Beginner-friendly clean code
