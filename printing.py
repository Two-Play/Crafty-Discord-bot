def print_server_info(data) -> str:
    # Extract server names, server IPs and server ports from the API response
    server_info = [(server['server_id'], server['server_name'], server['server_ip'], server['server_port']) for
                   server in
                   data['data']]

    # Format the server information as text
    server_info_text = ""
    for id, name, ip, port in server_info:
        server_info_text += f"```\nID: {id}\nServer: {name}\n  IP: {ip}\n  Port: {port}\n```\n"
    return server_info_text

def print_server_status(data) -> str:
    data = data['data']

    cpu_usage = data['cpu']
    mem = data['mem']
    mem_percent = data['mem_percent']
    running = data['running']

    server_info_text: str
    if running:
         server_info_text = (
            f"```\nWorld: {data['world_name']}\nRunning: {running}\nPlayers: {data['players']}\nVersion: {data['version']}\nCPU: {cpu_usage}%\nRAM: {mem}MB ({mem_percent}%)\n```\n")
    else:
         server_info_text = f"```\nWorld: {data['world_name']}\nRunning: {running}\n```\n"
    return server_info_text