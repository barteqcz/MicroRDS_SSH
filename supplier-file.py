from paramiko import AutoAddPolicy, SSHClient
from configparser import ConfigParser
import os
import time

def connect_to_ssh(address, username, password, port):
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    
    try:
        ssh_client.connect(address=address, port=port, username=username, password=password)
        print("Successfully connected to the SSH server")
        return ssh_client

    except Exception as e:
        print(f"Error connecting to the SSH server: {e}")
        return None

def run_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    print(stdout.read().decode())
    print(stderr.read().decode())

def write_to_fifo(ssh_client, fifo_path, data):
    try:
        channel = ssh_client.get_transport().open_session()
        channel.exec_command(f'echo -e "{data}\\n" > {fifo_path}')
        channel.shutdown_write()

    except Exception as e:
        print(f"Error writing to FIFO file: {e}")

def send_commands_from_file(ssh_client, fifo_path, local_file_path):
    try:
        prev_mod_time = os.path.getmtime(local_file_path)
        
        while True:
            curr_mod_time = os.path.getmtime(local_file_path)
            
            if curr_mod_time != prev_mod_time:
                prev_mod_time = curr_mod_time
                with open(local_file_path, 'r') as file:
                    for line in file:
                        command = line.strip()
                        if command:
                            write_to_fifo(ssh_client, fifo_path, command)
            time.sleep(1)

    except KeyboardInterrupt:
        print("Closing the screen session and connection...")
        run_command(ssh_client, 'screen -S MicroRDS -X quit')
        ssh_client.close()
    except FileNotFoundError:
        print(f"Error: File '{local_file_path}' not found.")
    except Exception as e:
        print(f"Error reading or sending commands: {e}")

if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.conf')

    ssh_config = config['SSH']
    settings = config['Settings']

    address = ssh_config.get('address')
    port = ssh_config.getint('port')
    username = ssh_config.get('username')
    password = ssh_config.get('password')

    fifo_path = settings.get('fifo_path')
    encoder_path = settings.get('encoder_path')
    source_path = settings.get('source_path')

    ssh_client = connect_to_ssh(address, username, password, port)

    if ssh_client:
        run_command(ssh_client, f'screen -dmS MicroRDS bash -c "cd {encoder_path} && ./micrords --ctl {fifo_path}"')
        print(f"Reading commands from {source_path}")
        send_commands_from_file(ssh_client, fifo_path, source_path)
