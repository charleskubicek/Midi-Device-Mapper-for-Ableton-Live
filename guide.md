
# Custom MIDI Controller for Ableton Live: A Step-by-Step Guide

This guide will show you how to create a custom MIDI controller setup for Ableton Live without writing any code! You'll use simple text files to tell Ableton how your MIDI controller's knobs, buttons, and sliders should control things like volume, pan, device parameters, and more.

## What You'll Need

*   **Ableton Live:** Version 10, 11, or 12 (the latest version is recommended).
*   **A MIDI Controller:** Any MIDI controller with knobs, buttons, or sliders.
*   **A Text Editor:** A plain text editor (like Notepad on Windows, TextEdit on Mac, or VS Code - *make sure to save files as plain text*).  *Do not* use a word processor like Microsoft Word. VS Code is highly recommended.
*   **Python 3:** This project uses Python, but you won't need to *write* any Python code.  You just need it installed. You can download it from [https://www.python.org/downloads/](https://www.python.org/downloads/). Make sure to check the box that says "Add Python to PATH" during installation.
*   **(Optional) VS Code:** Although optional, VS Code is highly recommended for editing the configuration files, as it provides useful features like syntax highlighting and error checking. You can download it from [https://code.visualstudio.com/](https://code.visualstudio.com/).

## Getting Started: Installation (Simplified)

1.  **Download the Project:**

    *   Download the latest release ZIP file from: [https://github.com/charleskubicek/Midi-Device-Mapper-for-Ableton-Live/releases/latest](https://github.com/charleskubicek/Midi-Device-Mapper-for-Ableton-Live/releases/latest)
    *   Extract (unzip) the downloaded file to a convenient location on your computer (e.g., your `Documents` folder). This will create a folder (likely named something like `Midi-Device-Mapper-for-Ableton-Live-X.Y.Z` where X.Y.Z is the version number).

2.  **Install Required Tools:**

    *   Open a terminal or command prompt. (On Windows, search for "cmd" or "PowerShell"; on Mac, search for "Terminal").
    *   Navigate to the extracted folder.  For example, if you extracted it to your `Documents` folder, you might type:

        ```bash
        cd Documents/Midi-Device-Mapper-for-Ableton-Live-X.Y.Z
        ```
        (Replace `X.Y.Z` with the actual version number, and adjust the path if you extracted it somewhere else).

    *   Run the following command to install the necessary Python packages:

        ```bash
        pip install -r requirements.txt
        ```

    *  *(If you get an error like "pip not found," make sure you have installed Python with Pip)*

    The `requirements.txt` file should exist, and contain:

    ```
    pydantic
    lark
    nestedtext
    autopep8
    prettytable
    ```

3. **Optional**: You may need to install `pywin32` on windows:

```
pip install pywin32
```

## Creating Your Custom Controller Setup

You'll find example `controller.yaml` and `mapping.yaml` files in the extracted folder.  You'll edit these to match your MIDI controller and desired mappings.

**Important:** These files use a special text format called **NestedText**. It's similar to YAML, but simpler. The important rules are:

*   **Indentation is crucial:** Use spaces (not tabs!) to indent lines. The number of spaces matters.
*   **Everything is text:** Don't worry about putting quotes around numbers or strings.

### 1. `controller.yaml`: Describing Your Controller

This file describes the physical layout of your MIDI controller.  Open it in your text editor.

**Example (and you'll likely need to modify this):**

```nestedtext
encoder-mode: absolute

light_colors:
  red: 1
  green: 5
  blue: 9
  amber: 17
  yellow: 21
  orange: 37
  off: 0

control_groups:
  - layout: row
    number: 1
    type: knob
    midi_channel: 1
    midi_type: CC
    midi_range: 21-28

  - layout: row
    number: 2
    type: knob
    midi_channel: 1
    midi_type: CC
    midi_range: 41-48

  - layout: row
    number: 3
    type: button
    midi_channel: 9
    midi_type: note
    midi_range: 36, 37, 38, 39, 40, 41, 42, 43
```

**Key things to change:**

*   **`midi_channel`**: Find out which MIDI channel your controller uses (check its documentation).
*   **`midi_range`**:  This *must* match the MIDI CC numbers (for knobs/sliders) or note numbers (for buttons) that your controller sends. Consult your controller's documentation.  Some controllers have configuration software to change these settings.
*   **`type`**:  Make sure this is `knob`, `button`, or `slider`, as appropriate.
*   **`layout`**:  If your controller isn't laid out in simple rows, you may need to use `row-part` and the `row_parts` setting (see the original guide for details).
*   **`number`**: This is the row (or column) number *on your controller*, starting from 1.
*  **`light_colors`**: If your controller has lights, you can change the color names and values here. Consult the controller manual for how it maps midi notes to colors.

### 2. `mapping.yaml`: Connecting Controls to Ableton

This file defines what each knob, button, etc., will control in Ableton.  Open it in your text editor.

**Example (you'll modify this):**

```nestedtext
controller: controller.yaml
ableton_dir: "/Applications/Ableton Live 12 Suite.app" # VERY IMPORTANT

mappings:
  - type: mixer
    track: selected
    mappings:
      volume: row-1:1
      pan: row-1:2

  - type: device
    track: selected
    device: selected
    mappings:
      encoders: row-1:1-8
      parameters: 1-8
      on-off: row-2:8
```

**Key things to change:**

*   **`ableton_dir`**:  *This is crucial.*  You *must* change this to the correct path to your Ableton Live application.
    *   **On Windows:** It will probably look something like `C:\ProgramData\Ableton\Live 11 Suite\Program` (but check, and adjust the version number).
    *   **On Mac:** It will probably look something like `/Applications/Ableton Live 12 Suite.app`
*   **`mappings`**:  This is where you define what each control does.  Use the format `row-column:index`. For example:
    *   `row-1:3` means the third control on the first row (as defined in your `controller.yaml`).
    *   `row-2:1-4` means the first *four* controls on the second row.
* **`track`**: For `mixer` and `device` mappings, you can use:
    * `selected`: The currently selected track in Ableton.
    * `master`: The master track.
    * a number: Refer to a track by its number
* **`device`**:
    * `selected`: refers to the selected device.
    * a number: refers to the device by its number.
    * text: refer to a device by its name.

**Refer to the "Mapping Types in Detail" section of the previous, longer user guide for all the options you can use within each `type` of mapping (mixer, device, transport, etc.).** That section is still completely valid. The examples provided are also valid.

## 4. Generating and Deploying <a name="generating-and-deploying"></a>

1.  **Open a terminal/command prompt.**

2.  **Navigate to the directory containing your `mapping.yaml` and `controller.yaml` files.**  This is the folder you extracted from the ZIP file.

3.  **Run the generator and deploy:**

    ```bash
    python ableton_control_surface_as_code/gen.py mapping.yaml
    ./deploy.sh
    ```

4.  **Restart Ableton Live.**

5.  **Configure MIDI Settings:**
    *   Open Ableton Live's Preferences.
    *   Go to the "Link MIDI" tab.
    *   Under "Control Surface," select an entry with the same name as your `mapping.yaml` file (e.g., "mapping").
    *   Set the "Input" and "Output" to your MIDI controller.

## 5. Live Reloading (Making Changes) <a name="live-reloading"></a>

You can quickly test changes *without* restarting Ableton:

1.  **Save** your changes to `mapping.yaml`, `controller.yaml`, or `functions.py`.
2.  **Run this command** in your terminal (from the project directory):

    ```bash
    python update.py reload
    ```

## 6. Custom Functions (`functions.py`) – Optional <a name="custom-functions"></a>

If you want to add custom Python code to control Ableton, create a file named `functions.py` in the *same directory* as your `mapping.yaml` and `controller.yaml` files.  Refer to the previous, longer user guide for details and examples.

## 7. Troubleshooting <a name="troubleshooting-new"></a>

*   **Script Not Found:**
    *   Make *absolutely sure* you set `ableton_dir` correctly in `mapping.yaml`.  This is the most common cause of problems.
    *   Make sure you ran `./deploy.sh` and restarted Ableton.

*   **Controls Not Working:**
    *   Double-check your `controller.yaml` and `mapping.yaml` for typos. The row/column numbers and MIDI values *must* be correct.
    *   Use `python update.py reload` to apply changes.
    *   Use `python update.py debug` to see extra logging messages in the terminal, which might help you find the problem.
    *   Check your MIDI controller's documentation!

*   **Configuration File Errors:**
    *   Make sure your files are valid NestedText.  Use the examples as a guide.
    *   Pay close attention to indentation (use spaces, not tabs).

* **`update.py` errors**
    *  Check you are using the correct port by running
       ```
       python update.py cs_dir
       ```

* **Ableton's Log file**

```
./bin/tail_logs.sh
```

