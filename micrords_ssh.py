import os
from sys import exit, executable
from paramiko import AutoAddPolicy, SSHClient
from configparser import ConfigParser
from time import sleep

def closeAll():
    print("Closing the screen session and connection...")
    commandRunning(ssh_client, 'screen -S MicroRDS -X quit')
    ssh_client.close()
    exit()

def sshConnection(address, username, password, port):
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    
    try:
        ssh_client.connect(hostname=address, port=port, username=username, password=password)
        print("Successfully connected to the SSH server")
        return ssh_client

    except Exception as e:
        print(f"Error: Connection to the SSH server failed: {e}")
        return None

def commandRunning(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    print(stdout.read().decode())
    print(stderr.read().decode())

def fifoWriting(ssh_client, fifo_path, data):
    try:
        channel = ssh_client.get_transport().open_session()
        channel.exec_command(f'echo -e "{data}\\n" > {fifo_path}')
        channel.shutdown_write()

    except Exception as e:
        print(f"Error: Writing to FIFO file not possible: {e}")

def fileCommands(ssh_client, fifo_path, source_path):
    try:
        prev_mod_time = os.path.getmtime(source_path)
        prev_content = ""
        
        while True:
            curr_mod_time = os.path.getmtime(source_path)
            
            if curr_mod_time > prev_mod_time:
                prev_mod_time = curr_mod_time
                with open(source_path, 'r') as file:
                    new_content = file.read()
                    if new_content != prev_content:
                        prev_content = new_content
                        lines = new_content.split("\n")
                        for line in lines:
                            line = line.strip()
                            if line:
                                fifoWriting(ssh_client, fifo_path, line)
            sleep(1)

    except FileNotFoundError:
        print(f"Error: File '{source_path}' not found.")
        closeAll()

    except Exception as e:
        print(f"Error: Reading or sending commands not possible: {e}")
        closeAll()

if __name__ == "__main__":
    try:
        exe_dir = os.path.dirname(executable)
        config_path = os.path.join(exe_dir, 'config.conf')

        config = ConfigParser()
        config.read(config_path)

        ssh_config = config['SSH']
        settings = config['Settings']

        address = ssh_config.get('address')
        port = ssh_config.getint('port')
        username = ssh_config.get('username')
        password = ssh_config.get('password')

        fifo_path = settings.get('fifo_path')
        encoder_path = settings.get('encoder_path')
        source_path = settings.get('source_path')

        ssh_client = sshConnection(address, username, password, port)

        if ssh_client:
            commandRunning(ssh_client, f'screen -dmS MicroRDS bash -c "cd {encoder_path} && ./micrords --ctl {fifo_path}"')
            try:
                print(f"Reading commands from {source_path}")
                with open(source_path, 'r') as file:
                    for line in file:
                        command = line.strip()
                        if command:
                            fifoWriting(ssh_client, fifo_path, command)

            except FileNotFoundError:
                print(f"Error: File '{source_path}' not found.")
                closeAll()
            fileCommands(ssh_client, fifo_path, source_path)

    except KeyboardInterrupt:
        closeAll()
