from machine import UART, I2C, Pin, Timer
import time
import network
import espnow

# Initialisation UART pour Nextion
nextion = UART(2, baudrate=9600, tx=14, rx=13)

# Initialisation I2C pour la lecture de la batterie
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=100000)

# Constantes pour la batterie LiPo
TENSION_MAX = 4.2
TENSION_MIN = 3.0

# Initialisation de la valeur normalisée
normalized_value = 0

# Initialisation de pas (step)
step = 1

# Configuration ESP-NOW
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
e = espnow.ESPNow()
e.active(True)

# Adresse MAC de l'autre ESP32 (remplacer par la vôtre)
peer = b'\xb4\x8a\n\x8a/\x88'
e.add_peer(peer)

# Fonction pour convertir la tension de batterie en pourcentage
def voltage_to_percentage(voltage):
    return (voltage - TENSION_MIN) / (TENSION_MAX - TENSION_MIN) * 100

# Fonction pour envoyer la valeur de pourcentage à l'écran Nextion
def update_nextion(pourcentage, tension_data, etat_interrupteur):
        if (etat_interrupteur is "Ouvert"):
            valeur = 0
        elif (etat_interrupteur is "ferme"):
            valeur = 180

        commande_pourcentage = "j7.val=" + str(int(pourcentage))
        #print("Envoi de la commande à Nextion:", commande_pourcentage)  # Débogage
        commande_tension = "j6.val=" + str(int(float(tension_data)))
        #print("Envoi de la commande à Nextion:", commande_tension)  # Débogage
        commande_contact= "z0.val=" + str(valeur)
        #print("Envoi de la commande à Nextion:", commande_contact)  # Débogage
        print(" ")
        nextion.write(commande_pourcentage)
        nextion.write(b'\xff\xff\xff')
        nextion.write(commande_tension)
        nextion.write(b'\xff\xff\xff')
        nextion.write(commande_contact)
        nextion.write(b'\xff\xff\xff')

# Fonction pour lire la valeur de la batterie
def lire_tension_batterie():
    data = i2c.readfrom(78, 2)  # Lit 2 octets depuis le périphérique I2C à l'adresse 78 (0x4E en hexadécimal)
    msb = data[0] << 6          # Décale l'octet de poids fort de 6 bits vers la gauche
    lsb = data[1] >> 2          # Décale l'octet de poids faible de 2 bits vers la droite
    result = msb + lsb          # Combine les deux octets pour obtenir la valeur entière
    tension = (result * 5 / 1024)  # Convertit cette valeur en tension (en volts)
    return tension

# Callback pour le timer
def callback(timer):
    global tension, pourcentage_batterie, decoded_msg, e, peer, tension_data, interrupteur_data

    # Lire la tension de la batterie
    tension = lire_tension_batterie()
    pourcentage_batterie = voltage_to_percentage(tension)

    # Afficher les valeurs lues pour le débogage
    print("Batterie Pupitre :V {:.2f} ".format(tension))
    print("Batterie Pupitre :% {:.2f}".format(pourcentage_batterie))
    print("Batterie Etau    :% ", tension_data)
    print("Interrupteur     : ", interrupteur_data)
    print(" ")

    # Mettre à jour l'écran Nextion avec le pourcentage de batterie
    update_nextion(pourcentage_batterie, tension_data, interrupteur_data)

# Initialisation du timer
timer = Timer(0)
timer.init(period=8000, mode=Timer.PERIODIC, callback=callback)

# Fonction pour interpréter les données de Nextion
def interpret_data(data):
    global step
    data_list = list(data)
    if data_list[:5] == [112, 69, 116, 97, 117]:
        return "Page 1 << Etau >>"
    if data_list[:2] == [102, 0]:
        return "Page 0 << Accueil >>"
    if data_list[:10] == [112, 80, 97, 114, 97, 109, 101, 116, 114, 101]:
        return "Page 2 << Parametre >>"
    if data_list[:12] == [112, 80, 97, 103, 101, 32, 86, 101, 105, 108, 108, 101]:
        return "Page 3 << Mode veille >>"
    if data_list[:13] == [112, 80, 97, 103, 101, 32, 67, 111, 110, 116, 97, 99, 116]:
        return "Page 4 << Contact >>"
    if data_list[:8] == [112, 65, 118, 97, 110, 99, 101, 114]:
        return "Rotation sens horaire du moteur" # La tige du moteur sort
    if data_list[:8] == [112, 82, 101, 99, 117, 108, 101, 114]:
        return "Rotation sens antihoraire du moteur" # La tige du moteur rentre
    if data_list[:6] == [112, 82, 101, 115, 101, 116]:
        return "Renitialisation du moteur" # La tige est remise à zéro
    if data_list[:4] == [112, 43, 49, 48]:
        step = 10
        return "Parametrage de l'avancement et du recul en +10"
    if data_list[:3] == [112, 43, 49]:
        step = 1
        return "Parametrage de l'avancement et du recul en +1"
    if data_list[:3] == [112, 43, 53]:
        step = 5
        return "Parametrage de l'avancement et du recul en +5"
    if data_list[:4] == [112, 43, 50, 53]:
        step = 25
        return "Parametrage de l'avancement et du recul en +25"
    if data_list[:13] == [112, 76, 111, 110, 103, 117, 101, 117, 114, 32, 77, 97, 120]:
        return "Longueur Max"
    if data_list[:7] == [112, 49, 53, 32, 115, 101, 99]:
        return "Parametrage du mode veille en 15 sec"
    if data_list[:7] == [112, 51, 48, 32, 115, 101, 99]:
        return "Parametrage du mode veille en 30 sec"
    if data_list[:6] == [112, 49, 32, 109, 105, 110]:
        return "Parametrage du mode veille en 1 min"
    if data_list[:6] == [112, 50, 32, 109, 105, 110]:
        return "Parametrage du mode veille en 2 min"
    return None

# Boucle principale
while True:
    dataIn = nextion.read()  # Lecture des données série
    if dataIn:  # Vérifier si des données ont été reçues
        interpreted_data = interpret_data(dataIn)
        if interpreted_data:
            print("Texte affiché :", interpreted_data)
            if interpreted_data == "Rotation sens horaire du moteur":
                normalized_value += step
                if normalized_value > 100:
                    normalized_value = 100
            elif interpreted_data == "Rotation sens antihoraire du moteur":
                normalized_value -= step if normalized_value >= step else 0
            elif interpreted_data == "Renitialisation du moteur":
                normalized_value = 0
            print("Valeur de la jauge :", normalized_value)
            print(" ")
            e.send(peer, str(interpreted_data))
            e.send(peer, str(normalized_value))

    time.sleep(0.1)
    host, msg = e.recv()
    if msg:  # Vérifier si un message est reçu
        decoded_msg = msg.decode("utf-8")
        if decoded_msg.startswith("TENSION:"):
            tension_data = decoded_msg.split(":")[1]
        elif decoded_msg.startswith("INTERRUPTEUR:"):
            interrupteur_data = decoded_msg.split(":")[1]
