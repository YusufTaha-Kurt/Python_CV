
# Complated:
# El Takibi ve İşaret Parmağı Ucunu Tespit Etme işlemleri tamamlandı. 
# Baş ve İşaret parmağı birbirine temas ettirilince "TIKLANDI" yazısı ekrana geliyor ve gerçek fare tıklaması gerçekleşiyor.


import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os
import math
import pyautogui
import time


# 1. Model Dosyasını İndir (Sadece ilk çalışmada bir kere indirilir)
dosya_dizini = os.path.dirname(os.path.abspath(__file__))
model_yolu = os.path.join(dosya_dizini, 'hand_landmarker.task')
if not os.path.exists(model_yolu):
    print("MediaPipe yapay zeka modeli indiriliyor (yaklaşık 30MB)... Lütfen bekleyin.")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, model_yolu)
    print("Model başarıyla indirildi!")

# 2. Yeni Nesil MediaPipe Tasks API Ayarları
base_options = python.BaseOptions(model_asset_path=model_yolu)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_hands=2) # Ekranda aranacak maksimum el sayısı
dedektor = vision.HandLandmarker.create_from_options(options)

# 3. Kamerayı Başlat
kamera = cv2.VideoCapture(0) #Eğer harici bir kamera kullanıyorsanız, 1 veya 2 gibi farklı bir sayı deneyebilirsiniz.

# Ekranımızın (monitörün) tam piksel boyutlarını al
ekran_genisligi, ekran_yuksekligi = pyautogui.size()
# Fare köşelere gidince programın çökmesini engelleyen güvenlik kilidini kapat
pyautogui.FAILSAFE = False

# Tıklama mekanizması için durum değişkenleri
son_tiklama_zamani = 0
tiklama_durumu = False
basili_tutuluyor_mu = False
temas_baslangic_zamani = 0 

# Yumuşatma (Smoothing) için değişkenler
onceki_fare_x, onceki_fare_y = 0, 0
yumusatma_faktoru = 2 # Bu değer arttıkça fare daha hantal ama pürüzsüz hareket eder (3-7 arası idealdir)

# Sanal Çalışma Alanı (Bounding Box) değişkeni
kutu_kenar_boslugu = 100 # Kameranın kenarlarından bırakılacak piksel boşluğu

# Uyku modu toggle (aç-kapat) değişkenleri
uyku_modu_aktif = False
son_yumruk_zamani = 0

