import network
import espnow
import time
import ujson
from machine import I2C, Pin, Timer


# =========
# variables
# =========


# pin moteur
ENABLE = Pin(15, Pin.OUT)
M1 = Pin(16, Pin.OUT) # create output pin on GPIO0
M2 = Pin(17, Pin.OUT) # create output pin on GPIO0

DIR = Pin(27, Pin.OUT)   # create output pin on GPIO0
STEP = Pin(26, Pin.OUT)  # create output pin on GPIO0
STBY = Pin(25, Pin.OUT)  # create output pin on GPIO0

interrupteur = Pin(35, Pin.IN, Pin.PULL_UP)

# variables moteur
n = 0
delais = 0.005
step = 155
step_display = 25
position = 0
butee = 620

# Configuration de l'I2C
i2c = I2C(1, scl=Pin(22), sda=Pin(21), freq=100000)

# Définir la plage de tension de la batterie (dans cet exemple, de 3,0 à 4,2 volts)
min_voltage = 3.0
max_voltage = 4.2


# =========
# fonctions
# =========


def connect():
    '''
    connecte l'ESP NOW
    '''
    e = espnow.ESPNow()
    e.active(True)
    peer = b'\xb4\x8a\n\x8a/\xe4'
    e.add_peer(peer)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    return e, peer

def voltToPercent(voltage):
    '''
    convertit la tension de batterie en pourcentage
    '''
    return (voltage - min_voltage) / (max_voltage - min_voltage) * 100

def send_with_retry(data, max_retries=10):
    '''
    essai d'envoyer les données plusieurs fois pour éviter les erreurs de timeout
    '''
    # essai d'envoyer max {max_entries} fois
    for _ in range(max_retries):
        try:
            e.send(data)
            return True # si on a reussi à envoyer le message
        
        # si il y a un timeout on attent 100 ms
        except OSError as err:
            if err.errno == 116:
                time.sleep(0.1)
                continue
            raise
    return False # si on n'a pas reussi à envoyer le message

# Fonction pour lire la valeur de la batterie
def lire_tension_batterie():
    data = i2c.readfrom(78, 2)
    msb = data[0] << 6 
    lsb = data[1] >> 2
    return ((msb + lsb) * 5 / 1024)

def getButtonVal():
    data = i2c.readfrom(79, 2)
    msb = data[0] << 6
    lsb = data[1] >> 2
    return ((msb + lsb) * 5 / 1024)

def readAndSend(timer):
    '''
    lit les données et envoie le message
    '''
    try:
        global e, peer, step
        pos_moteur = int(position/butee*100)
        tension_msg = voltToPercent(lire_tension_batterie())
        print(getButtonVal())
        interrupteur_msg = "C" if not interrupteur.value() else "O"
        data = {
            'interrupteur_msg' : interrupteur_msg,
            'tension_msg' : tension_msg,
            'pos_moteur' : pos_moteur,
            'pas_moteur' : step_display
        }
        
        json_data = ujson.dumps(data)
        send_with_retry(json_data)
              
    except Exception as ex:
        print("Erreur lors de la lecture ou de l'envoi:", ex)

def init():
    M1.value(0)
    M2.value(0)
    STEP.value(0)
    STBY.value(0)
    
def pas(n, sens):
    '''
    permet d'avancer d'un nombre de pas
    sens :
        - 1 : rétracter
        - 0 : déployer
    '''
    global position
    DIR.value(sens)
    STBY.value(1)
    if sens:
        add = -1
    else:
        add = 1
    for _ in range(n):
        STEP.value(1)
        time.sleep(0.005)
        STEP.value(0)
        position += add
    STBY.value(0)
        
def positionZero():
    '''
    remet le moteur à la position rétractée
    '''
    global position
    print("Reset Position ...", end="\r")
    DIR.value(1)
    pas(butee, 1)
    position = 0
    print("Reset Position Ok.")

def resetBufferEspNow():
    while True:
        _, msg = e.recv(0)
        if msg is None:
            return

# =========
# main
# =========


# Remise à zéro du moteur
init()
positionZero()

# Connexion
print("Connexion ...", end="\r")
e, peer = connect()
print('Connexion Ok.')

print(i2c.scan())

timer = Timer(0)
timer.init(period=100, mode=Timer.PERIODIC, callback=readAndSend)

while True:
    _, msg = e.recv()
    if msg:
        print('reçu', msg)
        if(msg == b"1"):
            step = 6
            step_display = 1

        elif(msg == b"5"):
            step = 31
            step_display = 5

        elif(msg == b"10"):
            step = 62
            step_display = 10

        elif(msg == b"25"):
            step = 155
            step_display = 25
            
        elif(msg == b"max"):
            step = butee
            step_display = 100

        elif(msg == b'-'): # rentrer la tige
            if position > 0:
                if position - step < 0:
                    pas(position, 1)
                else:
                    pas(step, 1)
            
        elif(msg == b'+'): # sortir la tige
            if position < butee:
                if position + step > butee:
                    pas(butee - position, 0)
                else:
                    pas(step, 0)

        elif(msg == b'rs'): # remise à zero
            if position > 0:
                DIR.value(1)
                pas(position, 1)
        resetBufferEspNow()
