# DAEDALUS-Performance-Calculator
Performance calculator for Project1.1 


GUI for Calc v1.2.5

# Instructions
Download and run the GUI
1. Download both files
Download glider_gui.py and glider_performance.py from the file cards in this chat. You need both.

2. Put them in one folder
Save both in the same folder, for example C:\Downloads\

3. Install Python (skip if you already have it)

Download Python from python.org.
In the installer, tick Add Python to PATH before clicking Install.
To check it worked, open Command Prompt and run python --version.
4. Open Command Prompt in the folder
Open the folder in File Explorer, click the address bar, type cmd, and press Enter. A Command Prompt opens already pointing at that folder.

If you open Command Prompt yourself instead, use this, with the quotes and /d (needed because the folder is on another drive and its name has a space):

cd /d "C:\Downloads\"
5. Install the plotting library 

pip install matplotlib
6. Run it

python glider_gui.py
The calculator window opens.

7. Open and Test

Fill in every box. Set CL max to about 1.4, because an empty box gives an error.
Press Calculate or Enter.
Read the results on the left and the plot on the right.
If something goes wrong
“can’t open file ... glider_gui.py”: you’re in the wrong folder. Redo step 4.
“No module named matplotlib”: redo step 5.
“No module named glider_performance”: glider_performance.py isn’t in the same folder as glider_gui.py.
“‘python’ is not recognized”: Python isn’t on PATH. Reinstall it and tick Add Python to PATH.

