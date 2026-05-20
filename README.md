# Screenshot Tool

A small, efficient screenshot capture and management utility built in Python.

## Overview

Screenshot Tool lets you capture, save, and organize screenshots quickly from your desktop. It provides a simple CLI/GUI entry point and stores captures in the `screenshots/` directory.

## Features

- **Quick Capture**: Capture full screen or selected regions.
- **Organized Output**: Saves images to the `screenshots/` folder with timestamped filenames.
- **Configurable**: Basic settings stored in `settings.json` for easy customization.
- **Lightweight**: Minimal dependencies and fast startup.

## Requirements

- **Python**: 3.8+ recommended
- See [requirements.txt](requirements.txt) for exact dependencies.

## Installation

1. Clone or download the repository.
2. Create a virtual environment and activate it:

```
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
```

3. Install dependencies:

```
pip install -r requirements.txt
```

## Usage

- Run the main program:

```
python main.py
```

- The main entry point is [main.py](main.py). Captured screenshots are written to the [screenshots/](screenshots/) folder.

## Configuration

- Edit [settings.json](settings.json) to customize default behavior (output folder, image format, hotkeys).

## Development

- Run the app locally and modify `main.py` for feature changes.
- If you add dependencies, update `requirements.txt` accordingly.

## Contributing

- **Bug reports**: Open an issue describing the problem and environment.
- **Pull requests**: Fork the repo, create a feature branch, and submit a PR with a clear description.

## License

This project is distributed under the MIT License. Replace this section if a different license applies.

## Contact

For questions or feedback, open an issue or contact the maintainer.
