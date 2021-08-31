FROM python:3.9

WORKDIR /app

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 80

#ENV SLACK_BOT_TOKEN='TEXT'
#
#ENV SLACK_BOT_SIGNING_SECRET='TEXT'
#
#ENV SLACK_BOT_VERIFICATION_TOKEN='TEXT'

ENTRYPOINT ["python"]
CMD [ "main.py"]