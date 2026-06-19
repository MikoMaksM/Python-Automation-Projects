import os
import time
import smtplib
import requests
import paramiko
import linode_api4
import schedule

EMAIL_ADDRESS      = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD     = os.environ.get('EMAIL_PASSWORD')
LINODE_TOKEN       = os.environ.get('LINODE_TOKEN')
LINODE_INSTANCE_ID = int(os.environ.get('LINODE_INSTANCE_ID'))

CONTAINER_HOST_IP  = os.environ.get('CONTAINER_HOST_IP')
CONTAINER_SSH_USER = os.environ.get('CONTAINER_SSH_USER')
CONTAINER_SSH_KEY  = os.environ.get('CONTAINER_SSH_KEY')
CONTAINER_NAME     = os.environ.get('CONTAINER_NAME')
CONTAINER_URL      = f'http://{CONTAINER_HOST_IP}:8080/'


def send_notification(message):
    print('Sending email notification...')
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.ehlo()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, f'Subject: SITE DOWN\n{message}')
    except Exception as e:
        print(f'Email sending failed: {e}')


def restart_container():
    print('Restarting the container...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=CONTAINER_HOST_IP, username=CONTAINER_SSH_USER, key_filename=CONTAINER_SSH_KEY)
    _, stdout, _ = ssh.exec_command(f'docker restart {CONTAINER_NAME}')
    print(stdout.readlines())
    ssh.close()


def restart_server_and_container():
    print('Rebooting the Linode server...')
    client = linode_api4.LinodeClient(LINODE_TOKEN)
    server = client.load(linode_api4.Instance, LINODE_INSTANCE_ID)
    server.reboot()

    print('Waiting for server to come back online...')
    while True:
        server = client.load(linode_api4.Instance, LINODE_INSTANCE_ID)
        if server.status == 'running':
            time.sleep(5)
            restart_container()
            break


def monitor_application():
    try:
        response = requests.get(CONTAINER_URL)
        if response.status_code == 200:
            print('Application is running successfully.')
        else:
            print(f'Application returned {response.status_code}. Restarting container...')
            send_notification(f'Application returned status code {response.status_code}.')
            restart_container()
    except Exception as e:
        print(f'Connection error: {e}')
        send_notification('Application is not accessible. Rebooting server.')
        restart_server_and_container()


schedule.every(5).minutes.do(monitor_application)

while True:
    schedule.run_pending()
