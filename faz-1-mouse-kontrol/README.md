# El Kontrollü Fare (Hand-Tracking Mouse)

Bu proje, standart bir web kamerası ve görüntü işleme teknolojileri kullanarak bilgisayar faresini sadece el hareketleriyle kontrol etmeyi sağlayan Python tabanlı bir yazılımdır.

> **Ders 1 (V1, arşiv).** Bu klasör ilk sürüm olarak olduğu gibi korunuyor. Takılma, titreme
> ve tıklama sorunlarının çözüldüğü sürüm: [Ders 2: Fare V2](../dersler/ders_02_fare_v2/)

## 🚀 Özellikler (Faz 1 - Temel Kontrol)

* **İmleç Takibi:** Başparmak ucu baz alınarak ekrandaki fare imlecinin düşük gecikmeli takibi.
* **Akıllı Tıklama Mekanizması:** İşaret parmağı ve başparmak arasındaki dinamik mesafeye dayalı olarak;
    * Tek tıklama
    * Çift tıklama (Klasör/dosya açma toleransı ile)
    * Basılı tutarak sürükleme (Drag & Drop)
* **Matematiksel Yumuşatma (Smoothing):** Kamera sarsıntılarını ve nefes alma gibi mikro titreşimleri filtreleyerek stabil bir imleç deneyimi sunar.
* **Sanal Çalışma Alanı (Bounding Box):** Kullanıcının tüm ekrana ulaşmak için fiziksel olarak geniş el hareketleri yapmasını engelleyen, kamera içi oranlama sistemi.
* **Uyku Modu (Toggle):** Eli yumruk yaparak sistemi duraklatma ve istenmeyen tıklamaları engelleme. Tekrar yumruk hareketiyle sistem uyanır.

## 🛠️ Kullanılan Teknolojiler

* **Python:** Ana programlama dili.
* **OpenCV:** Görüntü yakalama ve ekrana görsel geri bildirim (çizim/yazı) basma.
* **MediaPipe:** Yapay zeka destekli el ve eklem noktası (landmark) tespiti.
* **PyAutoGUI:** İşletim sistemi seviyesinde fare (hareket, tıklama) simülasyonu.

## ⚙️ Kurulum ve Kullanım

1. Repoyu bilgisayarınıza klonlayın ve projenin ilgili faz klasörüne girin:
   ```bash
   cd faz-1-mouse-kontrol
   ```

2. İzole bir Python sanal ortamı (venv) oluşturun ve aktifleştirin:
    * Windows için: 
        ```bash
        python -m venv venv 
        .\venv\Scripts\activate
        ```

    * Mac/Linux için: 
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3. Gerekli kütüphaneleri requirements.txt üzerinden yükleyin:
    ```bash
    pip install -r requirements.txt
    ```

4. Uygulamayı çalıştırın:
    ```bash
    python hand_tracking.py
    ```