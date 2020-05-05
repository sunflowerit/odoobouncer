# Nginx extra security layer for Odoo

## Installation

### Install `direnv`

sudo apt install direnv
echo "eval \"$(direnv hook bash)\"" >> $HOME/.bashrc
source .bashrc

### Prepare project first time

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate-envrc.py > .envrc
direnv allow

## Usage

source venv/bin/activate
python main.py
gnome-open http://127.0.0.1:8080/

