def write_out(message):
    file = open("/tmp/out", "w")
    file.write("We have triggered.")
    file.write(message)
    file.close()
