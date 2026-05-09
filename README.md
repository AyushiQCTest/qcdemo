# QuantCopierTelegram Demo

This project generates and animates a **Multibrot set** fractal using Python and Matplotlib. It includes scripts to package the application as a binary sidecar for a Tauri application.

## 🚀 Getting Started

### Prerequisites

Ensure you have Python 3.x installed.

### Installation

1.  **Clone the repository** (if you haven't already).
2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 🎥 Running the Animation

To see the fractal animation:

```bash
python QuantCopierTelegram.py
```

This will open a Matplotlib window showing a dynamic visualization of the Multibrot set, evolving the exponent over time.

## 🛠 Building the Sidecar

This project is designed to be bundled as a sidecar binary for a Tauri application (`QuantCopierTelegramUI`).

### Files Overview

-   **`QuantCopierTelegram.py`**: The main Python script containing the fractal logic and animation.
-   **`QuantCopierTelegram.spec`**: The PyInstaller specification file defining how the application is packaged (e.g., hidden imports, data files).
-   **`gen_qc_sidecar.sh`**: A helper script to automate the build and copy process.

### Using the Build Script

The `gen_qc_sidecar.sh` script performs the following steps:
1.  Cleans up previous build artifacts (`build/`, `dist/`).
2.  Runs **PyInstaller** using `QuantCopierTelegram.spec`.
3.  Detects the current system's **Rust target triple** (e.g., `x86_64-apple-darwin`).
4.  Copies the generated binary to the Tauri project's sidecar directory: `../QuantCopierTelegramUI/src-tauri/binaries/`.
5.  Renames the binary to include the target triple, which is required for Tauri sidecars (e.g., `QuantCopierTelegram-x86_64-apple-darwin.exe`).

**To run the build:**

```bash
./gen_qc_sidecar.sh
```

> **Note:** Ensure you have `pyinstaller` installed (`pip install pyinstaller`) and `rustc` available in your path (for triple detection).
