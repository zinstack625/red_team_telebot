FROM python:alpine

WORKDIR /usr/src/red-team-telebot
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python3", "-m", "red_team_telebot"]