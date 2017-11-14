# Use an official Python runtime as a parent image
FROM python:3.5.3-slim

# Set the working directory to /app
WORKDIR /foglamp

# Copy the current directory contents into the container at /app
ADD . /foglamp

# Install any needed packages specified in requirements.txt
RUN pip3 install --trusted-host pypi.python.org -r python/requirements.txt
RUN pip3 install python/build/foglamp-0.1.tar.gz

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

ENV DB_CONNECTION "dbname=foglamp user=foglamp"
ENV FOGLAMP_ROOT /foglamp/C/services/storage/build

# Run app.py when the container launches
CMD ["python3", "-m", "foglamp.services.core"]
