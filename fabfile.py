from fabric.api import *

env.hosts = ['spoke.techbikers.com']
env.user = 'django'

def deploy():
    "Updates the repository."
    print "ENV %s" %(env.hosts)
    run("cd ~/webapps/techbikers.com/; git pull")
    run("cd ~/webapps/techbikers.com/; sed 's/^DEBUG = True$/DEBUG = False/' -i techbikers/settings.py")
    sudo("supervisorctl stop techbikers.com")
    sudo("pkill django")
    sudo("pkill gunicorn")
    sudo("supervisorctl start techbikers.com")
