def write_out(message):
    with open('/tmp/out', 'w') as f:
        f.write("We have triggered.")
        f.write(message)
