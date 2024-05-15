# COMP639S1_Group_AX Home

## Web element templates are all using [Bootstrap 5.3](https://getbootstrap.com/docs/5.3/getting-started/introduction/)

https://getbootstrap.com/docs/5.3/getting-started/introduction/

## Setup Flask on Windows System using VS Code

Flask is a powerful web framework for Python that allows developers to build scalable and flexible web applications. While setting up Flask on Linux or macOS can be relatively straightforward, the process can be a bit more complex on Windows. In this guide, we’ll walk you through the steps to set up Flask on Windows 10 using VS Code.

### Step 1: Install Python

Before installing Flask, we need to install Python on our Windows machine. Go to the official Python website and download the latest version of Python for Windows.

Once the download is complete, run the installer and follow the instructions to install Python on your system. During the installation process, make sure to select the option to add Python to your system path.

### Step 2: Install VS Code

Next, we’ll need to install Visual Studio Code (VS Code) on our system. Go to the official VS Code website and download the latest version of VS Code for Windows.

Once the download is complete, run the installer and follow the instructions to install VS Code on your system.

### Step 3: Create a Virtual Environment

After installing Python and VS Code, we’ll need to create a virtual environment for our Flask project. A virtual environment is a self-contained environment that allows us to install Python packages without affecting the global Python installation on our system.

To create a virtual environment, open a new terminal window in VS Code and navigate to the root directory of your project. Then, run the following command to create a new virtual environment:
** python -m venv venv **
This command will create a new virtual environment named ‘venv’ in the root directory of your project.

### Step 4: Activate the Virtual Environment

After creating the virtual environment, we need to activate it. To activate the virtual environment, run the following command in the terminal:
venv\Scripts\activate
This command will activate the virtual environment, and you’ll see the name of your virtual environment in the terminal prompt.

### Step 5: Install Flask

With the virtual environment activated, we can now install Flask using pip, the package manager for Python. To install Flask, run the following command in the terminal:
pip install flask
This command will download and install Flask and all its dependencies in your virtual environment.

### Step 6: Create a Flask Application

Now that we have Flask installed, we can create a new Flask application. Create a new Python file named app.py in the root directory of your project and add the following code:
from flask import Flask

app = Flask(\_\_name\_\_)

@app.route('/')
def index():
return 'Hello, World!'
This code will create a new Flask application with a single route that returns the string ‘Hello, World!’ when the root URL is accessed.

### Step 7: Run the Flask Application

With the Flask application created, we can now run it using the following command:
flask run
This command will start the Flask development server, and you’ll be able to access your application by navigating to http://localhost:5000/ in your web browser.

### Step 8: Debugging with VS Code

Debugging is an essential part of any software development process, and VS Code makes it easy to debug Flask applications.

Open your Flask project in VS Code.

Make sure you have the Python extension installed in VS Code. If not, you can install it from the VS Code Marketplace.

In the VS Code editor, click on the "Run and Debug" icon on the left-hand side panel, or press Ctrl + Shift + D on your keyboard.

This will open the "Run and Debug" panel in VS Code. Click on the "create a launch.json file" link to create a new launch configuration for your Flask application.

In the "Select Environment" dropdown, select "Python". This will create a new launch.json file in the .vscode folder of your project.

Modify the configuration settings in the launch.json file as follows:
{
"version": "0.2.0",
"configurations": [
{
"name": "Python: Flask",
"type": "python",
"request": "launch",
"module": "flask",
"env": {
"FLASK_APP": "app.py",
"FLASK_ENV": "development",
"FLASK_DEBUG": "1"
},
"args": [
"run",
"--no-debugger",
"--no-reload"
],
"jinja": true
}
]
}
Here, the "FLASK_APP": "app.py" setting should match the name of the main Flask application file in your project. The "FLASK_ENV": "development" and "FLASK_DEBUG": "1" settings enable Flask's development mode and debugger, respectively.

Place a breakpoint in your Flask application code where you want to start debugging.

Click on the "Start Debugging" button in the "Run and Debug" panel, or press F5 on your keyboard.

This will start the Flask server with the debugger attached. When the breakpoint is hit, the execution will pause, and you can inspect variables and step through the code using the debugging controls in the VS Code editor.
