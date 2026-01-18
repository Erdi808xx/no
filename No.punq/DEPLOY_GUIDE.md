---
description: Deploying No.punq to the Cloud (Free & 24/7)
---

# 🚀 Ücretsiz ve 7/24 Aktif Yayınlama Rehberi

Bu rehber, No.punq botunu ve panelini **Render.com** üzerinde %100 ücretsiz ve sürekli aktif olacak şekilde nasıl yayınlayacağınızı anlatır.

## 1. Hazırlık (GitHub)
Botunuzu yayınlamak için kodlarınızın GitHub'da olması gerekir.
1. [GitHub](https://github.com) hesabınıza giriş yapın.
2. Yeni bir **Repository** oluşturun (Örn: `nopunq-bot`).
3. Kodlarınızı bu repository'ye yükleyin.

## 2. Render.com Kurulumu (Web Servisi)
Render, botun web panelini ve kendisini çalıştırmak için en iyi ücretsiz seçenektir.
1. [Render.com](https://render.com) adresine gidin ve GitHub ile giriş yapın.
2. **"New +"** butonuna tıklayın ve **"Web Service"** seçin.
3. GitHub repository'nizi listeden seçin ve **Connect** deyin.
4. Aşağıdaki ayarları yapın:
   - **Name:** `nopunq` (veya istediğiniz isim)
   - **Region:** `Frankfurt` (Türkiye'ye en yakın)
   - **Branch:** `main` (veya master)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Instance Type:** `Free`
5. **Environment Variables** kısmına tıklayın ve şu bilgileri ekleyin:
   - `TOKEN`: (Discord Bot Tokeniniz)
   - `CLIENT_ID`: (Bot ID)
   - `CLIENT_SECRET`: (OAuth2 Secret)
   - `REDIRECT_URI`: `https://SİZİN-APP-İSMİNİZ.onrender.com/callback` (Bunu Render size app ismi verince güncelleyin)
   - `OWNER_ID`: (Kendi Discord ID'niz)
6. **Create Web Service** butonuna basın.

## 3. Discord Developer Portal Ayarı
Render size `https://nopunq.onrender.com` gibi bir adres verecektir.
1. [Discord Developer Portal](https://discord.com/developers/applications) adresine gidin.
2. Botunuzu seçin -> **OAuth2** menüsüne gelin.
3. **Redirects** kısmına Render adresinizin sonuna `/callback` ekleyerek yazın.
   - Örn: `https://nopunq.onrender.com/callback`
4. Değişiklikleri kaydedin.

## 4. 7/24 Aktif Tutma (UptimeRobot)
Render ücretsiz sunucuları 15 dakika işlem olmazsa uyku moduna geçer. Bunu engellemek için dışarıdan dürtmemiz (ping) gerekir.
1. [UptimeRobot](https://uptimerobot.com) adresine gidin (Ücretsiz).
2. Kayıt olun ve **"Add New Monitor"** butonuna basın.
3. Ayarlar:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `No.punq Bot`
   - **URL (or IP):** `https://SİZİN-APP-İSMİNİZ.onrender.com`
   - **Monitoring Interval:** `5 minutes`
4. **Create Monitor** deyin.

🎉 **Tebrikler!** Artık botunuz ve web paneliniz kapanmadan 7/24 çalışacak.

## ⚠️ Önemli Uyarı: Veri Kaybı
Render (Free Tier) her yeniden başlatmada (deploy) sunucu diskini sıfırlar. 
- **config.json** ve **database.json** içindeki veriler silinebilir.
- Kalıcı veri için daha sonra **MongoDB** gibi bir bulut veritabanına geçiş yapmamız gerekebilir. Şimdilik botu her güncellediğinizde ayarlar sıfırlanabilir, yedeğinizi alın.
