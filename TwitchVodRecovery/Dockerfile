FROM python

WORKDIR /app

COPY config .
COPY lib .
COPY shortcuts .
COPY install_dependencies.py .

COPY . .

RUN python install_dependencies.py

CMD bash