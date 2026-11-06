#!/usr/bin/env python3
import os
import struct
import math
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "./sd_out"
OUT_PATH = os.path.join(OUT_DIR, "cases.bin")

def pack_utf8(text: str, size: int) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) >= size:
        words = text.rstrip(".").split()
        while words and len(" ".join(words).encode("utf-8")) >= size:
            words.pop()
        s = " ".join(words) if words else ""
        raw = s.encode("utf-8")[:size - 1].decode("utf-8", errors="ignore").encode("utf-8")
    assert len(raw) <= size - 1
    return raw + b"\x00" * (size - len(raw))

def render_portrait(seed: int, style: dict) -> bytes:
    W, H = 120, 120
    img = Image.new("1", (W, H), 0)
    pix = img.load()
    draw = ImageDraw.Draw(img)

    # Background crosshatch booth wall
    for y in range(4, H - 4):
        for x in range(4, W - 4):
            if (x + y) % 6 == 0:
                pix[x, y] = 1
    # Height ruler ticks on right side
    for y in range(12, H - 12, 8):
        draw.line([(W - 14, y), (W - 5, y)], fill=1, width=1)

    # Shoulders / coat
    coat = style.get("coat", "suit")
    draw.polygon([(18, 118), (32, 84), (88, 84), (102, 118)], fill=1)
    if coat == "suit":
        draw.polygon([(48, 84), (60, 112), (72, 84)], fill=0) # shirt V
        draw.polygon([(58, 88), (62, 88), (63, 110), (57, 110)], fill=1) # tie
    elif coat == "uniform":
        draw.line([(32, 88), (88, 88)], fill=0, width=2)
        for bx in (46, 74):
            for by in (95, 106):
                draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=0)
    elif coat == "scarf":
        draw.rectangle([38, 80, 82, 94], fill=0, outline=1)
        for sx in range(40, 82, 4):
            draw.line([(sx, 80), (sx, 94)], fill=1)

    # Neck & Head silhouette
    draw.rectangle([50, 72, 70, 88], fill=0, outline=1)
    jw = style.get("jaw", 22)
    draw.ellipse([60 - jw, 24, 60 + jw, 78], fill=0, outline=1)
    draw.ellipse([59 - jw, 25, 61 + jw, 77], outline=1)

    # Ears
    draw.arc([60 - jw - 5, 44, 60 - jw + 2, 58], 90, 270, fill=1)
    draw.arc([60 + jw - 2, 44, 60 + jw + 5, 58], 270, 90, fill=1)

    # Hair / Hat
    hair = style.get("hair", "short")
    if hair == "short":
        draw.pieslice([60 - jw, 20, 60 + jw, 52], 180, 360, fill=1)
    elif hair == "parted":
        draw.pieslice([60 - jw, 20, 60 + jw, 50], 180, 360, fill=1)
        draw.line([(48, 22), (52, 36)], fill=0, width=2)
    elif hair == "bun":
        draw.ellipse([50, 10, 70, 26], fill=1)
        draw.pieslice([60 - jw, 20, 60 + jw, 50], 180, 360, fill=1)
    elif hair == "wavy":
        draw.pieslice([60 - jw - 4, 18, 60 + jw + 4, 58], 160, 20, fill=1)
        draw.ellipse([60 - jw + 2, 30, 60 + jw - 2, 76], fill=0, outline=1)
    elif hair == "fedora":
        draw.polygon([(34, 32), (44, 14), (76, 14), (86, 32)], fill=1)
        draw.rectangle([24, 30, 96, 35], fill=1)
        draw.line([(36, 28), (84, 28)], fill=0, width=2)
    elif hair == "beret":
        draw.pieslice([32, 14, 92, 42], 170, 355, fill=1)
    elif hair == "bald":
        draw.arc([46, 28, 74, 38], 180, 360, fill=1)

    # Eyebrows & Eyes
    eb = style.get("brow", 0)
    draw.line([(45, 43 + eb), (55, 43 - eb)], fill=1, width=2)
    draw.line([(65, 43 - eb), (75, 43 + eb)], fill=1, width=2)
    for ex in (50, 70):
        draw.ellipse([ex - 4, 46, ex + 4, 51], fill=0, outline=1)
        draw.ellipse([ex - 1, 47, ex + 1, 50], fill=1)

    # Glasses
    if style.get("glasses", False):
        draw.rectangle([42, 43, 57, 53], outline=1)
        draw.rectangle([63, 43, 78, 53], outline=1)
        draw.line([(57, 47), (63, 47)], fill=1, width=1)

    # Nose
    nose = style.get("nose", 0)
    draw.line([(60, 46), (58 - nose, 60), (63, 60)], fill=1, width=1)

    # Mustache / Beard / Mouth
    facial = style.get("facial", "none")
    if facial == "mustache":
        draw.polygon([(48, 66), (60, 63), (72, 66), (68, 69), (52, 69)], fill=1)
    elif facial == "beard":
        draw.pieslice([40, 56, 80, 82], 0, 180, fill=1)
        draw.rectangle([52, 64, 68, 68], fill=0)
    draw.line([(52, 67), (68, 67)], fill=1, width=1)

    # Border & Stamp Frame
    draw.rectangle([0, 0, W - 1, H - 1], outline=1)
    draw.rectangle([2, 2, W - 3, H - 3], outline=1)

    buf = bytearray(W * H // 8)
    for y in range(H):
        row_off = y * (W // 8)
        for x in range(W):
            if pix[x, y]:
                buf[row_off + (x >> 3)] |= (0x80 >> (x & 7))
    return bytes(buf)

CASES = [
    # 1
    {
        "date": "1964-11-02", "name": "MARCO VALENTI", "nat": "ITALIA", "city": "TORINO",
        "pass": "IT-482910", "exp": "1968-05-14", "approve": 1, "seal": 1, "wt": 74,
        "rulesEn": "DAY 1 DIRECTIVE: Current date is 1964-11-02. All travelers require a valid unexpired passport and an Entry Permit bearing the official Ministry Seal.",
        "rulesIt": "DIRETTIVA GIORNO 1: Data odierna 1964-11-02. Tutti i viaggiatori devono avere passaporto non scaduto e Permesso d'Ingresso col Sigillo Ufficiale.",
        "permitEn": "ENTRY PERMIT #8812 | Name: MARCO VALENTI | Purpose: Mechanical Engineer transit to Susa Valley | Valid through: 1965-01-01.",
        "permitIt": "PERMESSO #8812 | Nome: MARCO VALENTI | Scopo: Ingegnere meccanico in transito per la Val di Susa | Valido fino al: 1965-01-01.",
        "diagEn": "\"Good morning, Inspector. I am heading from Turin to inspect the hydroelectric turbines at Moncenisio. All papers are in order.\"",
        "diagIt": "\"Buongiorno, Ispettore. Vengo da Torino per ispezionare le turbine idroelettriche del Moncenisio. I documenti sono tutti in regola.\"",
        "auditEn": "All documents match. Passport IT-482910 is valid until 1968 and the Entry Permit carries the authentic Ministry Seal.",
        "auditIt": "Tutti i documenti coincidono. Il passaporto IT-482910 è valido fino al 1968 e il permesso reca il Sigillo Ufficiale autentico.",
        "style": {"coat": "suit", "hair": "parted", "glasses": True, "jaw": 21},
    },
    # 2
    {
        "date": "1964-11-02", "name": "CLARA BELLINI", "nat": "ITALIA", "city": "MILANO",
        "pass": "IT-109442", "exp": "1963-09-30", "approve": 0, "seal": 1, "wt": 58,
        "rulesEn": "DAY 1 DIRECTIVE: Current date is 1964-11-02. Reject any passport whose Expiry Date is earlier than 1964-11-02.",
        "rulesIt": "DIRETTIVA GIORNO 1: Data odierna 1964-11-02. Rifiutare qualsiasi passaporto con data di scadenza anteriore al 1964-11-02.",
        "permitEn": "ENTRY PERMIT #8819 | Name: CLARA BELLINI | Purpose: Trade exhibition in Chambery | Valid through: 1964-12-15.",
        "permitIt": "PERMESSO #8819 | Nome: CLARA BELLINI | Scopo: Fiera commerciale a Chambéry | Valido fino al: 1964-12-15.",
        "diagEn": "\"Please hurry, my train leaves in ten minutes! I renewed my permit last week in Milan.\"",
        "diagIt": "\"La prego di fare in fretta, il mio treno parte tra dieci minuti! Ho rinnovato il permesso la settimana scorsa a Milano.\"",
        "auditEn": "VIOLATION: Passport expired on 1963-09-30 (over one year before current date 1964-11-02). Entry must be DENIED.",
        "auditIt": "VIOLAZIONE: Il passaporto è scaduto il 1963-09-30 (oltre un anno prima della data odierna 1964-11-02). Ingresso RIFIUTATO.",
        "style": {"coat": "scarf", "hair": "bun", "jaw": 19},
    },
    # 3
    {
        "date": "1964-11-03", "name": "HENRI MOREAU", "nat": "FRANCE", "city": "LYON",
        "pass": "FR-773104", "exp": "1967-03-20", "approve": 0, "seal": 0, "wt": 81,
        "rulesEn": "DAY 2 DIRECTIVE: Current date 1964-11-03. Foreign nationals must carry an Entry Permit with an OFFICIAL SEAL. Forged or missing seals must be DENIED.",
        "rulesIt": "DIRETTIVA GIORNO 2: Data 1964-11-03. Gli stranieri devono avere un Permesso col SIGILLO UFFICIALE. I sigilli falsi o mancanti vanno RIFIUTATI.",
        "permitEn": "ENTRY PERMIT #9004 | Name: HENRI MOREAU | Purpose: Silk merchant delivery to Como | Notice: Temporary hand-inked stamp.",
        "permitIt": "PERMESSO #9004 | Nome: HENRI MOREAU | Scopo: Consegna seta a Como | Nota: Timbro provvisorio a mano.",
        "diagEn": "\"The consulate in Lyon ran out of embossed seals, so the clerk signed it by hand. Surely that is fine?\"",
        "diagIt": "\"Il consolato di Lione aveva finito i sigilli a secco, così l'impiegato ha firmato a mano. Non ci saranno problemi, vero?\"",
        "auditEn": "VIOLATION: Entry Permit lacks the Official Ministry Seal (FORGED/MISSING SEAL). Entry must be DENIED.",
        "auditIt": "VIOLAZIONE: Il Permesso d'Ingresso è privo del Sigillo Ufficiale del Ministero (SIGILLO FALSO/MANCANTE). Ingresso RIFIUTATO.",
        "style": {"coat": "fedora", "hair": "fedora", "facial": "mustache", "jaw": 22},
    },
    # 4
    {
        "date": "1964-11-03", "name": "ELENA ROSSI", "nat": "ITALIA", "city": "BOLOGNA",
        "pass": "IT-552019", "exp": "1966-11-12", "approve": 1, "seal": 1, "wt": 61,
        "rulesEn": "DAY 2 DIRECTIVE: Current date 1964-11-03. Check passport expiry, official seal, and verify that the name on the Permit matches the Passport.",
        "rulesIt": "DIRETTIVA GIORNO 2: Data 1964-11-03. Controllare scadenza, sigillo ufficiale e corrispondenza del nome tra Permesso e Passaporto.",
        "permitEn": "ENTRY PERMIT #9041 | Name: ELENA ROSSI | Purpose: University of Bologna philology exchange | Valid through: 1965-06-30.",
        "permitIt": "PERMESSO #9041 | Nome: ELENA ROSSI | Scopo: Scambio filologico Università di Bologna | Valido fino al: 1965-06-30.",
        "diagEn": "\"Good day. I am carrying rare Latin manuscripts from Bologna for the alpine monastery archive.\"",
        "diagIt": "\"Buongiorno. Porto con me rari manoscritti latini da Bologna per l'archivio del monastero alpino.\"",
        "auditEn": "Clean record. Valid Bologna passport, matching name ELENA ROSSI, and authentic Ministry Seal.",
        "auditIt": "Tutto regolare. Passaporto di Bologna valido, nome ELENA ROSSI corrispondente e Sigillo Ufficiale autentico.",
        "style": {"coat": "scarf", "hair": "wavy", "glasses": True, "jaw": 19},
    },
    # 5
    {
        "date": "1964-11-04", "name": "LUKAS WEBER", "nat": "HELVETIA", "city": "ZURICH",
        "pass": "CH-330192", "exp": "1969-01-10", "approve": 0, "seal": 1, "wt": 79,
        "rulesEn": "DAY 3 DIRECTIVE: Current date 1964-11-04. Ensure the Applicant Name and Passport Number on the Entry Permit match the Passport exactly.",
        "rulesIt": "DIRETTIVA GIORNO 3: Data 1964-11-04. Verificare che Nome e Numero di Passaporto sul Permesso coincidano esattamente col Passaporto.",
        "permitEn": "ENTRY PERMIT #9112 | Name: LUKAS WEBER | Passport Ref: CH-330999 | Purpose: Banking courier from Zurich.",
        "permitIt": "PERMESSO #9112 | Nome: LUKAS WEBER | Rif. Passaporto: CH-330999 | Scopo: Corriere bancario da Zurigo.",
        "diagEn": "\"Just a routine transit from Zurich to Milan. Everything was typed by our bank secretary this morning.\"",
        "diagIt": "\"Solo un transito di routine da Zurigo a Milano. Tutto è stato battuto a macchina dalla nostra segretaria stamattina.\"",
        "auditEn": "DISCREPANCY: Passport Number is CH-330192, but the Entry Permit lists CH-330999. Entry must be DENIED.",
        "auditIt": "DISCREPANZA: Il numero di passaporto è CH-330192, ma il Permesso indica CH-330999. Ingresso RIFIUTATO.",
        "style": {"coat": "suit", "hair": "bald", "glasses": True, "jaw": 23},
    },
    # 6
    {
        "date": "1964-11-04", "name": "SOFIA CONTI", "nat": "ITALIA", "city": "GENOVA",
        "pass": "IT-618204", "exp": "1967-08-22", "approve": 1, "seal": 1, "wt": 56,
        "rulesEn": "DAY 3 DIRECTIVE: Current date 1964-11-04. Verify passport validity, official seal, and exact document number match.",
        "rulesIt": "DIRETTIVA GIORNO 3: Data 1964-11-04. Verificare validità passaporto, sigillo ufficiale ed esatta corrispondenza del numero.",
        "permitEn": "ENTRY PERMIT #9150 | Name: SOFIA CONTI | Passport Ref: IT-618204 | Purpose: Maritime insurance auditor from Genoa.",
        "permitIt": "PERMESSO #9150 | Nome: SOFIA CONTI | Rif. Passaporto: IT-618204 | Scopo: Ispettrice assicurazioni marittime da Genova.",
        "diagEn": "\"Good afternoon. My office at Porto Antico sent my permit ahead by telegraph. Here is the stamped original.\"",
        "diagIt": "\"Buon pomeriggio. Il mio ufficio al Porto Antico ha anticipato il permesso via telegrafo. Ecco l'originale timbrato.\"",
        "auditEn": "Approved. Passport IT-618204 matches the permit reference, seal is authentic, and expiry is 1967.",
        "auditIt": "Approvato. Il passaporto IT-618204 coincide col permesso, il sigillo è autentico e scade nel 1967.",
        "style": {"coat": "suit", "hair": "bun", "jaw": 19},
    },
    # 7
    {
        "date": "1964-11-05", "name": "VIKTOR KOVACS", "nat": "OSTLAND", "city": "GRAZ",
        "pass": "OS-902114", "exp": "1966-04-01", "approve": 0, "seal": 1, "wt": 112,
        "rulesEn": "DAY 4 ALERT: Smuggling alert at the Alpine tunnel! Reject any traveler whose recorded booth scale weight exceeds 95 kg unless carrying a Freight Waiver.",
        "rulesIt": "ALLERTA GIORNO 4: Contrabbando al tunnel alpino! Rifiutare chiunque superi i 95 kg sulla bilancia senza Deroga Merci.",
        "permitEn": "ENTRY PERMIT #9208 | Name: VIKTOR KOVACS | Ref: OS-902114 | Purpose: Tourist visit (No Freight Waiver attached).",
        "permitIt": "PERMESSO #9208 | Nome: VIKTOR KOVACS | Rif: OS-902114 | Scopo: Visita turistica (Nessuna Deroga Merci allegata).",
        "diagEn": "\"Why does my coat clink when I walk? Oh, I simply wear very heavy wool lining for the mountain cold, Inspector!\"",
        "diagIt": "\"Perché il mio cappotto tintinna quando cammino? Oh, indosso solo una fodera di lana molto pesante per il freddo di montagna!\"",
        "auditEn": "SMUGGLING VIOLATION: Booth sensor reads 112 kg (above 95 kg limit) with no Freight Waiver; 18 Swiss watches found under coat!",
        "auditIt": "CONTRABBANDO: La bilancia segna 112 kg (oltre il limite di 95 kg) senza Deroga Merci; trovati 18 orologi svizzeri sotto il cappotto!",
        "style": {"coat": "uniform", "hair": "beret", "facial": "beard", "jaw": 24},
    },
    # 8
    {
        "date": "1964-11-05", "name": "GIORGIO FERRERO", "nat": "ITALIA", "city": "TORINO",
        "pass": "IT-741008", "exp": "1969-10-19", "approve": 1, "seal": 1, "wt": 76,
        "rulesEn": "DAY 4 ALERT: Current date 1964-11-05. Max personal weight 95 kg without Freight Waiver. Verify seal and passport number.",
        "rulesIt": "ALLERTA GIORNO 4: Data 1964-11-05. Peso massimo 95 kg senza Deroga Merci. Verificare sigillo e numero passaporto.",
        "permitEn": "ENTRY PERMIT #9233 | Name: GIORGIO FERRERO | Ref: IT-741008 | Purpose: Automotive test driver, Lingotto track.",
        "permitIt": "PERMESSO #9233 | Nome: GIORGIO FERRERO | Rif: IT-741008 | Scopo: Collaudatore automobilistico, pista del Lingotto.",
        "diagEn": "\"Testing the new coupe on the mountain hairpins today. Weight is 76 kilos, permit stamped in Turin.\"",
        "diagIt": "\"Oggi provo la nuova coupé sui tornanti di montagna. Peso 76 chili, permesso timbrato a Torino.\"",
        "auditEn": "All checks passed. Weight 76 kg is within the 95 kg threshold and all documents match.",
        "auditIt": "Controlli superati. Il peso di 76 kg rientra nel limite di 95 kg e tutti i documenti coincidono.",
        "style": {"coat": "suit", "hair": "short", "jaw": 21},
    },
    # 9
    {
        "date": "1964-11-06", "name": "JEAN-LUC DUPONT", "nat": "FRANCE", "city": "MARSEILLE",
        "pass": "FR-204881", "exp": "1967-07-14", "approve": 0, "seal": 1, "wt": 72,
        "rulesEn": "DAY 5 HEALTH DIRECTIVE: Due to port quarantine, passports issued in MARSEILLE are temporarily suspended unless accompanied by a Sanitary Certificate.",
        "rulesIt": "DIRETTIVA SANITARIA GIORNO 5: Per quarantena portuale, i passaporti emessi a MARSEILLE sono sospesi senza Certificato Sanitario.",
        "permitEn": "ENTRY PERMIT #9301 | Name: JEAN-LUC DUPONT | Ref: FR-204881 | Attachments: Standard Transit Permit only (No Sanitary Certificate).",
        "permitIt": "PERMESSO #9301 | Nome: JEAN-LUC DUPONT | Rif: FR-204881 | Allegati: Solo Permesso di Transito (Nessun Certificato Sanitario).",
        "diagEn": "\"I haven't been near the Marseille docks in months! You can't turn me back over a missing health slip!\"",
        "diagIt": "\"Non mi avvicino al porto di Marsiglia da mesi! Non può respingermi per un modulo sanitario mancante!\"",
        "auditEn": "QUARANTINE VIOLATION: Passport issued in MARSEILLE without mandatory Sanitary Certificate. Entry must be DENIED.",
        "auditIt": "VIOLAZIONE QUARANTENA: Passaporto emesso a MARSEILLE privo del Certificato Sanitario obbligatorio. Ingresso RIFIUTATO.",
        "style": {"coat": "scarf", "hair": "parted", "facial": "mustache", "jaw": 21},
    },
    # 10
    {
        "date": "1964-11-06", "name": "CAMILLE LAURENT", "nat": "FRANCE", "city": "PARIS",
        "pass": "FR-883412", "exp": "1968-12-01", "approve": 1, "seal": 1, "wt": 54,
        "rulesEn": "DAY 5 HEALTH DIRECTIVE: Passports issued in MARSEILLE require a Sanitary Certificate. Other French issuing cities (PARIS, LYON) are exempt.",
        "rulesIt": "DIRETTIVA SANITARIA GIORNO 5: I passaporti emessi a MARSEILLE richiedono Certificato Sanitario. PARIS e LYON sono esenti.",
        "permitEn": "ENTRY PERMIT #9318 | Name: CAMILLE LAURENT | Ref: FR-883412 | Purpose: Architectural photographer visiting Ivrea.",
        "permitIt": "PERMESSO #9318 | Nome: CAMILLE LAURENT | Rif: FR-883412 | Scopo: Fotografa d'architettura in visita a Ivrea.",
        "diagEn": "\"Good morning. My passport was issued in Paris, and I am photographing the Olivetti buildings in Ivrea.\"",
        "diagIt": "\"Buongiorno. Il mio passaporto è stato emesso a Parigi, vado a fotografare gli edifici Olivetti a Ivrea.\"",
        "auditEn": "Approved. Passport issued in PARIS (exempt from Marseille quarantine), valid through 1968 with official seal.",
        "auditIt": "Approvato. Passaporto emesso a PARIS (esente dalla quarantena di Marsiglia), valido fino al 1968 con sigillo ufficiale.",
        "style": {"coat": "scarf", "hair": "wavy", "jaw": 19},
    },
    # 11
    {
        "date": "1964-11-07", "name": "MATTEO GRECO", "nat": "ITALIA", "city": "NAPOLI",
        "pass": "IT-309115", "exp": "1966-02-28", "approve": 0, "seal": 1, "wt": 70,
        "rulesEn": "DAY 6 DIRECTIVE: Verify that the Applicant Name on the Entry Permit matches the Passport holder's name letter-for-letter.",
        "rulesIt": "DIRETTIVA GIORNO 6: Verificare che il Nome sul Permesso coincida lettera per lettera con quello sul Passaporto.",
        "permitEn": "ENTRY PERMIT #9402 | Name: MASSIMO GRECO | Ref: IT-309115 | Purpose: Railway signalling technician.",
        "permitIt": "PERMESSO #9402 | Nome: MASSIMO GRECO | Rif: IT-309115 | Scopo: Tecnico segnalamento ferroviario.",
        "diagEn": "\"Matteo, Massimo—everyone in my family starts with M! It belongs to me, look at the photo!\"",
        "diagIt": "\"Matteo, Massimo—nella mia famiglia iniziamo tutti con la M! È mio, guardi la foto!\"",
        "auditEn": "IDENTITY MISMATCH: Passport says MATTEO GRECO, but Entry Permit was issued to MASSIMO GRECO. Entry DENIED.",
        "auditIt": "IDENTITÀ NON CORRISPONDENTE: Il passaporto dice MATTEO GRECO, ma il Permesso è intestato a MASSIMO GRECO. RIFIUTATO.",
        "style": {"coat": "uniform", "hair": "short", "facial": "mustache", "jaw": 22},
    },
    # 12
    {
        "date": "1964-11-07", "name": "BEATRICE SARTI", "nat": "ITALIA", "city": "FIRENZE",
        "pass": "IT-994120", "exp": "1967-09-15", "approve": 1, "seal": 1, "wt": 57,
        "rulesEn": "DAY 6 DIRECTIVE: Current date 1964-11-07. Verify exact name match, valid dates, and authentic Ministry Seal.",
        "rulesIt": "DIRETTIVA GIORNO 6: Data 1964-11-07. Verificare esatta corrispondenza del nome, date valide e Sigillo Ufficiale.",
        "permitEn": "ENTRY PERMIT #9440 | Name: BEATRICE SARTI | Ref: IT-994120 | Purpose: Art restorer from Uffizi Gallery.",
        "permitIt": "PERMESSO #9440 | Nome: BEATRICE SARTI | Rif: IT-994120 | Scopo: Restauratrice d'arte dalla Galleria degli Uffizi.",
        "diagEn": "\"I am travelling to restore a 15th-century altarpiece in the valley cathedral. All documents are signed.\"",
        "diagIt": "\"Viaggio per restaurare una pala d'altare del Quattrocento nella cattedrale della valle. Tutti i documenti sono firmati.\"",
        "auditEn": "Approved. Name BEATRICE SARTI, passport IT-994120, expiry 1967-09-15, and official seal all match.",
        "auditIt": "Approvato. Nome BEATRICE SARTI, passaporto IT-994120, scadenza 1967-09-15 e sigillo ufficiale corrispondono.",
        "style": {"coat": "suit", "hair": "bun", "glasses": True, "jaw": 19},
    },
    # 13
    {
        "date": "1964-11-08", "name": "DIETER KRAUSE", "nat": "GERMANIA", "city": "MUNICH",
        "pass": "DE-410299", "exp": "1965-12-31", "approve": 0, "seal": 1, "wt": 83,
        "rulesEn": "DAY 7 DIRECTIVE: Current date is 1964-11-08. Check that BOTH the Passport AND the Entry Permit have not expired before 1964-11-08.",
        "rulesIt": "DIRETTIVA GIORNO 7: Data odierna 1964-11-08. Verificare che NÉ il Passaporto NÉ il Permesso siano scaduti prima del 1964-11-08.",
        "permitEn": "ENTRY PERMIT #8102 | Name: DIETER KRAUSE | Ref: DE-410299 | Valid through: 1964-10-31 (EXPIRED).",
        "permitIt": "PERMESSO #8102 | Nome: DIETER KRAUSE | Rif: DE-410299 | Valido fino al: 1964-10-31 (SCADUTO).",
        "diagEn": "\"Snow blocked the Brenner pass last week, so I arrived eight days late. My passport is still valid until 1965!\"",
        "diagIt": "\"La neve ha bloccato il Brennero la settimana scorsa, sono arrivato con otto giorni di ritardo. Il passaporto vale fino al 1965!\"",
        "auditEn": "EXPIRED PERMIT: Although passport is valid, Entry Permit #8102 expired on 1964-10-31 (before 1964-11-08). Entry DENIED.",
        "auditIt": "PERMESSO SCADUTO: Sebbene il passaporto sia valido, il Permesso #8102 è scaduto il 1964-10-31. Ingresso RIFIUTATO.",
        "style": {"coat": "fedora", "hair": "fedora", "glasses": True, "jaw": 22},
    },
    # 14
    {
        "date": "1964-11-08", "name": "ALESSANDRO RIVA", "nat": "ITALIA", "city": "VENEZIA",
        "pass": "IT-820331", "exp": "1968-03-15", "approve": 1, "seal": 1, "wt": 68,
        "rulesEn": "DAY 7 DIRECTIVE: Current date 1964-11-08. Both Passport and Entry Permit must be valid on or after 1964-11-08.",
        "rulesIt": "DIRETTIVA GIORNO 7: Data 1964-11-08. Sia il Passaporto sia il Permesso devono essere validi in data 1964-11-08 o successiva.",
        "permitEn": "ENTRY PERMIT #9510 | Name: ALESSANDRO RIVA | Ref: IT-820331 | Valid through: 1965-03-15 | Purpose: Glass optics delivery.",
        "permitIt": "PERMESSO #9510 | Nome: ALESSANDRO RIVA | Rif: IT-820331 | Valido fino al: 1965-03-15 | Scopo: Consegna ottiche in vetro.",
        "diagEn": "\"Bringing precision Murano lenses for the mountain observatory. Both my passport and permit are valid through next year.\"",
        "diagIt": "\"Porto lenti di precisione di Murano per l'osservatorio alpino. Sia il passaporto sia il permesso valgono fino all'anno prossimo.\"",
        "auditEn": "Approved. Both passport (1968) and permit (1965) are valid, seal is official, weight 68 kg is normal.",
        "auditIt": "Approvato. Sia il passaporto (1968) sia il permesso (1965) sono validi, sigillo ufficiale, peso 68 kg regolare.",
        "style": {"coat": "suit", "hair": "parted", "jaw": 20},
    },
    # 15
    {
        "date": "1964-11-09", "name": "MARTIN NOVAK", "nat": "BOHEMIA", "city": "PRAHA",
        "pass": "CS-501920", "exp": "1966-06-01", "approve": 0, "seal": 1, "wt": 77,
        "rulesEn": "DAY 8 SECURITY BULLETIN: Watchlist alert! Arrest and DENY entry to anyone carrying passport number CS-501920 (stolen diplomatic blank).",
        "rulesIt": "BOLLETTINO SICUREZZA GIORNO 8: Lista nera! Bloccare e RIFIUTARE chiunque presenti il passaporto n. CS-501920 (modulo rubato).",
        "permitEn": "ENTRY PERMIT #9604 | Name: MARTIN NOVAK | Ref: CS-501920 | Valid through: 1965-01-15 | Purpose: Chess tournament.",
        "permitIt": "PERMESSO #9604 | Nome: MARTIN NOVAK | Rif: CS-501920 | Valido fino al: 1965-01-15 | Scopo: Torneo di scacchi.",
        "diagEn": "\"I am only here for the international chess tournament in Turin. My papers have the official seal!\"",
        "diagIt": "\"Sono qui solo per il torneo internazionale di scacchi a Torino. I miei documenti hanno il sigillo ufficiale!\"",
        "auditEn": "WATCHLIST HIT: Passport CS-501920 is flagged on today's Security Bulletin as a stolen blank. Entry DENIED.",
        "auditIt": "SEGNALAZIONE LISTA NERA: Il passaporto CS-501920 è segnalato nel Bollettino di oggi come documento rubato. RIFIUTATO.",
        "style": {"coat": "suit", "hair": "bald", "facial": "beard", "jaw": 23},
    },
    # 16
    {
        "date": "1964-11-09", "name": "LUCIA MORETTI", "nat": "ITALIA", "city": "ROMA",
        "pass": "IT-219884", "exp": "1969-04-30", "approve": 1, "seal": 1, "wt": 59,
        "rulesEn": "DAY 8 SECURITY BULLETIN: Current date 1964-11-09. Deny blacklisted passport CS-501920. Approve valid diplomats and citizens.",
        "rulesIt": "BOLLETTINO GIORNO 8: Data 1964-11-09. Rifiutare il passaporto CS-501920. Approvare diplomatici e cittadini regolari.",
        "permitEn": "ENTRY PERMIT #9622 | Name: LUCIA MORETTI | Ref: IT-219884 | Valid through: 1965-05-01 | Purpose: Ministry inspector from Rome.",
        "permitIt": "PERMESSO #9622 | Nome: LUCIA MORETTI | Rif: IT-219884 | Valido fino al: 1965-05-01 | Scopo: Ispettrice ministeriale da Roma.",
        "diagEn": "\"Ministry of Foreign Affairs, Rome. I am conducting the quarterly inspection of alpine border posts.\"",
        "diagIt": "\"Ministero degli Affari Esteri, Roma. Sto svolgendo l'ispezione trimestrale dei valichi di frontiera alpini.\"",
        "auditEn": "Approved. Authentic Ministry credentials from Rome, valid passport IT-219884 and official seal.",
        "auditIt": "Approvato. Credenziali ministeriali autentiche da Roma, passaporto IT-219884 valido e sigillo ufficiale.",
        "style": {"coat": "uniform", "hair": "wavy", "jaw": 19},
    },
    # 17
    {
        "date": "1964-11-10", "name": "PIERRE GARNIER", "nat": "FRANCE", "city": "GRENOBLE",
        "pass": "FR-662011", "exp": "1967-11-10", "approve": 1, "seal": 1, "wt": 99,
        "rulesEn": "DAY 9 DIRECTIVE: Travelers over 95 kg must be DENIED UNLESS their Entry Permit explicitly includes a 'FREIGHT WAIVER: APPROVED' clause.",
        "rulesIt": "DIRETTIVA GIORNO 9: Chi supera i 95 kg va RIFIUTATO A MENO CHE il Permesso includa espressamente 'DEROGA MERCI: APPROVATA'.",
        "permitEn": "ENTRY PERMIT #9701 | Name: PIERRE GARNIER | Ref: FR-662011 | Note: FREIGHT WAIVER: APPROVED (25 kg mountain rescue winch).",
        "permitIt": "PERMESSO #9701 | Nome: PIERRE GARNIER | Rif: FR-662011 | Nota: DEROGA MERCI: APPROVATA (verricello soccorso alpino 25 kg).",
        "diagEn": "\"I am carrying a steel rescue cable winch for the Alpine mountain guides. The freight waiver is printed on my permit.\"",
        "diagIt": "\"Trasporto un verricello d'acciaio per le guide del soccorso alpino. La deroga merci è stampata sul mio permesso.\"",
        "auditEn": "Approved! Although weight is 99 kg, Permit #9701 explicitly includes 'FREIGHT WAIVER: APPROVED'.",
        "auditIt": "Approvato! Sebbene il peso sia 99 kg, il Permesso #9701 include espressamente 'DEROGA MERCI: APPROVATA'.",
        "style": {"coat": "uniform", "hair": "beret", "facial": "beard", "jaw": 23},
    },
    # 18
    {
        "date": "1964-11-10", "name": "CARLO BIANCHI", "nat": "ITALIA", "city": "MILANO",
        "pass": "IT-400129", "exp": "1966-08-15", "approve": 0, "seal": 0, "wt": 73,
        "rulesEn": "DAY 9 DIRECTIVE: Current date 1964-11-10. Even domestic citizens require an Official Seal on their border transit permit.",
        "rulesIt": "DIRETTIVA GIORNO 9: Data 1964-11-10. Anche i cittadini nazionali devono avere il Sigillo Ufficiale sul permesso di transito.",
        "permitEn": "ENTRY PERMIT #9715 | Name: CARLO BIANCHI | Ref: IT-400129 | Valid through: 1965-02-01 | Unstamped carbon copy.",
        "permitIt": "PERMESSO #9715 | Nome: CARLO BIANCHI | Rif: IT-400129 | Valido fino al: 1965-02-01 | Copia carbone senza timbro.",
        "diagEn": "\"Come on, paesano! I left the stamped original on my desk in Milan, this carbon copy is exactly the same!\"",
        "diagIt": "\"Ma dai, paesano! Ho lasciato l'originale timbrato sulla scrivania a Milano, questa copia carbone è identica!\"",
        "auditEn": "VIOLATION: Unstamped carbon copy (FORGED/MISSING SEAL). Official seal is mandatory for all travelers.",
        "auditIt": "VIOLAZIONE: Copia carbone priva di timbro (SIGILLO FALSO/MANCANTE). Il sigillo ufficiale è obbligatorio per tutti.",
        "style": {"coat": "suit", "hair": "short", "facial": "mustache", "jaw": 21},
    },
    # 19
    {
        "date": "1964-11-11", "name": "ANNA LINDQVIST", "nat": "SVEZIA", "city": "STOCKHOLM",
        "pass": "SE-118044", "exp": "1964-11-01", "approve": 0, "seal": 1, "wt": 60,
        "rulesEn": "DAY 10 FINAL AUDIT: Current date is 1964-11-11. Zero tolerance on expired passports, missing seals, or mismatched numbers.",
        "rulesIt": "ISPEZIONE FINALE GIORNO 10: Data odierna 1964-11-11. Tolleranza zero su passaporti scaduti, sigilli mancanti o numeri errati.",
        "permitEn": "ENTRY PERMIT #9804 | Name: ANNA LINDQVIST | Ref: SE-118044 | Valid through: 1965-01-20 | Purpose: Botanist.",
        "permitIt": "PERMESSO #9804 | Nome: ANNA LINDQVIST | Rif: SE-118044 | Valido fino al: 1965-01-20 | Scopo: Botanica.",
        "diagEn": "\"Oh dear, did my passport expire ten days ago on November 1st? My permit is still valid until January!\"",
        "diagIt": "\"Oh cielo, il mio passaporto è scaduto dieci giorni fa, il primo novembre? Ma il mio permesso vale fino a gennaio!\"",
        "auditEn": "VIOLATION: Passport SE-118044 expired on 1964-11-01 (ten days before current date 1964-11-11). Entry DENIED.",
        "auditIt": "VIOLAZIONE: Il passaporto SE-118044 è scaduto il 1964-11-01 (dieci giorni prima della data odierna 1964-11-11). RIFIUTATO.",
        "style": {"coat": "scarf", "hair": "bun", "glasses": True, "jaw": 19},
    },
    # 20
    {
        "date": "1964-11-11", "name": "LORENZO COSTA", "nat": "ITALIA", "city": "TORINO",
        "pass": "IT-990001", "exp": "1970-01-01", "approve": 1, "seal": 1, "wt": 75,
        "rulesEn": "DAY 10 FINAL AUDIT: Current date 1964-11-11. Verify all fields: Passport expiry, Permit validity, Official Seal, Name/Number match, and Weight.",
        "rulesIt": "ISPEZIONE FINALE GIORNO 10: Data 1964-11-11. Verificare tutti i campi: scadenza, validità permesso, sigillo, nome/numero e peso.",
        "permitEn": "ENTRY PERMIT #9899 | Name: LORENZO COSTA | Ref: IT-990001 | Valid through: 1966-01-01 | Chief Diplomatic Courier, Turin.",
        "permitIt": "PERMESSO #9899 | Nome: LORENZO COSTA | Rif: IT-990001 | Valido fino al: 1966-01-01 | Corriere Diplomatico Capo, Torino.",
        "diagEn": "\"Inspector, this is the final dispatch pouch of the autumn session. Your border post has maintained an exemplary record.\"",
        "diagIt": "\"Ispettore, questa è l'ultima valigia diplomatica della sessione autunnale. Il suo valico ha mantenuto un servizio esemplare.\"",
        "auditEn": "Exemplary inspection! All credentials for Chief Courier LORENZO COSTA (IT-990001) are in perfect order.",
        "auditIt": "Ispezione esemplare! Tutte le credenziali del Corriere Capo LORENZO COSTA (IT-990001) sono in perfetto ordine.",
        "style": {"coat": "uniform", "hair": "parted", "glasses": True, "jaw": 21},
    },
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    assert len(CASES) == 20
    out = bytearray()
    out += struct.pack("<8sHHI", b"CNFR0001", len(CASES), 0, 0)
    assert len(out) == 16

    for idx, c in enumerate(CASES):
        rec = bytearray()
        rec += pack_utf8(c["date"], 16)
        rec += pack_utf8(c["name"], 36)
        rec += pack_utf8(c["nat"], 24)
        rec += pack_utf8(c["city"], 24)
        rec += pack_utf8(c["pass"], 16)
        rec += pack_utf8(c["exp"], 16)
        rec += struct.pack("<BBH", c["approve"], c["seal"], c["wt"])
        rec += pack_utf8(c["rulesEn"], 220)
        rec += pack_utf8(c["rulesIt"], 220)
        rec += pack_utf8(c["permitEn"], 160)
        rec += pack_utf8(c["permitIt"], 160)
        rec += pack_utf8(c["diagEn"], 180)
        rec += pack_utf8(c["diagIt"], 180)
        rec += pack_utf8(c["auditEn"], 180)
        rec += pack_utf8(c["auditIt"], 180)
        bmp = render_portrait(idx, c["style"])
        assert len(bmp) == 1800
        rec += bmp
        assert len(rec) == 3416, f"Case {idx} size {len(rec)}"
        out += rec

    assert len(out) == 16 + 20 * 3416
    with open(OUT_PATH, "wb") as f:
        f.write(out)
    print(f"Wrote {OUT_PATH}: {len(out)} bytes ({len(CASES)} cases)")

if __name__ == "__main__":
    main()
