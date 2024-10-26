import os


def check_env_vars():
    # check if all environment variables are set
    required_env_vars = []
    if not ('SERVER_URL' in os.environ):
        required_env_vars.append('SERVER_URL')
    if not ('DISCORD_TOKEN' in os.environ):
        required_env_vars.append('DISCORD_TOKEN')
    if not ('CRAFTY_TOKEN' in os.environ):
        if not ('USERNAME' in os.environ):
            required_env_vars.append('USERNAME')
        if not ('PASSWORD' in os.environ):
            required_env_vars.append('PASSWORD')
        required_env_vars.append('or CRAFTY_TOKEN')

    if len(required_env_vars) > 0:
        print('Not all environment variables set')
        for env_var in required_env_vars:
            print(env_var + ' not set')
        exit()

    print('All environment variables set')
    if os.environ['SERVER_URL'] == '':
        print('SERVER_URL not set')
        exit()
    if os.environ['CRAFTY_TOKEN'] == '':
        # if CRAFTY_TOKEN is not set, try to get it from the server
        if os.environ['USERNAME'] == '':
            print('USERNAME not set')
            exit()
        if os.environ['PASSWORD'] == '':
            print('PASSWORD not set')
            exit()
        else:
            print('CRAFTY_TOKEN not set')

    if os.environ['DISCORD_TOKEN'] == '':
        print('DISCORD_TOKEN not set')
        exit()
