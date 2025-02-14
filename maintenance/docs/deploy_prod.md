````shell
sudo apt install libpq-dev postgresql curl postgresql-contrib python3-dev python3-venv python3-pip postgresql-client

create user and include him to sudo users

create same user on postgresql
CREATE USER pepito;
CREATE DATABASE unicornio OWNER pepito;
ALTER ROLE pepito CREATEDB;

sudo vim /etc/postgresql/16/main/postgresql.conf 
listen_addresses = ''
sudo systemctl restart postgresql
psql -h /var/run/postgresql -d unicornio

# log in as new user
ssh-keygen
cat .ssh/id_ed25519.pub

git clone git@github.com:chaufon/unicornio.git
python3 -m venv .venv
source .venv/bin/activate
cd unicornio/
pip install -r requirements/dev.txt

#create .env file

pip install -r requirements/prod.txt

#REDOIS
sudo apt install redis-server
sudo vim /etc/redis/redis.conf
unixsocket /run/redis/redis-server.sock
unixsocketperm 770
port 0
sudo systemctl restart redis
sudo usermod -aG redis pepito
reboot
redis-cli -s /var/run/redis/redis-server.sock ping

#NGINX
sudo apt install nginx
sudo mkdir /var/www/unicornio/static
sudo chown -R pepito:pepito /var/www/unicornio

#MISC
CREAR .env .env.sh
source .venv/bin/activate && source .env.sh && cd unicornio/
````
1. Disable ipv6
sudo vim /etc/sysctl.conf

net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1

sudo sysctl -p

1. sudo vim /etc/systemd/system/disable-ipv6.service
[Unit]
Description=Run my custom startup command
After=network.target

[Service]
ExecStart=/sbin/sysctl -p

[Install]
WantedBy=default.target

1. sudo systemctl enable disable-ipv6.service
1. `sudo systemctl start disable-ipv6.service`


1. sudo vim /etc/systemd/system/gunicorn.socket
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target

1. sudo vim /etc/systemd/system/gunicorn.service
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=pepito
Group=www-data
WorkingDirectory=/home/pepito/unicornio
EnvironmentFile=/home/pepito/.env
ExecStart=/home/pepito/.venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target

1. sudo systemctl start gunicorn.socket
1. sudo systemctl enable gunicorn.socket
1. sudo systemctl enable gunicorn.service

1. sudo vim /etc/nginx/sites-available/unicornio

server {
    listen 80;
    server_name myccenter.partner.pe;
    location /static/ {
        root /var/www/unicornio;
    }
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}

1. sudo ln -s /etc/nginx/sites-available/unicornio /etc/nginx/sites-enabled/

--

--
1. sudo apt install certbot python3-certbot-nginx

1. sudo certbot --nginx -d myccenter.partner.pe

1. sudo vim /etc/ssh/sshd_config.d/70-port.conf
Port 42424
PermitRootLogin no

reboot
1. block ip access to server by nginx.conf
1. sudo vim /etc/nginx/sites-available/block-ip
server {
     listen 80 default_server;
     listen 443 default_server;

     ssl_reject_handshake on;

     server_name _;

     return 444;
}
1. sudo ln -s /etc/nginx/sites-available/block-ip /etc/nginx/sites-enabled/
1. sudo vim /etc/nginx/nginx.conf 
server_tokens off;

 
1. estaesunaclavesuperlargaparaaburriraljaquer

