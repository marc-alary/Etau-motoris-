import network
import espnow
import machine
import time
from machine import I2C, Pin, Timer

ENABLE = Pin(15, Pin.OUT)
M1 = Pin(16, Pin.OUT) # create output pin on GPIO0
M2 = Pin(17, Pin.OUT) # create output pin on GPIO0
DIR = Pin(27, Pin.OUT)   # create output pin on GPIO0
STEP = Pin(26, Pin.OUT)  # create output pin on GPIO0
STBY = Pin(25, Pin.OUT)  # create output pin on GPIO0

n=0
delais=0.05
step = 0
jauge = 0

def debut_reculer():
    M1.value(0)
    M2.value(0)
    DIR.value(1)
    STEP.value(0)
    STBY.value(0)
    
def debut_avancer():
    M1.value(0)
    M2.value(0)
    DIR.value(0)
    STEP.value(0)
    STBY.value(0)
    
def fin():
    M1.value(0)
    M2.value(0)
    DIR.value(0)
    STEP.value(0)
    STBY.value(0)
    
def debut_Renitialisation():
    M1.value(0)
    M2.value(0)
    DIR.value(1)
    STEP.value(0)
    STBY.value(0)
    
def pas(val):
    STBY.value(1)
    for n in range(val):
        STEP.value(1)
        time.sleep(delais)
        STEP.value(0)
        time.sleep(delais)
        print(n)
        
def Renitialisation():
    STBY.value(1)
    for n in range(jauge):
        STEP.value(1)
        time.sleep(delais)
        STEP.value(0)
        time.sleep(delais)
        
def butée():
    if (jauge > 600):
        print("moteur en butée")
        step=0
        fin()

interrupteur = Pin(35, Pin.IN, Pin.PULL_UP)


# Configuration de l'I2C
i2c = I2C(1, scl=Pin(22), sda=Pin(21), freq=100000)

# Initialisation de l'ESP-NOW
e = espnow.ESPNow()
e.active(True)
peer = b'\xb4\x8a\n\x8a/\xe4'  # L'adresse MAC de l'interface wifi de l'homologue
e.add_peer(peer)

# L'interface Wlan doit être active pour envoyer()/recevoir()
sta = network.WLAN(network.STA_IF)
sta.active(True)

# Définir la plage de tension de la batterie (dans cet exemple, de 3,0 à 4,2 volts)
min_voltage = 3.0
max_voltage = 4.2

# Fonction pour convertir la tension de batterie en pourcentage
def voltage_to_percentage(voltage):
    return (voltage - min_voltage) / (max_voltage - min_voltage) * 100

# Fonction pour lire les données et envoyer le message
def read_and_send(timer):
    try:
        # Lecture des données du périphérique I2C
        data = i2c.readfrom(78, 2)
        msb = data[0] << 6
        lsb = data[1] >> 2
        result = msb + lsb
        tension = (result * 5 / 1024)
        
        etat = interrupteur.value()
        interrupteur_etat = "ferme" if etat == 0 else "Ouvert"
        #print("interrupteur", interrupteur_etat)
        interrupteur_msg = "INTERRUPTEUR:{}".format(interrupteur_etat)
        e.send(peer, interrupteur_msg)

        
        # Affichage du résultat
        percentage = voltage_to_percentage(tension)
        #print("{:.2f}%".format(percentage))
        
        # Envoie du résultat
        tension_msg = "TENSION:{:.2f} ".format(voltage_to_percentage(tension))
        e.send(peer, tension_msg)
              
    except Exception as ex:
        print("Erreur lors de la lecture ou de l'envoi:", ex)

# Configuration du timer pour appeler la fonction toutes les 5 secondes
timer = Timer(0)
timer.init(period=1000, mode=Timer.PERIODIC, callback=read_and_send)

# Boucle principale
while True:
    
    host, msg = e.recv()
    decoded_msg = msg.decode("utf-8")
    #if msg:  # msg == None if timeout in recv()
    #    print("Valeur jauge:", decoded_msg)

# <------------------COMMANDE MOTEUR---------------------->

    if(msg == b"Parametrage de l'avancement et du recul en +1"):
        step = 6
        
    if(msg == b"Parametrage de l'avancement et du recul en +5"):
        step = 30
        
    if(msg == b"Parametrage de l'avancement et du recul en +10"):
        step = 60 
        
    if(msg == b"Parametrage de l'avancement et du recul en +25"):
        step = 150
            
    if(msg == b'Rotation sens antihoraire du moteur'):
        debut_reculer()
        pas(step)
        jauge = jauge - step
        if(jauge <= 0):
            jauge = 0
        print("Jauge moteur :",jauge)
        fin()
        
    if(msg == b'Rotation sens horaire du moteur'):
        debut_avancer()
        pas(step)
        jauge = jauge + step
        print("Jauge moteur :",jauge)
        butée()
        fin()

    if(msg == b'Renitialisation du moteur'):
        debut_Renitialisation()
        Renitialisation()
        jauge = 0 
        print("Jauge moteur :",jauge)
        fin()