while True:
    basarili, kare = kamera.read()
    if not basarili:
        break

    # Görüntüyü yatayda çevir (Ayna etkisi)
    kare = cv2.flip(kare, 1)

    # OpenCV görüntüyü BGR okur, MediaPipe ise RGB bekler. Formatı çeviriyoruz:
    rgb_kare = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_kare)

    # 4. Görüntüyü yapay zekaya ver ve elleri tespit et
    sonuc = dedektor.detect(mp_image)

    # 5. İşaret ve Başparmak ucu ile "Tıklama" mekanizması
    if sonuc.hand_landmarks:
        yukseklik, genislik, _ = kare.shape
        
        # Hangi el olduğunu (sağ/sol) ayırt edebilmek için enumerate kullanıyoruz
        for i, el_noktalari in enumerate(sonuc.hand_landmarks):
            
            # Sadece sağ eli işleme al
            # Not: Kamerayı cv2.flip ile aynaladığımız için fiziksel sağ elin MediaPipe'ta 'Left' olarak görünür.
            # Eğer sistem sol elinde çalışırsa buradaki 'Left' yazısını 'Right' olarak değiştir.
            el_taraf = sonuc.handedness[i][0].category_name
            if el_taraf != 'Left': 
                continue
            
            # --- 1. UYKU MODU (YUMRUK KONTROLÜ) ---
            # Parmak uçlarının bileğe (0) olan mesafesini, alt boğumların bileğe olan mesafesiyle kıyaslıyoruz.
            def bilek_mesafesi(nokta_idx):
                return math.hypot(el_noktalari[nokta_idx].x - el_noktalari[0].x, el_noktalari[nokta_idx].y - el_noktalari[0].y)
                
            isaret_kapali = bilek_mesafesi(8) < bilek_mesafesi(6)
            orta_kapali = bilek_mesafesi(12) < bilek_mesafesi(10)
            yuzuk_kapali = bilek_mesafesi(16) < bilek_mesafesi(14)
            serce_kapali = bilek_mesafesi(20) < bilek_mesafesi(18)

            su_an = time.time()
            yumruk_yapildi_mi = isaret_kapali and orta_kapali and yuzuk_kapali and serce_kapali

            # Yumruk yapıldığında ve bir önceki tetiklenmenin üzerinden 1 saniye geçtiyse (sürekli aç/kapa yapmasını engellemek için)
            if yumruk_yapildi_mi and (su_an - son_yumruk_zamani > 1.0):
                uyku_modu_aktif = not uyku_modu_aktif # Durumu tersine çevir (Açıksa kapat, kapalıysa aç)
                son_yumruk_zamani = su_an

            # Eğer uyku modu aktifse ekrana yazı yazdır ve fare işlemlerini atla
            if uyku_modu_aktif:
                cv2.putText(kare, "UYKU MODU AKTIF (UYANMAK ICIN YUMRUK YAP)", (15, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)
                continue # Alttaki fare hareketini ve tıklama işlemlerini atlayıp başa döner
            # ---------------------------------------------

            # İşaret parmağı ucu (8) ve Başparmak ucu (4) koordinatlarını al
            isaret_ucu = el_noktalari[8]
            basparmak_ucu = el_noktalari[4]
            
            # Oransal değerleri gerçek piksel koordinatlarına çevir
            x1, y1 = int(isaret_ucu.x * genislik), int(isaret_ucu.y * yukseklik)
            x2, y2 = int(basparmak_ucu.x * genislik), int(basparmak_ucu.y * yukseklik)

            # --- 2. SANAL ÇALIŞMA ALANI (BOUNDING BOX) ---
            # Ekranda referans alacağımız dikdörtgeni mor renkle çiz
            cv2.rectangle(kare, (kutu_kenar_boslugu, kutu_kenar_boslugu), 
                         (genislik - kutu_kenar_boslugu, yukseklik - kutu_kenar_boslugu), (255, 0, 255), 2)

            # Sınırları belirle
            min_x, max_x = kutu_kenar_boslugu, genislik - kutu_kenar_boslugu
            min_y, max_y = kutu_kenar_boslugu, yukseklik - kutu_kenar_boslugu

            # Başparmağın piksel koordinatını kutu sınırları içinde tut (Dışarı taşarsa kutu sınırına sabitler)
            sinirli_x = max(min_x, min(x2, max_x))
            sinirli_y = max(min_y, min(y2, max_y))

            # Sadece KUTU İÇİNDEKİ dar alanı, BÜTÜN EKRANA (monitöre) oranla
            hedef_fare_x = int(((sinirli_x - min_x) / (max_x - min_x)) * ekran_genisligi)
            hedef_fare_y = int(((sinirli_y - min_y) / (max_y - min_y)) * ekran_yuksekligi)
            # ---------------------------------------------------
            
            # Yumuşatma (Smoothing) formülü
            fare_x = onceki_fare_x + (hedef_fare_x - onceki_fare_x) / yumusatma_faktoru
            fare_y = onceki_fare_y + (hedef_fare_y - onceki_fare_y) / yumusatma_faktoru
            
            # Fareyi hareket ettir
            pyautogui.moveTo(int(fare_x), int(fare_y))
            
            # Bir sonraki döngü için mevcut konumu kaydet
            onceki_fare_x, onceki_fare_y = fare_x, fare_y
            
            # 3. İki parmak ucuna da daire çiz ve aralarına bir çizgi çek
            cv2.circle(kare, (x1, y1), 12, (0, 0, 255), -1) # Kırmızı (İşaret)
            cv2.circle(kare, (x2, y2), 12, (255, 0, 0), -1) # Mavi (Başparmak)
            cv2.line(kare, (x1, y1), (x2, y2), (0, 255, 0), 3) # Yeşil Çizgi
            
            # 4. İki nokta arasındaki mesafeyi ölç
            mesafe = math.hypot(x2 - x1, y2 - y1)
            
            # 5. Gelişmiş Tıklama Mekanizması
            if mesafe < 25: 
                cv2.circle(kare, (x1, y1), 15, (0, 255, 0), -1) 
                
                su_an = time.time()
                if not tiklama_durumu: # Parmaklar ilk defa birleştiğinde
                    temas_baslangic_zamani = su_an # Temasın ne kadar sürdüğünü ölçmek için sayacı başlat
                    
                    # 1.0 saniye işletim sistemleri için çok uzun. Çift tık toleransını 0.45'e düşürdük.
                    if su_an - son_tiklama_zamani < 0.45: 
                        pyautogui.mouseDown()
                        basili_tutuluyor_mu = True
                    else:
                        pyautogui.click() # Normal tek tıklama
                        son_tiklama_zamani = su_an
                
                tiklama_durumu = True

                # Ekrana görsel geri bildirim yazdır
                if basili_tutuluyor_mu:
                    cv2.putText(kare, "BASILI TUTULUYOR (SURUKLE)!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                else:
                    cv2.putText(kare, "TIKLANDI!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

            else:
                # Parmaklar birbirinden ayrıldığında
                if tiklama_durumu:
                    if basili_tutuluyor_mu:
                        pyautogui.mouseUp() # Önce basılı tutulan tuşu bırak
                        basili_tutuluyor_mu = False
                        
                        # EĞER KULLANICI İKİNCİ TIKLAMAYI ÇOK KISA TUTTUYSA (0.25 saniyeden az):
                        # Bu bir sürükleme hamlesi değil, klasör açmak için yapılmış bir çift tıklamadır.
                        if time.time() - temas_baslangic_zamani < 0.25:
                            pyautogui.click() # Sistemi çift tıklamaya ikna etmek için ekstra bir tık daha at
                            
                tiklama_durumu = False

    cv2.imshow("Kamera Ekrani", kare)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

kamera.release()
cv2.destroyAllWindows()