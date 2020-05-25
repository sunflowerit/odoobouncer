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
    cp .envrc-template .envrc
    # now edit mail server settings
    python generate-secret-code.py
    # now copy the generated code into .envrc
    direnv allow

## Usage

    source venv/bin/activate
    python nginx-odoo.py -u http://localhost:8169 -d odoodatabase

Configure nginx `auth_request` to http://127.0.0.1:8888/

