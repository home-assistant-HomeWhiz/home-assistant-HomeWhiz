# Develop On Linux
This is a quick tutorial on how to setup your development environment from scratch on any Debian
based Linux distro and get started. While this is based on VSCode, you can apply these steps to any
other IDE.

## Outline
1. Create a folder for you to work in
2. Get your system ready
3. Install VSCode
4. Setup you own git repository
5. Configure your development environment inside VSCode
6. Create and run tests

## Create a folder for you to work in
Open your file manager and create a new folder called 'dev' where you want to place your work
or at type the command line

`user@machine:$ mkdir dev`

## Get your system ready
We need to make sure the package list is up to date

`user@machine:$ sudo apt-get update`

`user@machine:$ sudo apt-get install python3 python3-dev python3-venv`

## Install Visual Studio Code
Go to https://code.visualstudio.com/Download and download your package (.deb)
then follow the instructions at https://code.visualstudio.com/docs/setup/linux

You can now launch VSCode!\
Follow the wizard and, at the end, select the folder you created before. You can answer 'yes' to
"Do you trust the authors of the files in this folder?".
You will be presented with a Welcome / Start screen, minimize the window for now.

## Setup your own git repository
1. Go to https://github.com and create an account if you haven't already
2. Go to https://github.com/rowysock/home-assistant-HomeWhiz
3. On the top right corner, click on the down arrow at the right of "Fork" and "create new fork"
4. Fill in the required fields and follow the instructions. You now have your own copy of the code to work with
5. Copy the URL (everything left of the '?' if present) e.g.: https://github.com/YOUR_NAME/home-assistant-HomeWhiz

## Configure your development environment inside VSCode
1. Return to VSCode and click on "Clone Git Repository" and paste the URL
2. Select your 'dev' folder in the dialog box and click "Select Repository Location"
3. At the prompt "Would you like to open ...", select Open. 
4. Now click Terminal on the menu bar at the to of the window, then New Terminal 

   The prompt should be `user@machine:~/dev/home-assistant-HomeWhiz$`

5. Create a virtual Python environment with `python3 -m venv ./venv`
6. Select the newly created virtual environment with `source venv/bin/activate`

   The prompt should change to `(venv) user@machine:~/dev/home-assistant-HomeWhiz$`\
   This is now the root of your project
   
7. Install the required Python dependencies

   `python3 -m pip install -r requirement_dev.txt` (using python3 -m instead of pip ensures that the same interpreter is used
   in the virtual environment should you have more than one version installed)

   `python3 -m pip install -r requirement_test.txt`

8. Install pre-commit with `pre-commit install`.\
   Pre-commit runs a series of automated checks before every commit to ensure a high and consistent code quality.
   You can also run pre-commit outside of commits with `pre-commit run --all-files`.

If everything works you should be set 

1. In VSCode click on the 4 Squares icon on the left of the screen (`ctrl+shift+x`) to open the Marketplace
2. Search for "Black", and select "Format Python code with black" in the results and install it. You'll be 
able to run it by right-clicking your file and select "Run Black"

You should now have a fully functional IDE. 

## Running tests
If your code requires automated testing, the project uses pytest.

Simply go to the root of your project and run `pytest`
