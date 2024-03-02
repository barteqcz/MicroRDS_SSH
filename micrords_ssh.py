import os
from sys import exit, executable
from paramiko import AutoAddPolicy, SSHClient
from configparser import ConfigParser
from time import sleep

def sshConnection(hostname, username, password, port):
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(AutoAddPolicy())
    
    try:
        print("Connecting to the SSH server...\n")
        ssh_client.connect(hostname=hostname, port=port, username=username, password=password)
        print("Successfully connected to the SSH server")
        return ssh_client

    except Exception as e:
        print(f"Error: Connection to the SSH server failed: {e}\n")
        input("Press any key to exit...")
        exit()

def commandRunning(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    print(stdout.read().decode())
    print(stderr.read().decode())

def closeAll():
    print("Stopping the encoder and closing the connection...")
    commandRunning(ssh_client, 'screen -S MicroRDS -X quit')
    ssh_client.close()
    exit()

def fifoWriting(ssh_client, fifo_path, data):
    try:
        channel = ssh_client.get_transport().open_session()
        channel.exec_command(f'echo -e "{data}\\n" > {fifo_path}')
        channel.shutdown_write()

    except Exception as e:
        print(f"Error: Writing to FIFO file not possible: {e}\n")
        input("Press any key to exit...")
        closeAll()

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
            sleep(0.1)

    except FileNotFoundError:
        print(f"Error: File '{source_path}' not found.\n")
        input("Press any key to exit...")
        closeAll()

    except Exception as e:
        print(f"Error: Reading or sending commands not possible: {e}\n")
        input("Press any key to exit...")
        closeAll()

def checkRemotePathExists(ssh_client, path):
    stdin, stdout, stderr = ssh_client.exec_command(f'[ -e "{path}" ] && echo "Exists" || echo "Does not exist"')
    result = stdout.read().decode().strip()
    if result == "Exists":
        return True
    else:
        return False

if __name__ == "__main__":
    try:
        exeDir = os.path.dirname(executable)
        configPath = os.path.join(exeDir, 'config.conf')
        configExists = os.path.exists(configPath)

        if not configExists:
            print("Generating config file...")
            with open(configPath, 'a') as file:
                file.write(r"""[SSH]
# The hostname of the SSH server. It can be either IP, or hostname of the server.
hostname = 192.168.0.10

# The port that SSH server is running on.
port = 22

# Username that will be used to connect to the SSH server.
username = changeme

# Password that will be used to connect to the SSH server.  
password = changeme

[Settings]
# This is the path to the MicroRDS executable file directory.
encoder_path = /home/username/MicroRDS/src/

# This is the local file that contains the commands to be sent.
source_path = C:\Users\username\Documents\rds.txt

# This is the remote FIFO file that is used with MicroRDS.
fifo_path = /home/username/MicroRDS/scripts/rds_fifo""")
            print("Config file generated, adjust it to your needs and re-run the program.\n")
            input("Press any key to exit...")
            exit()

        try:
            config = ConfigParser()
            config.read(configPath)

            ssh_config = config['SSH']
            settings = config['Settings']

            hostname = ssh_config.get('hostname')
            port = ssh_config.getint('port')
            username = ssh_config.get('username')
            password = ssh_config.get('password')

            fifo_path = settings.get('fifo_path')
            encoder_path = settings.get('encoder_path')
            source_path = settings.get('source_path')

        except KeyError:
            print("Error: Syntax errors found in the config file.\n")
            input("Press any key to exit...")
            exit()

        ssh_client = sshConnection(hostname, username, password, port)

        if ssh_client:
            if not checkRemotePathExists(ssh_client, encoder_path):
                print("Error: Given encoder path doesn't exist on the SSH server.\n")
                input("Press any key to exit...")
                closeAll()

            if not checkRemotePathExists(ssh_client, fifo_path):
                print("Error: Given FIFO path doesn't exist on the SSH server.\n")
                input("Press any key to exit...")
                closeAll()

            commandRunning(ssh_client, f'screen -dmS MicroRDS bash -c "cd {encoder_path} && ./micrords --ctl {fifo_path}"')
            try:
                print(f"Reading commands from {source_path}")
                with open(source_path, 'r') as file:
                    for line in file:
                        command = line.strip()
                        if command:
                            fifoWriting(ssh_client, fifo_path, command)

            except FileNotFoundError:
                print(f"Error: File '{source_path}' not found.\n")
                input("Press any key to exit...")
                closeAll()

            fileCommands(ssh_client, fifo_path, source_path)

    except KeyboardInterrupt:
        closeAll()
