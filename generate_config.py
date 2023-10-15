import configparser, random, string,base64

configuration = {}

def randomword(length):
    letters = string.ascii_letters
    word = ''.join(random.choice(letters) for i in range(length))

    return word

print(randomword(10))
print(randomword(16))

print("==== Supabase Config ====")
print("URL: ", end=None)
supabase_url = input()
print("API Key: ", end=None)
supabase_api_key = input()

print("\n==== API Configuration ====")
print("Hostname: ", end=None)
api_hostname = input()
print("Port: ", end=None)
port = int(input())

print("\n==== Message Compression Config ====")
print("Transmission Interval [s]: ", end= None)
interval = int(input())
print("Batch Size: ", end=None)
batch_size = int(input())
print("Maximum Worker Threads: ", end=None)
thread_count = int(input())

print("\n==== MQTT Config ====")
print("Username Length: ", end= None)
username_len = int(input())
print("Password Length:: ", end=None)
password_len = int(input())



print('Generating config file...')
config = configparser.ConfigParser()
config['SUPABASE'] = {
    'URL': supabase_url,
    'API_KEY': supabase_api_key
}

config['API'] = {
    'HOST': api_hostname,
    'PORT': port
}

config['COMPRESSION_SETTINGS'] = {
    'INTERVAL': interval,
    'BATCH_SIZE': batch_size,
    'MAX_THREADS': thread_count
}

config['MQTT'] = {
    'USERNAME': randomword(username_len),
    'PASSWORD': randomword(password_len)
}

print('Saving config to file...')
with open("config.ini", "w") as file:
    config.write(file)

print('Successfully saved configuration settings to config.ini')