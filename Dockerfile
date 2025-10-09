FROM python:3.11-slim

# Sistem paketlerini güncelle ve Node.js ekle
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg2 \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libgbm1 \
    xdg-utils \
    --no-install-recommends

# Node.js 20 LTS kur
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Chrome key ekle
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg

# Chrome repository ekle
RUN sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'

# Chrome kur
RUN apt-get update && apt-get install -y google-chrome-stable

# Temizlik
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node.js dependencies kur
COPY package.json .
RUN npm install

# Uygulama dosyalarını kopyala
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]