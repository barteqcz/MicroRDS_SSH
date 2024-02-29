# MicroRDS_SSH

This is a script in Python that connects to a remote SSH server, runs MicroRDS and controls it with a text file from the SSH client.

### Installation

#### Binaries

You can just download a binary file for your system (the client system) [here](https://github.com/barteqcz/MicroRDS_SSH/releases/latest/).

#### Running from source

You can run it with an interpreter. E.g. `python micrords_ssh.py` (not recommended)

You can also compile the code with `pyinstaller`. You will need the `pyinstaller` package along with `paramiko` library. Then you can just run `pyinstaller --onefile --icon NONE micrords_ssh.py`. The exe will be in the `dist` folder.

### Customization

To change the IP/hostname, port, username or password, see `config.conf`.
