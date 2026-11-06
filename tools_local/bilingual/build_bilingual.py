#!/usr/bin/env python3
import os
import struct

OUT_DIR = "./sd_out"
OUT_PATH = os.path.join(OUT_DIR, "texts.bin")

def pack_utf8(text: str, size: int) -> bytes:
    raw = text.encode("utf-8")
    if len(raw) >= size:
        truncated = raw[:size - 1]
        while truncated and (truncated[-1] & 0xC0) == 0x80:
            truncated = truncated[:-1]
        if truncated and truncated[-1] >= 0xC0:
            truncated = truncated[:-1]
        raw = truncated
    return raw + b"\x00" * (size - len(raw))

TEXTS = [
    # 1. Un Caffè a Torino (A1)
    {
        "title": "1. Un Caffè a Torino (A1)",
        "subtitle": "A1 | Torino'da Sabah Kahvesi ve Günlük Diyalog",
        "level": "A1",
        "segments": [
            (
                "È una mattina fresca d'autunno a Torino. Cammino sotto i lunghi portici di Via Po verso Piazza Vittorio.",
                "Torino'da serin bir sonbahar sabahı. Via Po'nun uzun kemerli kaldırımları altında Piazza Vittorio'ya doğru yürüyorum.",
                "It is a cool autumn morning in Turin. I walk under the long arcades of Via Po toward Piazza Vittorio.",
                "fresco = serin/taze | camminare = yürümek | il portico = kemerli kaldırım",
                "sotto i portici",
                "kemerlerin altında / arcades"
            ),
            (
                "Entro in un piccolo bar storico all'angolo. L'odore del caffè appena macinato e dei cornetti caldi riempie l'aria.",
                "Köşedeki küçük tarihi bir bara giriyorum. Taze çekilmiş kahve ve sıcak kruvasan kokusu havayı dolduruyor.",
                "I enter a small historic cafe on the corner. The smell of freshly ground coffee and warm croissants fills the air.",
                "all'angolo = köşede | appena = henüz/yeni | riempire = doldurmak",
                "appena macinato",
                "taze çekilmiş / freshly ground"
            ),
            (
                "«Buongiorno! Cosa Le preparo?» mi chiede il barista con un sorriso gentile mentre pulisce il bancone.",
                "«Günaydın! Size ne hazırlayayım?» diye soruyor barmen nazik bir gülümsemeyle tezgâhı silerken.",
                "\"Good morning! What can I make for you?\" asks the barista with a kind smile while wiping the counter.",
                "preparare = hazırlamak | chiedere = sormak | il bancone = bar tezgâhı",
                "Cosa Le preparo?",
                "Size ne hazırlayayım? (resmî)"
            ),
            (
                "«Buongiorno! Vorrei un caffè macchiato caldo e una brioche alla crema, per favore» rispondo io.",
                "«Günaydın! Sıcak bir macchiato kahve ve kremalı bir çörek istiyorum lütfen» diye cevap veriyorum.",
                "\"Good morning! I would like a hot macchiato and a cream brioche, please,\" I reply.",
                "vorrei = isterdim/istiyorum | caldo = sıcak | rispondere = cevap vermek",
                "Vorrei un caffè",
                "Bir kahve istiyorum / I'd like"
            ),
            (
                "In Italia, al mattino si beve il caffè in piedi al bancone. È un rituale veloce ma pieno di calore umano.",
                "İtalya'da sabahları kahve tezgâhta ayakta içilir. Hızlı ama insan sıcaklığıyla dolu bir ritüeldir.",
                "In Italy, in the morning coffee is drunk standing at the counter. It is a quick ritual full of human warmth.",
                "al mattino = sabahleyin | in piedi = ayakta | pieno di = ... ile dolu",
                "bere in piedi",
                "ayakta içmek / drink standing"
            ),
            (
                "Accanto a me, un signore anziano legge il giornale «La Stampa» e commenta il tempo con il barista.",
                "Yanımda yaşlı bir beyefendi «La Stampa» gazetesini okuyor ve barmenle hava durumu hakkında sohbet ediyor.",
                "Next to me, an elderly gentleman reads the newspaper 'La Stampa' and comments on the weather with the barista.",
                "accanto a = yanında | anziano = yaşlı | il tempo = hava/zaman",
                "accanto a me",
                "yanımda / next to me"
            ),
            (
                "«Oggi sembra che piova verso sera» dice il signore. «Meglio prendere l'ombrello prima di uscire!»",
                "«Bugün akşama doğru yağmur yağacak gibi görünüyor» diyor beyefendi. «Çıkmadan önce şemsiyeyi almak daha iyi!»",
                "\"Today it looks like it might rain toward evening,\" says the gentleman. \"Better take an umbrella before going out!\"",
                "sembrare = görünmek | verso sera = akşama doğru | prima di = -meden önce",
                "prima di uscire",
                "çıkmadan önce / before leaving"
            ),
            (
                "Il barista mi serve il caffè con un bicchierino d'acqua frizzante. Bevo prima l'acqua per pulire il palato.",
                "Barmen bana kahveyi küçük bir bardak maden suyuyla servis ediyor. Damağımı temizlemek için önce suyu içiyorum.",
                "The barista serves me the coffee with a small glass of sparkling water. I drink the water first to cleanse my palate.",
                "servire = servis etmek | frizzante = gazlı/köpüklü | il palato = damak",
                "acqua frizzante",
                "maden suyu / sparkling water"
            ),
            (
                "«Sei studente al Politecnico?» mi chiede il signore vedendo il mio zaino pieno di quaderni.",
                "«Politecnico'da öğrenci misin?» diye soruyor beyefendi defterlerle dolu sırt çantamı görünce.",
                "\"Are you a student at the Polytechnic?\" the gentleman asks me, seeing my backpack full of notebooks.",
                "lo zaino = sırt çantası | il quaderno = defter | vedere = görmek",
                "lo zaino",
                "sırt çantası / backpack"
            ),
            (
                "«Sì, studio ingegneria meccanica. Sono arrivato a Torino da poche settimane» spiego con entusiasmo.",
                "«Evet, makine mühendisliği okuyorum. Torino'ya birkaç hafta önce geldim» diye heyecanla açıklıyorum.",
                "\"Yes, I study mechanical engineering. I arrived in Turin a few weeks ago,\" I explain with enthusiasm.",
                "sono arrivato = vardım/geldim | da poche = birkaç ...-den beri | spiegare = açıklamak",
                "da poche settimane",
                "birkaç haftadır / few weeks"
            ),
            (
                "«Complimenti! Torino è una città tranquilla, elegante e perfetta per studiare» mi dice sorridendo.",
                "«Tebrikler! Torino sakin, zarif ve ders çalışmak için mükemmel bir şehirdir» diyor bana gülümseyerek.",
                "\"Congratulations! Turin is a calm, elegant city, perfect for studying,\" he tells me smiling.",
                "complimenti = tebrikler | tranquillo = sakin | per studiare = okumak için",
                "una città tranquilla",
                "sakin bir şehir / quiet city"
            ),
            (
                "Finisco la mia brioche e vado alla cassa. «Quanto viene in tutto?» chiedo alla cassiera.",
                "Çöreğimi bitirip kasaya gidiyorum. «Toplam ne kadar tutuyor?» diye kasiyere soruyorum.",
                "I finish my brioche and go to the register. \"How much is it in total?\" I ask the cashier.",
                "finire = bitirmek | la cassa = kasa | quanto viene = ne kadar tutuyor",
                "Quanto viene in tutto?",
                "Toplam ne kadar? / How much?"
            ),
            (
                "«Sono due euro e settanta centesimi. Paga in contanti o con la carta?» «Con la carta, grazie.»",
                "«İki avro yetmiş sent. Nakit mi yoksa kartla mı ödüyorsunuz?» «Kartla, teşekkürler.»",
                "\"It is two euros and seventy cents. Are you paying in cash or by card?\" \"By card, thank you.\"",
                "in contanti = nakit olarak | la carta = kart | il centesimo = sent/kuruş",
                "pagare in contanti",
                "nakit ödemek / pay in cash"
            ),
            (
                "Esco dal bar pieno di energia. Le montagne delle Alpi brillano in lontananza sotto il sole del mattino.",
                "Enerji dolu bir şekilde bardan çıkıyorum. Alp dağları sabah güneşinin altında uzakta parlıyor.",
                "I leave the cafe full of energy. The Alps shine in the distance under the morning sun.",
                "uscire (esco) = çıkmak | brillare = parlamak | in lontananza = uzakta",
                "in lontananza",
                "uzakta / in the distance"
            ),
        ],
    },
    # 2. Il Mercato di Porta Palazzo (A1)
    {
        "title": "2. Il Mercato di Porta Palazzo (A1)",
        "subtitle": "A1 | Porta Palazzo Pazarında Alışveriş",
        "level": "A1",
        "segments": [
            (
                "Il sabato mattina vado sempre a Porta Palazzo, il mercato all'aperto più grande d'Europa.",
                "Cumartesi sabahları her zaman Avrupa'nın en büyük açık hava pazarı olan Porta Palazzo'ya giderim.",
                "On Saturday mornings I always go to Porta Palazzo, the largest open-air market in Europe.",
                "sempre = her zaman | all'aperto = açık havada | più grande = en büyük",
                "il mercato all'aperto",
                "açık hava pazarı / open market"
            ),
            (
                "La piazza è divisa in quattro zone: i banchi dei contadini, la frutta, il mercato del pesce e i formaggi.",
                "Meydan dört bölgeye ayrılmıştır: çiftçi tezgâhları, meyve-sebze, balık pazarı ve peynirler.",
                "The square is divided into four areas: the farmers' stalls, fruit, the fish market, and cheeses.",
                "diviso = bölünmüş | il banco = pazar tezgâhı | il contadino = çiftçi",
                "il banco del mercato",
                "pazar tezgâhı / market stall"
            ),
            (
                "I venditori gridano i prezzi a voce alta: «Pomodori dolci di Sicilia! Due euro al chilo!»",
                "Satıcılar fiyatları yüksek sesle bağırıyor: «Tatlı Sicilya domatesleri! Kilosu iki avro!»",
                "The vendors shout the prices out loud: \"Sweet tomatoes from Sicily! Two euros a kilo!\"",
                "il venditore = satıcı | gridare = bağırmak | a voce alta = yüksek sesle",
                "a voce alta",
                "yüksek sesle / out loud"
            ),
            (
                "Mi fermo davanti al banco di una signora piemontese che vende verdure fresche del suo orto.",
                "Kendi bahçesinden taze sebzeler satan Piyemonteli bir hanımın tezgâhının önünde duruyorum.",
                "I stop in front of the stall of a Piedmontese lady who sells fresh vegetables from her garden.",
                "fermarsi = durmak | davanti a = önünde | l'orto = sebze bahçesi",
                "mi fermo davanti",
                "önünde duruyorum / I stop at"
            ),
            (
                "«Buongiorno signora! Posso avere mezzo chilo di zucchine e un mazzo di basilico fresco?»",
                "«Günaydın hanımefendi! Yarım kilo kabak ve bir demet taze fesleğen alabilir miyim?»",
                "\"Good morning madam! Can I have half a kilo of zucchini and a bunch of fresh basil?\"",
                "mezzo chilo = yarım kilo | la zucchina = kabak | il mazzo = demet",
                "mezzo chilo di...",
                "yarım kilo ... / half a kilo"
            ),
            (
                "«Certo caro! Guarda che belle queste zucchine, le ho raccolte stamattina all'alba.»",
                "«Tabii canım! Bak bu kabaklar ne kadar güzel, onları bu sabah şafakta topladım.»",
                "\"Of course dear! Look how nice these zucchini are, I picked them this morning at dawn.\"",
                "raccogliere (raccolto) = toplamak | stamattina = bu sabah | l'alba = şafak",
                "stamattina all'alba",
                "bu sabah şafakta / at dawn"
            ),
            (
                "«Prendo anche quattro mele rosse e un grappolo d'uva bianca. È dolce l'uva?» chiedo curioso.",
                "«Dört kırmızı elma ve bir salkım beyaz üzüm de alıyorum. Üzüm tatlı mı?» diye merakla soruyorum.",
                "\"I'll also take four red apples and a bunch of white grapes. Are the grapes sweet?\" I ask curiously.",
                "prendere = almak | il grappolo = salkım | l'uva = üzüm",
                "un grappolo d'uva",
                "bir salkım üzüm / bunch grapes"
            ),
            (
                "«Assaggia pure un chicco! È dolcissima, sembra miele» risponde la signora porgendomi un acino.",
                "«Bir tanesinin tadına bak! Çok tatlı, bal gibi» diye cevap veriyor hanım bana bir üzüm tanesi uzatarak.",
                "\"Go ahead and taste one! It is very sweet, like honey,\" replies the lady handing me a grape.",
                "assaggiare = tadına bakmak | il miele = bal | porgere = uzatmak",
                "Assaggia pure!",
                "Tadına bak lütfen! / Taste it!"
            ),
            (
                "Ha ragione: l'uva è davvero squisita. Metto la frutta nella mia borsa di tela per non usare la plastica.",
                "Haklı: üzüm gerçekten enfes. Plastik kullanmamak için meyveleri bez çantama koyuyorum.",
                "She is right: the grapes are truly delicious. I put the fruit in my canvas bag to avoid using plastic.",
                "avere ragione = haklı olmak | squisito = enfes | la borsa di tela = bez çanta",
                "avere ragione",
                "haklı olmak / to be right"
            ),
            (
                "«Ecco a te, fanno cinque euro precisi. Buona domenica e buon appetito!» mi saluta con affetto.",
                "«Buyur bakalım, tam beş avro yapıyor. İyi pazarlar ve afiyet olsun!» diye beni sevgiyle uğurluyor.",
                "\"Here you go, that makes five euros exact. Have a nice Sunday and enjoy your meal!\" she greets me warmly.",
                "preciso = tam/kesin | salutare = selamlamak | con affetto = sevgiyle",
                "cinque euro precisi",
                "tam beş avro / five euros flat"
            ),
            (
                "Più avanti passo nel padiglione coperto dove si vendono formaggi d'alpeggio, olive e pane casereccio.",
                "Daha ileride yayla peynirleri, zeytin ve ev yapımı ekmek satılan kapalı pavyona geçiyorum.",
                "Further on I pass into the covered pavilion where mountain cheeses, olives, and homemade bread are sold.",
                "più avanti = daha ileride | coperto = kapalı/örtülü | casereccio = ev yapımı",
                "pane casereccio",
                "ev yapımı ekmek / homemade"
            ),
            (
                "Compro un pezzo di Parmigiano Reggiano stagionato ventiquattro mesi e una pagnotta ancora tiepida.",
                "Yirmi dört ay dinlendirilmiş bir parça Parmigiano Reggiano ve hâlâ ılık bir somun ekmek satın alıyorum.",
                "I buy a piece of Parmigiano Reggiano aged twenty-four months and a loaf of bread still warm.",
                "il pezzo = parça | stagionato = dinlendirilmiş/olgun | tiepido = ılık",
                "un pezzo di formaggio",
                "bir parça peynir / cheese piece"
            ),
            (
                "Intorno a me sento parlare italiano, piemontese, arabo e rumeno: il mercato è un piccolo mondo vivo.",
                "Çevremde İtalyanca, Piyemontece, Arapça ve Rumence konuşulduğunu duyuyorum: pazar canlı küçük bir dünya.",
                "Around me I hear Italian, Piedmontese, Arabic, and Romanian spoken: the market is a lively small world.",
                "intorno a me = çevremde | sentire = duymak/hissetmek | vivo = canlı",
                "intorno a me",
                "çevremde / around me"
            ),
            (
                "Torno a casa a piedi lungo il fiume Dora, felice di cucinare un buon pranzo con ingredienti freschi.",
                "Taze malzemelerle güzel bir öğle yemeği pişireceğim için mutlu bir şekilde Dora nehri boyunca yürüyerek eve dönüyorum.",
                "I walk back home along the Dora river, happy to cook a good lunch with fresh ingredients.",
                "tornare a casa = eve dönmek | a piedi = yürüyerek | lungo = boyunca",
                "tornare a piedi",
                "yürüyerek dönmek / walk back"
            ),
        ],
    },
    # 3. Treno per Firenze (A2)
    {
        "title": "3. Treno per Firenze (A2)",
        "subtitle": "A2 | Torino'dan Floransa'ya Tren Yolculuğu",
        "level": "A2",
        "segments": [
            (
                "Alle sette del mattino arrivo alla stazione di Torino Porta Nuova con una piccola valigia.",
                "Sabah saat yedide küçük bir bavulla Torino Porta Nuova istasyonuna varıyorum.",
                "At seven in the morning I arrive at Torino Porta Nuova station with a small suitcase.",
                "la stazione = tren istasyonu | la valigia = bavul | arrivare = varmak",
                "la piccola valigia",
                "küçük bavul / small suitcase"
            ),
            (
                "Controllo il tabellone luminoso delle partenze: il treno ad alta velocità per Firenze parte dal binario nove.",
                "Işıklı kalkış panosunu kontrol ediyorum: Floransa'ya giden yüksek hızlı tren dokuzuncu perondan kalkıyor.",
                "I check the departure board: the high-speed train to Florence leaves from platform nine.",
                "il tabellone = pano | la partenza = kalkış | il binario = peron/ray",
                "dal binario nove",
                "dokuzuncu perondan / platform 9"
            ),
            (
                "Salgo sulla carrozza quattro e trovo il mio posto vicino al finestrino. Il treno parte in perfetto orario.",
                "Dördüncü vagona biniyorum ve pencere kenarındaki yerimi buluyorum. Tren tam zamanında hareket ediyor.",
                "I board coach four and find my seat by the window. The train departs right on time.",
                "salire (salgo) = binmek | la carrozza = vagon | in orario = zamanında",
                "in perfetto orario",
                "tam zamanında / right on time"
            ),
            (
                "Dopo Milano e Bologna, il treno attraversa le lunghe gallerie degli Appennini e poi scende in Toscana.",
                "Milano ve Bologna'dan sonra tren Apenin Dağları'nın uzun tünellerini geçiyor ve ardından Toskana'ya iniyor.",
                "After Milan and Bologna, the train crosses the long tunnels of the Apennines and then descends into Tuscany.",
                "attraversare = geçmek | la galleria = tünel | scendere = inmek",
                "attraversare le gallerie",
                "tünelleri geçmek / cross tunnels"
            ),
            (
                "Fuori dal finestrino appaiono colline dolci, filari di cipressi e antichi casali di pietra.",
                "Pencerenin dışında yumuşak tepeler, sıra sıra selviler ve taş duvarlı eski çiftlik evleri beliriyor.",
                "Outside the window appear gentle hills, rows of cypresses, and ancient stone farmhouses.",
                "apparire = belirmek | la collina = tepe | il cipresso = selvi ağacı",
                "le colline dolci",
                "yumuşak tepeler / gentle hills"
            ),
            (
                "La signora seduta di fronte a me chiude il suo libro e mi sorride: «È la prima volta che visita Firenze?»",
                "Karşımda oturan hanımefendi kitabını kapatıp bana gülümsüyor: «Floransa'yı ilk kez mi ziyaret ediyorsunuz?»",
                "The lady sitting across from me closes her book and smiles at me: \"Is it the first time you visit Florence?\"",
                "seduto = oturan | di fronte a = karşısında | la prima volta = ilk kez",
                "di fronte a me",
                "karşımda / across from me"
            ),
            (
                "«Sì, ho sempre sognato di vedere la cupola del Brunelleschi e la Galleria degli Uffizi dal vivo.»",
                "«Evet, her zaman Brunelleschi'nin kubbesini ve Uffizi Galerisi'ni yakından görmeyi hayal ettim.»",
                "\"Yes, I have always dreamed of seeing Brunelleschi's dome and the Uffizi Gallery in person.\"",
                "sognare di = hayal etmek | la cupola = kubbe | dal vivo = canlı/yakından",
                "vedere dal vivo",
                "yakından görmek / see in person"
            ),
            (
                "«Vedrà, rimarrà senza parole! Io sono fiorentina, ma ogni volta che torno a casa mi emoziono ancora.»",
                "«Göreceksiniz, nutkunuz tutulacak! Ben Floransalıyım ama eve her döndüğümde hâlâ heyecanlanıyorum.»",
                "\"You'll see, you'll be speechless! I am Florentine, but every time I return home I still get emotional.\"",
                "rimanere senza parole = dili tutulmak | ogni volta = her seferinde | emozionarsi = duygulanmak",
                "senza parole",
                "sözsüz / speechless"
            ),
            (
                "Mi consiglia di non fermarmi solo nelle piazze turistiche, ma di attraversare l'Arno verso l'Oltrarno.",
                "Bana sadece turistik meydanlarda durmamamı, Arno nehrini geçip Oltrarno yakasına gitmemi tavsiye ediyor.",
                "She advises me not to stop only in tourist squares, but to cross the Arno toward the Oltrarno district.",
                "consigliare di = tavsiye etmek | solo = sadece | verso = ...-e doğru",
                "mi consiglia di...",
                "bana tavsiye ediyor / advises me"
            ),
            (
                "«Nell'Oltrarno ci sono ancora le botteghe degli artigiani che lavorano il cuoio, il legno e l'oro.»",
                "«Oltrarno'da hâlâ deri, ahşap ve altın işleyen zanaatkârların atölyeleri vardır.»",
                "\"In the Oltrarno there are still the workshops of artisans who work leather, wood, and gold.\"",
                "la bottega = atölye/dükkân | l'artigiano = zanaatkâr | il cuoio = deri",
                "le botteghe artigiane",
                "zanaatkâr atölyeleri / workshops"
            ),
            (
                "«E al tramonto salga a Piazzale Michelangelo: da lassù tutta Firenze sembra dipinta nell'oro.»",
                "«Ve gün batımında Piazzale Michelangelo'ya çıkın: oradan tüm Floransa altına boyanmış gibi görünür.»",
                "\"And at sunset go up to Piazzale Michelangelo: from up there all Florence looks painted in gold.\"",
                "il tramonto = gün batımı | lassù = yukarıda/orada | dipinto = boyanmış",
                "al tramonto",
                "gün batımında / at sunset"
            ),
            (
                "Il controllore passa nel corridoio per controllare il codice QR del biglietto sul mio telefono.",
                "Kondüktör telefonumdaki biletin QR kodunu kontrol etmek için koridordan geçiyor.",
                "The conductor walks down the aisle to check the ticket's QR code on my phone.",
                "il controllore = kondüktör | il corridoio = koridor | il biglietto = bilet",
                "il biglietto del treno",
                "tren bileti / train ticket"
            ),
            (
                "Una voce annuncia dagli altoparlanti: «Siamo in arrivo a Firenze Santa Maria Novella, capolinea.»",
                "Hoparlörlerden bir ses anons ediyor: «Floransa Santa Maria Novella'ya, son durağa varmak üzereyiz.»",
                "A voice announces from the speakers: \"We are arriving at Florence Santa Maria Novella, final stop.\"",
                "annunciare = anons etmek | in arrivo = varmak üzere | il capolinea = son durak",
                "siamo in arrivo",
                "varmak üzereyiz / arriving"
            ),
            (
                "Ringrazio la signora per i preziosi consigli, scendo dal treno e respiro l'aria luminosa di Firenze.",
                "Değerli tavsiyeleri için hanımefendiye teşekkür ediyor, trenden iniyor ve Floransa'nın aydınlık havasını soluyorum.",
                "I thank the lady for the valuable advice, step off the train, and breathe the bright air of Florence.",
                "ringraziare = teşekkür etmek | prezioso = değerli | respirare = nefes almak",
                "preziosi consigli",
                "değerli tavsiyeler / good advice"
            ),
        ],
    },
    # 4. La Bottega di Leonardo (A2)
    {
        "title": "4. La Bottega di Leonardo (A2)",
        "subtitle": "A2 | Floransa'da Leonardo'nun Atölyesi",
        "level": "A2",
        "segments": [
            (
                "Firenze, anno 1476. Nella bottega del maestro Andrea del Verrocchio si lavora dall'alba fino a sera.",
                "Floransa, 1476 yılı. Usta Andrea del Verrocchio'nun atölyesinde şafaktan akşama kadar çalışılıyor.",
                "Florence, year 1476. In the workshop of master Andrea del Verrocchio, work goes on from dawn till evening.",
                "il maestro = usta | si lavora = çalışılır | fino a = ...-e kadar",
                "dall'alba a sera",
                "şafaktan akşama / dawn to dusk"
            ),
            (
                "I giovani apprendisti macinano i pigmenti colorati sulla pietra e preparano le tavole di legno di pioppo.",
                "Genç çıraklar taş üzerinde renkli pigmentleri öğütüyor ve kavak ağacından ahşap panoları hazırlıyorlar.",
                "The young apprentices grind colored pigments on stone and prepare the poplar wood panels.",
                "l'apprendista = çırak | macinare = öğütmek | la tavola = ahşap pano/masa",
                "i giovani apprendisti",
                "genç çıraklar / apprentices"
            ),
            (
                "Tra loro c'è un giovane di ventiquattro anni nato a Vinci: si chiama Leonardo e scrive con la mano sinistra.",
                "Aralarında Vinci'de doğmuş yirmi dört yaşında bir genç var: adı Leonardo ve sol eliyle yazıyor.",
                "Among them is a twenty-four-year-old born in Vinci: his name is Leonardo and he writes with his left hand.",
                "tra loro = aralarında | nato a = ...-de doğmuş | la mano sinistra = sol el",
                "la mano sinistra",
                "sol el / left hand"
            ),
            (
                "Leonardo porta sempre alla cintura un piccolo taccuino per disegnare tutto ciò che osserva per strada.",
                "Leonardo sokakta gözlemlediği her şeyi çizmek için kemerinde her zaman küçük bir not defteri taşır.",
                "Leonardo always carries a small notebook on his belt to draw everything he observes in the street.",
                "la cintura = kemer | il taccuino = cep defteri | osservare = gözlemlemek",
                "tutto ciò che osserva",
                "gözlemlediği her şey / all seen"
            ),
            (
                "Disegna il volo degli uccelli, i vortici dell'acqua nell'Arno, il volto di un vecchio e gli ingranaggi.",
                "Kuşların uçuşunu, Arno nehrindeki su girdaplarını, yaşlı bir adamın yüzünü ve dişli çarkları çizer.",
                "He draws the flight of birds, water vortices in the Arno, an old man's face, and gears.",
                "il volo = uçuş | il vortice = girdap | l'ingranaggio = dişli çark",
                "il volo degli uccelli",
                "kuşların uçuşu / bird flight"
            ),
            (
                "«Leonardo, perché studi le ali dei rondini invece di finire questo dipinto?» gli chiede un compagno.",
                "«Leonardo, bu tabloyu bitirmek yerine neden kırlangıçların kanatlarını inceliyorsun?» diye soruyor bir arkadaşı.",
                "\"Leonardo, why do you study swallows' wings instead of finishing this painting?\" a fellow apprentice asks.",
                "l'ala (le ali) = kanat | invece di = ... yerine | il dipinto = tablo",
                "invece di finire",
                "bitirmek yerine / instead of"
            ),
            (
                "«Perché la pittura è una scienza!» risponde Leonardo. «Chi non conosce le leggi della natura dipinge alla cieca.»",
                "«Çünkü resim bir bilimdir!» diye cevap veriyor Leonardo. «Doğa yasalarını bilmeyen kişi körü körüne resim yapar.»",
                "\"Because painting is a science!\" replies Leonardo. \"Whoever doesn't know nature's laws paints blindly.\"",
                "la scienza = bilim | la legge = yasa | alla cieca = körü körüne",
                "le leggi della natura",
                "doğa yasaları / laws of nature"
            ),
            (
                "Per rappresentare la luce sul volto umano, Leonardo inventa lo «sfumato»: contorni morbidi come il fumo.",
                "İnsan yüzündeki ışığı betimlemek için Leonardo «sfumato» tekniğini icat eder: duman gibi yumuşak hatlar.",
                "To represent light on the human face, Leonardo invents 'sfumato': contours as soft as smoke.",
                "il volto = yüz/çehre | il contorno = dış hat | morbido = yumuşak",
                "morbido come il fumo",
                "duman gibi yumuşak / like smoke"
            ),
            (
                "Secondo lui, nella realtà non esistono linee nere tra la luce e l'ombra, ma infinite sfumature.",
                "Ona göre gerçeklikte ışık ile gölge arasında siyah çizgiler yoktur, sonsuz geçiş tonları vardır.",
                "According to him, in reality there are no black lines between light and shadow, but infinite nuances.",
                "secondo lui = ona göre | l'ombra = gölge | la sfumatura = nüans/ton geçişi",
                "tra la luce e l'ombra",
                "ışık ve gölge arasında"
            ),
            (
                "Di notte, nel silenzio della stanza, riempie i suoi fogli con quella misteriosa scrittura da destra a sinistra.",
                "Geceleyin odanın sessizliğinde kâğıtlarını sağdan sola doğru o gizemli el yazısıyla doldurur.",
                "At night, in the silence of the room, he fills his sheets with that mysterious right-to-left writing.",
                "di notte = geceleyin | il foglio = yaprak/kâğıt | misterioso = gizemli",
                "nel silenzio della notte",
                "gecenin sessizliğinde / at night"
            ),
            (
                "Basta mettere uno specchio accanto al foglio per leggere chiaramente i suoi pensieri e i suoi progetti.",
                "Düşüncelerini ve projelerini açıkça okumak için kâğıdın yanına bir ayna koymak yeterlidir.",
                "It is enough to place a mirror next to the sheet to read his thoughts and projects clearly.",
                "bastare (basta) = yetmek | lo specchio = ayna | chiaramente = açıkça",
                "mettere uno specchio",
                "bir ayna koymak / place mirror"
            ),
            (
                "In una pagina progetta ponti mobili e macchine per sollevare pesi; nell'altra studia l'anatomia del cuore.",
                "Bir sayfada hareketli köprüler ve ağırlık kaldırma makineleri tasarlar; diğerinde kalbin anatomisini inceler.",
                "On one page he designs movable bridges and machines to lift weights; on the next he studies heart anatomy.",
                "progettare = tasarlamak | sollevare = kaldırmak | il peso = ağırlık",
                "sollevare pesi",
                "ağırlık kaldırmak / lift weights"
            ),
            (
                "«Ostinato rigore» scrive sul margine del quaderno: il rigore ostinato di chi non smette mai di cercare.",
                "Defterin kenarına «Ostinato rigore» (inatçı titizlik) yazar: aramayı asla bırakmayan kişinin titizliği.",
                "\"Obstinate rigor,\" he writes in the notebook's margin: the tireless rigor of one who never stops seeking.",
                "ostinato = inatçı/azimli | il rigore = titizlik | smettere di = bırakmak",
                "non smettere mai",
                "asla bırakmamak / never stop"
            ),
            (
                "Cinque secoli dopo, quei quaderni ci insegnano che l'arte e l'ingegneria nascono dalla stessa meraviglia.",
                "Beş yüzyıl sonra o defterler bize sanat ve mühendisliğin aynı hayranlık duygusundan doğduğunu öğretiyor.",
                "Five centuries later, those notebooks teach us that art and engineering are born from the same wonder.",
                "il secolo = yüzyıl | nascere = doğmak | la meraviglia = hayret/hayranlık",
                "nascere dalla meraviglia",
                "hayretten doğmak / born of wonder"
            ),
        ],
    },
    # 5. Machiavelli: Il Principe (B1)
    {
        "title": "5. Machiavelli: Il Principe (B1)",
        "subtitle": "B1 | Machiavelli'nin Sürgün Mektubu ve Prens",
        "level": "B1",
        "segments": [
            (
                "Nel dicembre del 1513, Niccolò Machiavelli vive in esilio nel suo podere all'Albergaccio, vicino a San Casciano.",
                "1513 yılının Aralık ayında Niccolò Machiavelli, San Casciano yakınlarındaki Albergaccio çiftliğinde sürgünde yaşar.",
                "In December 1513, Niccolò Machiavelli lives in exile on his farm at Albergaccio, near San Casciano.",
                "l'esilio = sürgün | il podere = çiftlik arazisi | vicino a = yakınında",
                "vivere in esilio",
                "sürgünde yaşamak / live in exile"
            ),
            (
                "Dopo la caduta della Repubblica fiorentina, ha perso il suo incarico di Segretario ed è stato perfino torturato.",
                "Floransa Cumhuriyeti'nin düşüşünden sonra Sekreterlik görevini kaybetmiş ve hatta işkence görmüştür.",
                "After the fall of the Florentine Republic, he lost his post as Secretary and was even tortured.",
                "la caduta = düşüş/yıkılış | l'incarico = görev | perfino = hatta",
                "perdere l'incarico",
                "görevini kaybetmek / lose post"
            ),
            (
                "Durante il giorno passeggia nei boschi, parla con i boscaioli e gioca a carte nell'osteria del villaggio.",
                "Gündüzleri ormanda dolaşır, oduncularla konuşur ve köy meyhanesinde kâğıt oynar.",
                "During the day he walks in the woods, talks with woodcutters, and plays cards at the village tavern.",
                "il bosco = orman | il boscaiolo = oduncu | l'osteria = meyhane/lokanta",
                "durante il giorno",
                "gün boyunca / during the day"
            ),
            (
                "Ma quando viene la sera, come scrive nella celebre lettera a Francesco Vettori, tutto cambia.",
                "Fakat akşam olduğunda, Francesco Vettori'ye yazdığı ünlü mektupta anlattığı gibi her şey değişir.",
                "But when evening comes, as he writes in his famous letter to Francesco Vettori, everything changes.",
                "celebre = ünlü/meşhur | la lettera = mektup | cambiare = değişmek",
                "quando viene la sera",
                "akşam olduğunda / at evening"
            ),
            (
                "«Venuta la sera, mi ritorno in casa ed entro nel mio scrittoio; e in sull'uscio mi spoglio la veste cotidiana.»",
                "«Akşam olunca eve dönerim ve çalışma odama girerim; eşikte üstümdeki gündelik giysiyi çıkarırım.»",
                "\"When evening comes, I return home and enter my study; and at the threshold I take off my everyday clothes.\"",
                "lo scrittoio = çalışma odası | l'uscio = kapı eşiği | spogliarsi = soyunmak/çıkarmak",
                "entrare nello scrittoio",
                "çalışma odasına girmek / study"
            ),
            (
                "Si toglie gli abiti pieni di fango e indossa «panni reali e curiali», cioè vestiti degni di una corte.",
                "Çamurla kaplı giysilerini çıkarır ve «krallara ve saraya layık giysiler» giyer.",
                "He takes off his mud-stained clothes and puts on 'royal and courtly garments' worthy of a court.",
                "il fango = çamur | indossare = giymek | degno di = ...-e layık",
                "degno di rispetto",
                "saygıya layık / worthy of"
            ),
            (
                "Così vestito, entra nelle «antiche corti degli antiqui uomini»: legge Tito Livio, Tacito, Polibio e Cicerone.",
                "Böyle giyinmiş halde «antik çağ insanlarının meclislerine» girer: Titus Livius, Tacitus, Polybius ve Cicero okur.",
                "Thus dressed, he enters the 'ancient courts of ancient men': he reads Livy, Tacitus, Polybius, and Cicero.",
                "antico = antik/eski | la corte = saray/meclis | così = böylece",
                "gli antichi uomini",
                "antik çağ insanları / ancients"
            ),
            (
                "Non si limita a leggere: interroga gli storici antichi sulle ragioni delle loro azioni, ed essi gli rispondono.",
                "Sadece okumakla yetinmez: antik tarihçilere eylemlerinin nedenlerini sorar ve onlar da ona cevap verir.",
                "He does not just read: he questions the ancient historians about the reasons for their actions, and they answer.",
                "limitarsi a = ... ile yetinmek | interrogare = sorgulamak | la ragione = neden/akıl",
                "non si limita a...",
                "... ile yetinmez / not limited"
            ),
            (
                "Per quattro ore di seguito non sente alcuna noia, dimentica ogni affanno e non teme la povertà né la morte.",
                "Arka arkaya dört saat boyunca hiçbir sıkıntı duymaz, her derdi unutur, ne yoksulluktan ne ölümden korkar.",
                "For four hours straight he feels no boredom, forgets every trouble, and fears neither poverty nor death.",
                "di seguito = aralıksız | l'affanno = dert/kaygı | temere = korkmak",
                "quattro ore di seguito",
                "dört saat aralıksız / straight"
            ),
            (
                "Da queste notti di studio nasce un piccolo trattato intitolato «De Principatibus», oggi noto come «Il Principe».",
                "Bu çalışma gecelerinden bugün «Prens» (Il Principe) olarak bilinen «De Principatibus» adlı küçük inceleme doğar.",
                "From these nights of study is born a small treatise titled 'De Principatibus', known today as 'The Prince'.",
                "il trattato = inceleme/risale | intitolato = başlıklı | noto come = ... olarak bilinen",
                "noto come...",
                "... olarak bilinen / known as"
            ),
            (
                "Il metodo di Machiavelli è rivoluzionario: decide di andare «drieto alla verità effettuale della cosa».",
                "Machiavelli'nin yöntemi devrimcidir: hayallerin değil, «işin fiilî gerçekliğinin» (verità effettuale) peşinden gider.",
                "Machiavelli's method is revolutionary: he decides to go after the 'effectual truth of the matter'.",
                "la verità effettuale = fiilî gerçeklik | rivoluzionario = devrimci | decidere = karar vermek",
                "la verità effettuale",
                "fiilî gerçeklik / actual truth"
            ),
            (
                "Secondo lui, la storia umana è governata per metà dalla «Fortuna» (il caso) e per metà dalla «Virtù».",
                "Ona göre insanlık tarihi yarı yarıya «Fortuna» (talih/rastlantı) ve «Virtù» (irade/beceri) tarafından yönetilir.",
                "According to him, human history is governed half by 'Fortuna' (chance) and half by 'Virtù' (skill/vigor).",
                "governato = yönetilen | per metà = yarı yarıya | il caso = rastlantı",
                "per metà",
                "yarı yarıya / by half"
            ),
            (
                "La Fortuna è come un fiume in piena: distrugge tutto solo dove gli uomini non hanno costruito argini in tempo.",
                "Talih taşkın bir nehir gibidir: yalnızca insanların zamanında bentler inşa etmediği yerlerde her şeyi yıkar.",
                "Fortune is like a raging river: it destroys everything only where men have not built dikes in time.",
                "in piena = taşkın halde | distruggere = yıkmak | l'argine = bent/set",
                "costruire argini",
                "bentler kurmak / build dikes"
            ),
            (
                "Studiare la storia serve proprio a questo: costruire argini con l'intelligenza prima che arrivi la tempesta.",
                "Tarih okumak tam olarak buna yarar: fırtına gelmeden önce zekâyla bentler inşa etmek.",
                "Studying history serves precisely this purpose: building dikes with intelligence before the storm arrives.",
                "servire a = ...-e yaramak | proprio = tam olarak | la tempesta = fırtına",
                "prima della tempesta",
                "fırtınadan önce / before storm"
            ),
        ],
    },
    # 6. Dante: Nel Mezzo del Cammin (B1)
    {
        "title": "6. Dante: Nel Mezzo del Cammin (B1)",
        "subtitle": "B1 | Dante Alighieri ve İlahi Komedya'nın Başlangıcı",
        "level": "B1",
        "segments": [
            (
                "«Nel mezzo del cammin di nostra vita / mi ritrovai per una selva oscura, / ché la diritta via era smarrita.»",
                "«Hayat yolculuğumuzun ortasında / karanlık bir ormanda buldum kendimi, / çünkü doğru yol yitirilmişti.»",
                "\"Midway upon the journey of our life / I found myself within a dark forest, / for the straightforward pathway had been lost.\"",
                "il cammino = yol/yolculuk | la selva oscura = karanlık orman | smarrito = kaybolmuş",
                "una selva oscura",
                "karanlık bir orman / dark woods"
            ),
            (
                "Con questi tre versi immortali inizia la «Divina Commedia» di Dante Alighieri, padre della lingua italiana.",
                "İtalyan dilinin babası Dante Alighieri'nin «İlahi Komedya»sı bu üç ölümsüz dizeyle başlar.",
                "With these three immortal verses begins the 'Divine Comedy' by Dante Alighieri, father of the Italian language.",
                "il verso = dize/mısra | immortale = ölümsüz | iniziare = başlamak",
                "versi immortali",
                "ölümsüz dizeler / immortal lines"
            ),
            (
                "Dante dice «nostra vita», non «mia vita»: il suo viaggio attraverso la crisi appartiene a ogni essere umano.",
                "Dante «benim hayatım» değil, «bizim hayatımız» der: krizin içinden geçen yolculuğu her insana aittir.",
                "Dante says 'our life', not 'my life': his journey through crisis belongs to every human being.",
                "attraverso = içinden/boyunca | appartenere = ait olmak | l'essere umano = insan",
                "appartiene a tutti",
                "herkese aittir / belongs to all"
            ),
            (
                "Uscito dalla selva della paura, Dante vede un colle illuminato dai raggi del sole e cerca di salire.",
                "Korku ormanından çıkan Dante, güneş ışınlarıyla aydınlanan bir tepe görür ve tırmanmaya çalışır.",
                "Having left the forest of fear, Dante sees a hill lit by the sun's rays and tries to climb it.",
                "il colle = tepe | il raggio = ışın | cercare di = ...-meye çalışmak",
                "i raggi del sole",
                "güneş ışınları / sun's rays"
            ),
            (
                "Ma tre fiere gli sbarrano il passo: una lonza agile, un leone superbo e una lupa magra piena di brame.",
                "Ancak üç vahşi hayvan yolunu keser: çevik bir vaşak, kibirli bir aslan ve arzularla dolu cılız bir dişi kurt.",
                "But three beasts block his path: a nimble leopard, a proud lion, and a lean she-wolf full of cravings.",
                "sbarrare il passo = yolu kesmek | superbo = kibirli | la lupa = dişi kurt",
                "sbarrare il passo",
                "yolu kesmek / block the path"
            ),
            (
                "Mentre Dante sta per cadere di nuovo nell'oscurità, appare nel silenzio la figura del poeta latino Virgilio.",
                "Dante yeniden karanlığa düşmek üzereyken, sessizliğin içinde Latin şair Vergilius'un silüeti belirir.",
                "While Dante is about to fall back into darkness, the figure of the Latin poet Virgil appears in the silence.",
                "stare per = ...-mek üzere olmak | di nuovo = yeniden | l'oscurità = karanlık",
                "stare per cadere",
                "düşmek üzere olmak / about to"
            ),
            (
                "Virgilio rappresenta la Ragione umana: non si può uscire dal caos con una scorciatoia, bisogna comprendere il male.",
                "Vergilius insan Aklını temsil eder: kaostan kestirme bir yolla çıkılamaz, kötülüğü anlamak gerekir.",
                "Virgil represents human Reason: one cannot escape chaos via a shortcut; one must understand evil.",
                "rappresentare = temsil etmek | la scorciatoia = kestirme yol | comprendere = kavramak",
                "una scorciatoia",
                "kestirme yol / a shortcut"
            ),
            (
                "Nel canto di Ulisse, Dante immagina l'eroe greco che parla ai suoi compagni davanti alle Colonne d'Ercole.",
                "Odysseus kantosunda Dante, Yunan kahramanı Herkül Sütunları önünde yoldaşlarına seslenirken hayal eder.",
                "In the canto of Ulysses, Dante imagines the Greek hero speaking to his companions before the Pillars of Hercules.",
                "immaginare = hayal etmek | l'eroe = kahraman | il compagno = yoldaş",
                "immaginare il viaggio",
                "yolculuğu hayal etmek / imagine"
            ),
            (
                "«Considerate la vostra semenza: / fatti non foste a viver come bruti, / ma per seguir virtute e canoscenza.»",
                "«Soyunuzu düşünün: / hayvanlar gibi yaşamak için yaratılmadınız, / erdem ve bilginin peşinden gitmek için var oldunuz.»",
                "\"Consider your origin: / you were not made to live like brutes, / but to follow virtue and knowledge.\"",
                "la semenza = öz/soy | il bruto = kaba hayvan | la conoscenza = bilgi",
                "virtute e canoscenza",
                "erdem ve bilgi / virtue & mind"
            ),
            (
                "Dante ha scritto questo poema in esilio, lontano dalla sua amata Firenze, a cui non poté mai più tornare.",
                "Dante bu şiiri sürgünde, bir daha asla dönemediği sevgili Floransa'sından uzakta yazmıştır.",
                "Dante wrote this poem in exile, far from his beloved Florence, to which he could never return.",
                "lontano da = ...-den uzakta | amato = sevilen | mai più = bir daha asla",
                "lontano da casa",
                "evden uzakta / far from home"
            ),
            (
                "Invece del latino dei dotti, scelse il volgare fiorentino perché tutti potessero leggere e comprendere.",
                "Alimlerin Latincesi yerine herkesin okuyup anlayabilmesi için Floransa halk dilini (volgare) seçti.",
                "Instead of scholars' Latin, he chose the Florentine vernacular so that everyone could read and understand.",
                "scegliere (scelse) = seçmek | il dotto = bilgin | il volgare = halk dili",
                "scegliere la lingua",
                "dili seçmek / choose language"
            ),
            (
                "Grazie a quella scelta coraggiosa, ancora oggi un italiano può leggere i versi del Trecento e sentirli vivi.",
                "O cesur seçim sayesinde bugün hâlâ bir İtalyan 14. yüzyıl dizelerini okuyup onları canlı hissedebilir.",
                "Thanks to that brave choice, even today an Italian can read 14th-century verses and feel them alive.",
                "grazie a = sayesinde | coraggioso = cesur | sentire = hissetmek",
                "una scelta coraggiosa",
                "cesur bir seçim / brave choice"
            ),
            (
                "Alla fine dell'Inferno, dopo aver attraversato il centro della Terra, Dante e Virgilio risalgono verso la superficie.",
                "Cehennem'in sonunda, Dünya'nın merkezini geçtikten sonra Dante ve Vergilius yüzeye doğru yeniden yükselirler.",
                "At the end of Inferno, after crossing the center of the Earth, Dante and Virgil climb back toward the surface.",
                "alla fine = sonunda | risalire = yeniden çıkmak | la superficie = yüzey",
                "risalire alla luce",
                "ışığa yükselmek / rise to light"
            ),
            (
                "Il viaggio nell'oscurità si chiude con il verso della speranza: «E quindi uscimmo a riveder le stelle.»",
                "Karanlıktaki yolculuk umut dizesiyle kapanır: «Ve oradan yıldızları yeniden görmek için dışarı çıktık.»",
                "The journey in darkness closes with the verse of hope: \"And thence we came forth to see again the stars.\"",
                "la speranza = umut | quindi = oradan/böylece | rivedere = yeniden görmek",
                "riveder le stelle",
                "yıldızları yeniden görmek"
            ),
        ],
    },
    # 7. Italo Calvino: Le Città Invisibili (B1)
    {
        "title": "7. Italo Calvino: Le Città Invisibili (B1)",
        "subtitle": "B1 | Italo Calvino, Görünmez Kentler ve Hafıza",
        "level": "B1",
        "segments": [
            (
                "Nel romanzo «Le città invisibili» di Italo Calvino, il giovane veneziano Marco Polo parla con l'imperatore Kublai Khan.",
                "Italo Calvino'nun «Görünmez Kentler» romanında genç Venedikli Marco Polo, İmparator Kubilay Han ile konuşur.",
                "In Italo Calvino's novel 'Invisible Cities', the young Venetian Marco Polo speaks with Emperor Kublai Khan.",
                "il romanzo = roman | invisibile = görünmez | l'imperatore = imparator",
                "le città invisibili",
                "görünmez kentler / invisible"
            ),
            (
                "L'impero di Kublai Khan è così vasto che l'imperatore stesso non potrà mai visitare tutte le sue province.",
                "Kubilay Han'ın imparatorluğu o kadar geniştir ki imparatorun kendisi bile tüm eyaletlerini asla ziyaret edemeyecektir.",
                "Kublai Khan's empire is so vast that the emperor himself will never be able to visit all its provinces.",
                "così vasto = o kadar geniş | stesso = bizzat kendisi | la provincia = eyalet",
                "così vasto che...",
                "o kadar geniş ki / so vast that"
            ),
            (
                "Seduti nei giardini del palazzo, la sera, l'imperatore ascolta i racconti di viaggio del mercante veneziano.",
                "Akşamları saray bahçelerinde otururlarken imparator, Venedikli tüccarın yolculuk hikâyelerini dinler.",
                "Sitting in the palace gardens in the evening, the emperor listens to the travel tales of the Venetian merchant.",
                "ascoltare = dinlemek | il racconto = öykü/anlatı | il mercante = tüccar",
                "i racconti di viaggio",
                "yolculuk öyküleri / travel tales"
            ),
            (
                "Marco Polo descrive città costruite sull'acqua, città sottili come ragnatele e città fatte di specchi e ricordi.",
                "Marco Polo su üzerine kurulmuş kentleri, örümcek ağı gibi ince kentleri ve aynalarla anılardan yapılmış kentleri betimler.",
                "Marco Polo describes cities built on water, cities as thin as cobwebs, and cities made of mirrors and memories.",
                "descrivere = betimlemek | sottile = ince | la ragnatela = örümcek ağı",
                "sottile come ragnatela",
                "örümcek ağı gibi ince / thin"
            ),
            (
                "Una città non è fatta solo di pietre e mura, spiega Marco, ma delle relazioni tra lo spazio e il passato.",
                "Bir kent yalnızca taşlardan ve surlardan oluşmaz, diye açıklar Marco; mekân ile geçmiş arasındaki ilişkilerden oluşur.",
                "A city is not made only of stones and walls, Marco explains, but of relationships between space and the past.",
                "la pietra = taş | le mura = kent surları | la relazione = ilişki",
                "non solo di pietre",
                "sadece taşlardan değil / stones"
            ),
            (
                "Un giorno Kublai Khan gli fa una domanda diretta: «Marco, perché non mi parli mai di Venezia, la tua città?»",
                "Bir gün Kubilay Han ona doğrudan bir soru sorar: «Marco, neden bana kendi kentin Venedik'ten hiç bahsetmiyorsun?»",
                "One day Kublai Khan asks him a direct question: \"Marco, why do you never speak to me of Venice, your city?\"",
                "fare una domanda = soru sormak | diretto = doğrudan | parlare di = ...-den bahsetmek",
                "fare una domanda",
                "bir soru sormak / ask question"
            ),
            (
                "Marco Polo sorride e risponde: «Ogni volta che descrivo una città, dico qualcosa di Venezia.»",
                "Marco Polo gülümser ve cevap verir: «Bir kenti her betimlediğimde Venedik hakkında bir şey söylüyorum.»",
                "Marco Polo smiles and replies: \"Every time I describe a city, I am saying something about Venice.\"",
                "ogni volta che = her ...-diğinde | qualcosa = bir şey | rispondere = yanıtlamak",
                "ogni volta che...",
                "her ne zaman ... / whenever"
            ),
            (
                "«Per distinguere le qualità delle altre città, devo partire da una prima città che resta implicita: Venezia.»",
                "«Diğer kentlerin niteliklerini ayırt etmek için örtük kalan ilk bir kentten yola çıkmalıyım: Venedik.»",
                "\"To distinguish the qualities of other cities, I must start from a first city that remains implicit: Venice.\"",
                "distinguere = ayırt etmek | partire da = ...-den yola çıkmak | restare = kalmak",
                "partire da...",
                "...-den yola çıkmak / start from"
            ),
            (
                "Per Calvino, la scrittura deve possedere una virtù fondamentale: la «leggerezza» unita alla precisione.",
                "Calvino için yazı temel bir erdeme sahip olmalıdır: kesinlikle birleşmiş «hafiflik» (leggerezza).",
                "For Calvino, writing must possess a fundamental virtue: 'lightness' combined with precision.",
                "possedere = sahip olmak | la leggerezza = hafiflik | unito a = ... ile birleşmiş",
                "la leggerezza",
                "hafiflik / lightness"
            ),
            (
                "La leggerezza non è superficialità: è planare sulle cose dall'alto, senza avere macigni sul cuore.",
                "Hafiflik yüzeysellik değildir: yüreğinde kaya parçaları taşımadan şeylerin üzerinde yukarıdan süzülmektir.",
                "Lightness is not superficiality: it is gliding over things from above, without having boulders on one's heart.",
                "planare = süzülmek | dall'alto = yukarıdan | il macigno = büyük kaya",
                "planare dall'alto",
                "yukarıdan süzülmek / glide above"
            ),
            (
                "Nell'ultima pagina del libro, Kublai Khan guarda il suo atlante e teme che tutto conduca a una città infernale.",
                "Kitabın son sayfasında Kubilay Han atlasına bakar ve her şeyin cehennemî bir kente çıkmasından korkar.",
                "On the last page of the book, Kublai Khan looks at his atlas and fears everything leads to an infernal city.",
                "l'atlante = atlas | condurre = götürmek/çıkmak | infernale = cehennemî",
                "l'ultima pagina",
                "son sayfa / the last page"
            ),
            (
                "Marco Polo risponde che l'inferno dei viventi non è qualcosa che sarà: è già qui, intorno a noi ogni giorno.",
                "Marco Polo yaşayanların cehenneminin gelecekte olacak bir şey olmadığını söyler: o zaten burada, her gün çevremizdedir.",
                "Marco Polo replies that the inferno of the living is not something that will be: it is already here around us.",
                "i viventi = yaşayanlar | già = zaten/çoktan | intorno a noi = çevremizde",
                "è già qui",
                "zaten burada / already here"
            ),
            (
                "Ci sono due modi per non soffrirne: il primo riesce facile a molti, ed è accettare l'inferno fino a non vederlo più.",
                "Ondan acı çekmemenin iki yolu vardır: birincisi çoğuna kolay gelir; cehennemi artık görmeyecek kadar kabullenmektir.",
                "There are two ways not to suffer from it: the first comes easily to many, accepting the inferno until unseen.",
                "il modo = yol/biçim | soffrire = acı çekmek | accettare = kabul etmek",
                "ci sono due modi",
                "iki yol vardır / two ways"
            ),
            (
                "Il secondo è esigente: «cercare e saper riconoscere chi e cosa, in mezzo all'inferno, non è inferno, e dargli spazio.»",
                "İkincisi özen ister: «cehennemin ortasında kimin ve neyin cehennem olmadığını arayıp tanımak ve ona alan açmak.»",
                "The second is demanding: \"seek and learn to recognize who and what, in the midst of the inferno, is not inferno, and give it space.\"",
                "esigente = zahmetli/titiz | riconoscere = tanımak | dare spazio = alan açmak",
                "saper riconoscere",
                "tanıyabilmek / recognize"
            ),
        ],
    },
    # 8. Pirandello: La Maschera e il Volto (B1)
    {
        "title": "8. Pirandello: La Maschera e il Volto (B1)",
        "subtitle": "B1 | Luigi Pirandello, Maske ve Kimlik Felsefesi",
        "level": "B1",
        "segments": [
            (
                "Una mattina qualsiasi, Vitangelo Moscarda si guarda allo specchio mentre sua moglie gli fa notare un dettaglio.",
                "Sıradan bir sabah Vitangelo Moscarda aynada kendine bakarken eşi ona küçük bir ayrıntıyı fark ettirir.",
                "One ordinary morning, Vitangelo Moscarda looks at himself in the mirror while his wife points out a detail.",
                "qualsiasi = herhangi/sıradan | far notare = fark ettirmek | il dettaglio = ayrıntı",
                "far notare",
                "fark ettirmek / point out"
            ),
            (
                "«Ma non vedi che il tuo naso pende leggermente verso destra?» gli dice lei ridendo senza malizia.",
                "«Burnunun hafifçe sağa doğru eğildiğini görmüyor musun?» der eşi hiçbir kötülük düşünmeden gülerek.",
                "\"Don't you see that your nose tilts slightly to the right?\" she tells him laughing without malice.",
                "pendere = eğilmek/sarkmak | leggermente = hafifçe | senza malizia = art niyetsiz",
                "leggermente a destra",
                "hafifçe sağa / slightly right"
            ),
            (
                "Quella frase banale scatena nella mente di Moscarda una vertigine filosofica che cambierà tutta la sua vita.",
                "O sıradan cümle Moscarda'nın zihninde tüm hayatını değiştirecek felsefi bir baş dönmesi başlatır.",
                "That trivial sentence triggers a philosophical vertigo in Moscarda's mind that will change his whole life.",
                "banale = sıradan | scatenare = tetiklemek | la vertigine = baş dönmesi",
                "una frase banale",
                "sıradan bir cümle / trivial"
            ),
            (
                "Se non conosceva nemmeno il proprio naso, pensa, come può sapere chi è davvero agli occhi degli altri?",
                "Kendi burnunu bile tanımıyorsa, diye düşünür, başkalarının gözünde gerçekte kim olduğunu nasıl bilebilir?",
                "If he did not even know his own nose, he thinks, how can he know who he truly is in the eyes of others?",
                "nemmeno = bile (olumsuz) | proprio = kendi | agli occhi di = ... gözünde",
                "agli occhi degli altri",
                "başkalarının gözünde"
            ),
            (
                "Così nasce «Uno, nessuno e centomila», l'ultimo grande romanzo dello scrittore siciliano Luigi Pirandello.",
                "Sicilyalı yazar Luigi Pirandello'nun son büyük romanı «Bir, Hiçkimse ve Yüz Bin» böyle doğar.",
                "Thus is born 'One, No One and One Hundred Thousand', the last great novel by Sicilian writer Luigi Pirandello.",
                "nessuno = hiç kimse | centomila = yüz bin | lo scrittore = yazar",
                "uno, nessuno, centomila",
                "bir, hiçkimse, yüz bin"
            ),
            (
                "Noi crediamo di essere «uno»: una persona coerente, sempre uguale per noi stessi e per chi ci circonda.",
                "Biz «bir» kişi olduğumuza inanırız: hem kendimiz hem de çevremizdekiler için her zaman aynı, tutarlı bir birey.",
                "We believe we are 'one': a coherent person, always the same for ourselves and for those around us.",
                "credere di = ...-diğine inanmak | coerente = tutarlı | circondare = çevrelemek",
                "essere coerente",
                "tutarlı olmak / be coherent"
            ),
            (
                "In realtà siamo «centomila»: ogni amico, collega o passante costruisce dentro di sé un'immagine diversa di noi.",
                "Gerçekte ise «yüz bin» kişiyizdir: her dost, iş arkadaşı veya yoldan geçen kişi kendi içinde bizim farklı bir imgesini kurar.",
                "In reality we are 'one hundred thousand': every friend, colleague, or passerby builds a different image of us.",
                "in realtà = gerçekte | il passante = yoldan geçen | l'immagine = imge/görüntü",
                "in realtà",
                "gerçekte / in reality"
            ),
            (
                "E quando scopriamo di essere centomila maschere diverse, ci rendiamo conto di essere, in fondo, «nessuno».",
                "Ve yüz bin farklı maske olduğumuzu keşfettiğimizde, aslında özümüzde «hiç kimse» olduğumuzun farkına varırız.",
                "And when we discover we are a hundred thousand different masks, we realize we are, deep down, 'no one'.",
                "scoprire = keşfetmek | rendersi conto = farkına varmak | in fondo = özünde/temelde",
                "rendersi conto di...",
                "farkına varmak / realize"
            ),
            (
                "Pirandello chiama questo conflitto l'opposizione tra la «Vita» che scorre sempre e la «Forma» che ci imprigiona.",
                "Pirandello bu çatışmayı daima akan «Hayat» ile bizi hapseden «Biçim» (Forma) arasındaki karşıtlık olarak adlandırır.",
                "Pirandello calls this conflict the opposition between 'Life' that ever flows and the 'Form' that imprisons us.",
                "scorrere = akmak | la forma = biçim/kalıp | imprigionare = hapsetmek",
                "la vita che scorre",
                "akan hayat / flowing life"
            ),
            (
                "La società ci costringe a indossare una maschera fissa: il ruolo del figlio, del professionista, del cittadino modello.",
                "Toplum bizi sabit bir maske takmaya zorlar: evlat, meslek sahibi veya örnek yurttaş rolü.",
                "Society forces us to wear a fixed mask: the role of son, professional, or model citizen.",
                "costringere a = zorlamak | fisso = sabit | il ruolo = rol",
                "indossare una maschera",
                "maske takmak / wear a mask"
            ),
            (
                "Chi prova a strappare la propria maschera viene subito giudicato pazzo da chi preferisce non farsi domande.",
                "Kendi maskesini yırtıp atmaya çalışan kişi, soru sormamayı tercih edenler tarafından hemen deli ilan edilir.",
                "Whoever tries to tear off their mask is immediately judged mad by those who prefer not to ask questions.",
                "strappare = yırtıp koparmak | giudicare = yargılamak | pazzo = deli",
                "farsi domande",
                "kendine soru sormak / question"
            ),
            (
                "Nel saggio «L'umorismo», Pirandello distingue inoltre il «comico» dall'«umoristico» attraverso un celebre esempio.",
                "«Mizah» (L'umorismo) denemesinde Pirandello ayrıca ünlü bir örnekle «komik» ile «mizahi» olanı birbirinden ayırır.",
                "In his essay 'On Humor', Pirandello further distinguishes the 'comic' from the 'humorous' via a famous example.",
                "il saggio = deneme | inoltre = ayrıca | attraverso = aracılığıyla",
                "il saggio filosofico",
                "felsefi deneme / essay"
            ),
            (
                "Vedere una vecchia signora truccata come una ragazza fa ridere: questo è l'«avvertimento del contrario» (il comico).",
                "Genç bir kız gibi boyanmış yaşlı bir hanım görmek güldürür: bu «zıddın fark edilmesi»dir (komik).",
                "Seeing an old lady made up like a young girl makes us laugh: this is the 'perception of the opposite' (the comic).",
                "truccato = makyajlı | far ridere = güldürmek | il contrario = zıt/ters",
                "avvertire il contrario",
                "zıddı fark etmek / opposite"
            ),
            (
                "Ma se riflettiamo sul suo dolore nascosto, il riso diventa compassione: ecco il «sentimento del contrario» (l'umorismo).",
                "Fakat onun gizli acısı üzerine düşünürsek gülüş şefkate dönüşür: işte bu «zıddın hissedilmesi»dir (mizah).",
                "But if we reflect on her hidden pain, laughter turns into compassion: this is the 'feeling of the opposite' (humor).",
                "riflettere = derin düşünmek | nascosto = gizli | la compassione = şefkat/merhamet",
                "riflettere sul dolore",
                "acı üzerine düşünmek / reflect"
            ),
        ],
    },
    # 9. Seneca & Marco Aurelio: La Calma (B1)
    {
        "title": "9. Seneca & Marco Aurelio: La Calma (B1)",
        "subtitle": "B1 | Roma Stoacılığı: Seneca ve Marcus Aurelius",
        "level": "B1",
        "segments": [
            (
                "«Non abbiamo poco tempo, ma ne perdiamo molto.» Così inizia il trattato «Sulla brevità della vita» di Seneca.",
                "«Az zamanımız yok, fakat çoğunu boşa harcıyoruz.» Seneca'nın «Yaşamın Kısalığı Üzerine» eseri böyle başlar.",
                "\"It is not that we have little time, but that we waste much of it.\" Thus begins Seneca's 'On the Shortness of Life'.",
                "perdere = kaybetmek/harcamak | la brevità = kısalık | molto = çok",
                "perdere molto tempo",
                "çok zaman harcamak / waste time"
            ),
            (
                "Gli uomini difendono con ferocia il proprio denaro e le proprie terre, ma lasciano che chiunque rubi il loro tempo.",
                "İnsanlar paralarını ve topraklarını kıyasıya savunurlar ama herkesin zamanlarını çalmasına izin verirler.",
                "Men fiercely defend their money and land, yet allow anyone to steal their time.",
                "difendere = savunmak | lasciare che = izin vermek | rubare = çalmak",
                "difendere il tempo",
                "zamanı savunmak / guard time"
            ),
            (
                "Eppure il denaro perso si può riguadagnare, mentre nessuno ci restituirà mai un solo istante già trascorso.",
                "Oysa kaybedilen para geri kazanılabilir; fakat hiç kimse bize geçmiş olan tek bir anı bile geri vermeyecektir.",
                "Yet lost money can be regained, whereas no one will ever return to us a single moment already past.",
                "eppure = oysa/buna rağmen | restituire = geri vermek | l'istante = an",
                "un solo istante",
                "tek bir an / a single moment"
            ),
            (
                "A Luciano, che si lamenta delle mille preoccupazioni quotidiane, Seneca consiglia di distinguere l'essenziale dal superfluo.",
                "Binbir günlük kaygıdan yakınan Lucilius'a Seneca, özsel olanı gereksiz olandan ayırmasını öğütler.",
                "To Lucilius, who complains of a thousand daily worries, Seneca advises distinguishing the essential from the superfluous.",
                "lamentarsi di = yakınmak | la preoccupazione = kaygı | il superfluo = fazlalık/gereksiz",
                "l'essenziale e il superfluo",
                "özsel ve gereksiz / essential"
            ),
            (
                "«Soffriamo più spesso nell'immaginazione che nella realtà» scrive Seneca nelle «Lettere a Lucilio».",
                "«Gerçeklikten çok hayal gücümüzde acı çekeriz» diye yazar Seneca «Lucilius'a Ahlak Mektupları»nda.",
                "\"We suffer more often in imagination than in reality,\" Seneca writes in 'Letters to Lucilius'.",
                "più spesso = daha sık | l'immaginazione = hayal gücü | soffrire = acı çekmek",
                "nell'immaginazione",
                "hayal gücünde / in imagination"
            ),
            (
                "Un secolo più tardi, lungo il fiume Danubio gelato, l'imperatore Marco Aurelio scrive di notte nella sua tenda militare.",
                "Bir yüzyıl sonra, donmuş Tuna nehri boyunca İmparator Marcus Aurelius geceleyin askeri çadırında yazı yazar.",
                "A century later, along the frozen Danube river, Emperor Marcus Aurelius writes at night in his military tent.",
                "gelato = donmuş | la tenda = çadır | più tardi = daha sonra",
                "nella tenda militare",
                "askeri çadırda / military tent"
            ),
            (
                "L'uomo più potente del mondo non scrive per il pubblico, ma intitola il suo quaderno «A se stesso» (Colloqui con sé).",
                "Dünyanın en güçlü insanı halk için yazmaz; defterine «Kendime Düşünceler» (A se stesso) başlığını koyar.",
                "The most powerful man in the world does not write for the public, but titles his notebook 'To Himself' (Meditations).",
                "potente = güçlü | il pubblico = halk/okur | a se stesso = kendisine",
                "scrivere a se stesso",
                "kendine yazmak / to oneself"
            ),
            (
                "«Quando ti svegli al mattino, pensa a quale prezioso privilegio è essere vivi: respirare, pensare, provare gioia.»",
                "«Sabah uyandığında hayatta olmanın ne değerli bir ayrıcalık olduğunu düşün: nefes almak, düşünmek, sevinç duymak.»",
                "\"When you wake up in the morning, think of what a precious privilege it is to be alive: to breathe, to think, to feel joy.\"",
                "svegliarsi = uyanmak | il privilegio = ayrıcalık | provare gioia = sevinç duymak",
                "un prezioso privilegio",
                "değerli bir ayrıcalık"
            ),
            (
                "Se un evento esterno ti turba, ricorda che il dolore non viene dalla cosa in sé, ma dal giudizio che tu ne dai.",
                "Dışsal bir olay seni sarsarsa, acının şeyin kendisinden değil, senin ona verdiğin yargıdan geldiğini hatırla.",
                "If an external event disturbs you, remember that the pain comes not from the thing itself, but from your judgment of it.",
                "esterno = dışsal | turbare = sarsmak/üzmek | il giudizio = yargı",
                "il nostro giudizio",
                "bizim yargımız / our judgment"
            ),
            (
                "«Gli uomini non hanno il potere di ritirarsi in campagna in ogni momento, ma tu puoi sempre ritirarti dentro te stesso.»",
                "«İnsanların her an kırsala çekilme gücü yoktur, fakat sen her zaman kendi içine çekilebilirsin.»",
                "\"Men cannot retreat to the countryside at every moment, but you can always retreat within yourself.\"",
                "ritirarsi = çekilmek | la campagna = kırsal | dentro te stesso = kendi içine",
                "dentro te stesso",
                "kendi içine / within yourself"
            ),
            (
                "Questa «cittadella interiore» (la rocca della mente) resta libera anche quando fuori soffia la tempesta.",
                "Bu «içsel kale» (zihnin hisarı), dışarıda fırtına estiğinde bile özgür kalır.",
                "This 'inner citadel' (the fortress of the mind) remains free even when the storm blows outside.",
                "interiore = içsel | la rocca = hisar/kale | soffiare = esmek",
                "la cittadella interiore",
                "içsel kale / inner citadel"
            ),
            (
                "Quando incontri qualcuno ingrato o arrogante, non arrabbiarti: agisce così perché ignora il vero bene.",
                "Nankör veya kibirli biriyle karşılaştığında öfkelenme: gerçek iyiyi bilmediği için öyle davranıyordur.",
                "When you meet someone ungrateful or arrogant, do not get angry: they act so because they ignore the true good.",
                "ingrato = nankör | arrabbiarsi = öfkelenmek | agire (agisce) = davranmak",
                "non arrabbiarti",
                "öfkelenme / do not get angry"
            ),
            (
                "«La migliore vendetta» conclude Marco Aurelio «è non assomigliare a chi ti ha fatto un torto.»",
                "«En iyi intikam» diye tamamlar Marcus Aurelius, «sana haksızlık edene benzememektir.»",
                "\"The best revenge,\" concludes Marcus Aurelius, \"is not to be like the one who wronged you.\"",
                "la vendetta = intikam | assomigliare a = benzemek | il torto = haksızlık",
                "la migliore vendetta",
                "en iyi intikam / best revenge"
            ),
            (
                "La calma stoica non è freddezza del cuore: è lucidità della mente che agisce con giustizia nel presente.",
                "Stoacı dinginlik kalbin soğukluğu değildir: şimdiki zamanda adaletle hareket eden zihnin berraklığıdır.",
                "Stoic calm is not coldness of heart: it is clarity of mind acting with justice in the present.",
                "la freddezza = soğukluk | la lucidità = berraklık | la giustizia = adalet",
                "lucidità della mente",
                "zihin berraklığı / clear mind"
            ),
        ],
    },
    # 10. Venezia e il Mare (A2)
    {
        "title": "10. Venezia e il Mare (A2)",
        "subtitle": "A2 | Venedik Lagünü, Köprüler ve Deniz Tarihi",
        "level": "A2",
        "segments": [
            (
                "Chi arriva a Venezia per la prima volta scopre una città unica al mondo, dove le strade sono fatte d'acqua.",
                "Venedik'e ilk kez gelen kişi, caddelerin sudan yapıldığı dünyada eşi benzeri olmayan bir şehir keşfeder.",
                "Whoever arrives in Venice for the first time discovers a unique city in the world, where streets are made of water.",
                "unico = eşsiz/benzersiz | la strada = cadde/yol | fatto di = ...-den yapılmış",
                "unico al mondo",
                "dünyada eşsiz / unique in world"
            ),
            (
                "Qui non si sentono automobili o clacson, ma solo il rumore delle onde contro la pietra e i passi sui ponti.",
                "Burada otomobil veya korna sesi duyulmaz; yalnızca dalgaların taşa çarpan sesi ve köprülerdeki ayak sesleri duyulur.",
                "Here you hear no cars or horns, only the sound of waves against stone and footsteps on bridges.",
                "il rumore = ses/gürültü | l'onda = dalga | il passo = ayak adımı",
                "il rumore delle onde",
                "dalgaların sesi / sound of waves"
            ),
            (
                "La città è costruita su più di cento piccole isole nella laguna, collegate da oltre quattrocento ponti.",
                "Şehir, lagündeki yüzden fazla küçük ada üzerine kurulmuş ve dört yüzden fazla köprüyle birbirine bağlanmıştır.",
                "The city is built on more than a hundred small islands in the lagoon, linked by over four hundred bridges.",
                "l'isola = ada | collegato = birbirine bağlı | oltre = ...-den fazla",
                "oltre quattrocento ponti",
                "400'den fazla köprü / bridges"
            ),
            (
                "Sotto i palazzi di marmo si nasconde una foresta invisibile: milioni di pali di legno piantati nel fango.",
                "Mermer sarayların altında görünmez bir orman gizlidir: çamura çakılmış milyonlarca ahşap kazık.",
                "Beneath the marble palaces hides an invisible forest: millions of wooden piles driven into the mud.",
                "nascondersi = gizlenmek | il palo = kazık/direk | il marmo = mermer",
                "sotto i palazzi",
                "sarayların altında / beneath"
            ),
            (
                "Senza ossigeno sotto l'acqua salata, il legno delle Alpi non marcisce mai, ma diventa duro come la roccia.",
                "Tuzlu suyun altında oksijen olmadan Alplerin ahşabı asla çürümez, aksine kaya gibi sertleşir.",
                "Without oxygen under the salt water, the Alpine wood never rots, but becomes as hard as rock.",
                "salato = tuzlu | marcire = çürümek | duro come = ... kadar sert",
                "duro come la roccia",
                "kaya gibi sert / hard as rock"
            ),
            (
                "Prendiamo il vaporetto lungo il Canal Grande e passiamo sotto l'arco elegante del Ponte di Rialto.",
                "Büyük Kanal (Canal Grande) boyunca vapura biniyor ve Rialto Köprüsü'nün zarif kemerinin altından geçiyoruz.",
                "We take the waterbus along the Grand Canal and pass under the elegant arch of the Rialto Bridge.",
                "il vaporetto = Venedik vapuru | l'arco = kemer | passare sotto = altından geçmek",
                "lungo il Canal Grande",
                "Büyük Kanal boyunca / along"
            ),
            (
                "Per mille anni la Repubblica di Venezia, chiamata «La Serenissima», è stata la porta tra l'Europa e l'Oriente.",
                "Bin yıl boyunca «La Serenissima» olarak adlandırılan Venedik Cumhuriyeti, Avrupa ile Doğu arasındaki kapı olmuştur.",
                "For a thousand years the Republic of Venice, called 'La Serenissima', was the gateway between Europe and the East.",
                "chiamato = adlandırılan | la porta = kapı | l'Oriente = Doğu/Şark",
                "tra l'Europa e l'Oriente",
                "Avrupa ve Doğu arasında"
            ),
            (
                "Le navi veneziane partivano dall'Arsenale e tornavano da Costantinopoli e Alessandria cariche di spezie e seta.",
                "Venedik gemileri Tersane'den (Arsenale) yola çıkar, Konstantinopolis ve İskenderiye'den baharat ve ipek yüklü dönerdi.",
                "Venetian ships sailed from the Arsenale and returned from Constantinople and Alexandria laden with spices and silk.",
                "la nave = gemi | carico di = ... ile yüklü | la seta = ipek",
                "carico di spezie",
                "baharat yüklü / laden w/ spices"
            ),
            (
                "Anche nei palazzi veneziani si vede questo incontro di culture: archi bizantini, marmi orientali e luce gotica.",
                "Venedik saraylarında da bu kültür buluşması görülür: Bizans kemerleri, Doğu mermerleri ve Gotik ışık.",
                "In Venetian palaces too one sees this meeting of cultures: Byzantine arches, Eastern marbles, and Gothic light.",
                "l'incontro = buluşma/karşılaşma | anche = de/da | vedere (si vede) = görülmek",
                "incontro di culture",
                "kültürlerin buluşması / meeting"
            ),
            (
                "Verso sera entriamo in un «bacaro», una tipica osteria veneziana, per assaggiare i famosi «cicchetti».",
                "Akşama doğru ünlü «cicchetti» mezelerinin tadına bakmak için tipik bir Venedik meyhanesi olan «bacaro»ya giriyoruz.",
                "Toward evening we enter a 'bacaro', a typical Venetian wine bar, to taste the famous 'cicchetti' tapas.",
                "tipico = tipik/özgü | assaggiare = tatmak | verso sera = akşama doğru",
                "entrare in un bacaro",
                "bir meyhaneye girmek / tavern"
            ),
            (
                "I cicchetti sono fette di pane con baccalà mantecato, sarde in saor o carciofi, accompagnati da un bicchiere di vino.",
                "Cicchetti; krema kıvamında morina balığı, marine sardalya veya enginarlı ekmek dilimleridir ve bir kadeh şarapla sunulur.",
                "Cicchetti are slices of bread with creamed cod, marinated sardines, or artichokes, paired with a glass of wine.",
                "la fetta = dilim | il carciofo = enginar | accompagnato = eşliğinde",
                "una fetta di pane",
                "bir dilim ekmek / bread slice"
            ),
            (
                "Di notte, quando i turisti partono, le calli silenziose di Venezia si riempiono di una nebbia leggera.",
                "Geceleyin turistler ayrıldığında, Venedik'in sessiz dar sokakları (calli) hafif bir sisle dolar.",
                "At night, when tourists leave, the silent alleys of Venice fill with a light mist.",
                "la calle = Venedik dar sokağı | silenzioso = sessiz | la nebbia = sis",
                "una nebbia leggera",
                "hafif bir sis / a light mist"
            ),
            (
                "I lampioni si riflettono sull'acqua scura dei canali e il tempo sembra essersi fermato al Settecento.",
                "Sokak lambaları kanalların koyu suyuna yansır ve zaman 18. yüzyılda durmuş gibi görünür.",
                "Streetlamps reflect on the dark water of the canals and time seems to have stopped in the 18th century.",
                "il lampione = sokak lambası | riflettersi = yansımak | scuro = koyu",
                "il tempo si è fermato",
                "zaman durdu / time stopped"
            ),
            (
                "Camminando senza mappa tra i ponti, capisci che a Venezia perdersi è il modo più bello per trovare la città.",
                "Köprüler arasında haritasız yürürken, Venedik'te kaybolmanın şehri bulmanın en güzel yolu olduğunu anlarsın.",
                "Walking without a map among the bridges, you understand that in Venice getting lost is the best way to find the city.",
                "senza mappa = haritasız | perdersi = kaybolmak | capire (capisci) = anlamak",
                "perdersi a Venezia",
                "Venedik'te kaybolmak / get lost"
            ),
        ],
    },
    # 11. L'Arte della Conversazione (A2)
    {
        "title": "11. L'Arte della Conversazione (A2)",
        "subtitle": "A2 | İtalyancada Sohbet Sanatı ve Bağlaçlar",
        "level": "A2",
        "segments": [
            (
                "In Italia una cena tra amici non è solo un momento per mangiare, ma un vero teatro della conversazione.",
                "İtalya'da dostlar arasındaki bir akşam yemeği sadece yemek yeme anı değil, gerçek bir sohbet tiyatrosudur.",
                "In Italy a dinner among friends is not just a time to eat, but a true theater of conversation.",
                "la cena = akşam yemeği | tra amici = dostlar arasında | vero = gerçek",
                "una cena tra amici",
                "dostlarla akşam yemeği / dinner"
            ),
            (
                "Per parlare in modo naturale, gli italiani usano piccole parole che danno ritmo e sfumatura a ogni frase.",
                "Doğal bir biçimde konuşmak için İtalyanlar her cümleye ritim ve incelik katan küçük kelimeler kullanırlar.",
                "To speak naturally, Italians use small words that give rhythm and nuance to every sentence.",
                "in modo naturale = doğal biçimde | dare ritmo = ritim vermek | ogni = her",
                "in modo naturale",
                "doğal bir şekilde / naturally"
            ),
            (
                "La parola più famosa è «allora»: serve per iniziare un discorso, per riassumere o per prendere tempo.",
                "En ünlü kelime «allora»dır (öyleyse/peki/şimdi): bir konuşmaya başlamak, özetlemek veya zaman kazanmak için kullanılır.",
                "The most famous word is 'allora': it serves to begin a speech, to summarize, or to buy time.",
                "allora = öyleyse/şimdi | il discorso = konuşma | prendere tempo = zaman kazanmak",
                "Allora, iniziamo!",
                "Öyleyse başlayalım! / Let's start"
            ),
            (
                "«Allora, cosa facciamo stasera?» chiede Marco mentre apparecchia la tavola sul balcone.",
                "«Ee, bu akşam ne yapıyoruz?» diye soruyor Marco balkonda sofrayı kurarken.",
                "\"So, what are we doing tonight?\" asks Marco while setting the table on the balcony.",
                "stasera = bu akşam | apparecchiare = sofrayı kurmak | il balcone = balkon",
                "apparecchiare la tavola",
                "sofrayı kurmak / set the table"
            ),
            (
                "Quando vogliamo esprimere un contrasto gentile, usiamo «invece» oppure «però»: «Io resto qui; tu invece vai?»",
                "Nazik bir karşıtlık ifade etmek istediğimizde «invece» (aksine/ise) veya «però» (fakat) kullanırız: «Ben kalıyorum; sen ise gidiyor musun?»",
                "When we want to express a gentle contrast, we use 'invece' or 'però': \"I'm staying here; are you going instead?\"",
                "esprimere = ifade etmek | invece = ise/aksine | però = fakat/ama",
                "tu invece...",
                "sen ise... / whereas you..."
            ),
            (
                "Un'altra parola preziosa è «magari»: può significare «forse», ma da sola significa «quanto sarebbe bello!»",
                "Değerli bir diğer kelime «magari»dir: «belki» anlamına gelebilir ama tek başına «keşke, ne güzel olurdu!» demektir.",
                "Another precious word is 'magari': it can mean 'maybe', but on its own it means 'if only / I wish!'",
                "magari = keşke/belki | significare = anlamına gelmek | da solo = tek başına",
                "Magari!",
                "Keşke! Ne güzel olurdu! / I wish"
            ),
            (
                "«Vieni anche tu in Sicilia ad agosto?» «Magari! Purtroppo devo finire la tesi di laurea.»",
                "«Ağustosta sen de Sicilya'ya geliyor musun?» «Keşke! Maalesef mezuniyet tezimi bitirmem gerekiyor.»",
                "\"Are you coming to Sicily in August too?\" \"I wish! Unfortunately I have to finish my degree thesis.\"",
                "purtroppo = maalesef | la tesi di laurea = mezuniyet tezi | dovere = zorunda olmak",
                "Purtroppo devo...",
                "Maalesef ...-meliyim / Sadly"
            ),
            (
                "Per mostrare accordo e interesse mentre l'altro parla, si dice «certo», «esatto», «hai voglia!» o «eccome!»",
                "Karşıdaki konuşurken onay ve ilgi göstermek için «certo» (tabii), «esatto» (kesinlikle) veya «eccome!» (hem de nasıl!) denir.",
                "To show agreement and interest while the other speaks, one says 'certo', 'esatto', or 'eccome!' (and how!).",
                "l'accordo = uyum/onay | esatto = tam öyle | eccome = hem de nasıl",
                "Esatto, proprio così!",
                "Kesinlikle, tam öyle! / Exactly"
            ),
            (
                "Quando invece vogliamo cambiare argomento o chiudere un dubbio, diciamo «comunque» oppure «insomma».",
                "Konuyu değiştirmek veya bir tereddüdü kapatmak istediğimizde ise «comunque» (her neyse) veya «insomma» (kısacası) deriz.",
                "When instead we want to change the subject or close a doubt, we say 'comunque' (anyway) or 'insomma' (in short).",
                "l'argomento = konu | il dubbio = şüphe | comunque = her neyse/yine de",
                "cambiare argomento",
                "konuyu değiştirmek / topic"
            ),
            (
                "«Il treno era in ritardo e pioveva forte; comunque, alla fine siamo arrivati sani e salvi.»",
                "«Tren gecikmişti ve şiddetli yağmur yağıyordu; her neyse, sonunda sağ salim vardık.»",
                "\"The train was late and it was raining hard; anyway, in the end we arrived safe and sound.\"",
                "in ritardo = gecikmeli | forte = şiddetli | sano e salvo = sağ salim",
                "sani e salvi",
                "sağ salim / safe and sound"
            ),
            (
                "E i famosi gesti delle mani? Non sostituiscono le parole, ma disegnano nell'aria la melodia del pensiero.",
                "Ya ünlü el hareketleri? Kelimelerin yerini almazlar; düşüncenin melodisini havada çizerler.",
                "And the famous hand gestures? They do not replace words, but draw the melody of thought in the air.",
                "il gesto = el hareketi/jest | sostituire = yerini almak | il pensiero = düşünce",
                "i gesti delle mani",
                "el hareketleri / hand gestures"
            ),
            (
                "Per dire «non mi importa» o «chi lo sa?», basta alzare leggermente le spalle e aprire il palmo delle mani.",
                "«Umurumda değil» veya «kim bilir?» demek için omuzları hafifçe kaldırmak ve avuç içlerini açmak yeterlidir.",
                "To say 'I don't care' or 'who knows?', it is enough to shrug slightly and open the palms of your hands.",
                "importare = önemli olmak | alzare le spalle = omuz silkmek | il palmo = avuç içi",
                "alzare le spalle",
                "omuz silkmek / shrug shoulders"
            ),
            (
                "Ma il segreto più importante di ogni buona conversazione resta sempre lo stesso: saper ascoltare davvero.",
                "Fakat her iyi sohbetin en önemli sırrı her zaman aynı kalır: gerçekten dinlemeyi bilmek.",
                "But the most important secret of every good conversation always remains the same: knowing how to truly listen.",
                "il segreto = sır | lo stesso = aynı | saper ascoltare = dinlemeyi bilmek",
                "saper ascoltare",
                "dinlemeyi bilmek / listen well"
            ),
            (
                "Alla fine della serata ci salutiamo sulla porta: «Grazie di tutto, ci sentiamo presto! Buonanotte!»",
                "Gecenin sonunda kapıda vedalaşıyoruz: «Her şey için teşekkürler, yakında haberleşiriz! İyi geceler!»",
                "At the end of the evening we say goodbye at the door: \"Thanks for everything, talk to you soon! Goodnight!\"",
                "la serata = akşam vakti | grazie di tutto = her şey için teşekkürler | ci sentiamo = haberleşiriz",
                "Ci sentiamo presto!",
                "Yakında haberleşiriz! / Talk soon"
            ),
        ],
    },
    # 12. Camus in Italia: Il Deserto e l'Arte (B2)
    {
        "title": "12. Camus in Italia: Il Deserto e l'Arte (B2)",
        "subtitle": "B2 | Albert Camus Floransa'da: Sanat ve Varoluş",
        "level": "B2",
        "segments": [
            (
                "Nel 1937 il giovane Albert Camus viaggia per la prima volta in Italia e annota le sue riflessioni nel saggio «Il deserto».",
                "1937'de genç Albert Camus ilk kez İtalya'ya seyahat eder ve düşüncelerini «Çöl» (Il deserto) başlıklı denemesine kaydeder.",
                "In 1937 the young Albert Camus travels to Italy for the first time and records his reflections in the essay 'The Desert'.",
                "annotare = not düşmek | la riflessione = düşünce/tefekkür | il deserto = çöl",
                "annotare le riflessioni",
                "düşünceleri not etmek / note"
            ),
            (
                "Camminando per le vie di Pisa e di Firenze, Camus osserva una civiltà che ha saputo unire la bellezza e la lucidità.",
                "Pisa ve Floransa sokaklarında yürürken Camus, güzellik ile zihin berraklığını birleştirmeyi bilmiş bir uygarlığı gözlemler.",
                "Walking through the streets of Pisa and Florence, Camus observes a civilization that united beauty and lucidity.",
                "la civiltà = uygarlık | unire = birleştirmek | la bellezza = güzellik",
                "unire bellezza e lucidità",
                "güzellik ve berraklığı birleştirmek"
            ),
            (
                "Nei dipinti di Giotto, di Piero della Francesca e dei maestri toscani, le figure non cercano consolazioni illusorie.",
                "Giotto, Piero della Francesca ve Toskanalı ustaların tablolarında figürler aldatıcı teselliler aramazlar.",
                "In the paintings of Giotto, Piero della Francesca, and the Tuscan masters, figures seek no illusory consolations.",
                "la consolazione = teselli | illusorio = aldatıcı/hayalî | il maestro = usta",
                "consolazioni illusorie",
                "aldatıcı teselliler / illusions"
            ),
            (
                "Quei volti dipinti accettano il proprio destino senza illusioni: in loro vive una fiera «indifferenza» piena di dignità.",
                "O resmedilmiş yüzler kendi yazgılarını yanılsamasız kabul ederler: onlarda onurla dolu vakur bir dinginlik yaşar.",
                "Those painted faces accept their destiny without illusions: in them lives a proud composure full of dignity.",
                "il destino = kader/yazgı | senza illusioni = yanılsamasız | la dignità = onur/vakar",
                "senza illusioni",
                "yanılsamasız / without illusions"
            ),
            (
                "Per Camus, l'assurdo nasce dall'incontro tra la nostra sete di eterno e il silenzio ragionevole del mondo.",
                "Camus için «absürt», bizim sonsuzluk susuzluğumuz ile dünyanın makul sessizliği arasındaki karşılaşmadan doğar.",
                "For Camus, the absurd is born from the encounter between our thirst for eternity and the world's silence.",
                "l'assurdo = absürt/uyumsuz | la sete = susuzluk | l'eterno = sonsuzluk",
                "la sete di eterno",
                "sonsuzluk susuzluğu / eternity"
            ),
            (
                "Di fronte a questo silenzio, l'uomo non deve fuggire nella disperazione né chiudere gli occhi davanti al reale.",
                "Bu sessizlik karşısında insan ne umutsuzluğa kaçmalı ne de gerçekliğin önünde gözlerini kapatmalıdır.",
                "Faced with this silence, man must neither flee into despair nor close his eyes before reality.",
                "di fronte a = karşısında | fuggire = kaçmak | la disperazione = umutsuzluk",
                "non chiudere gli occhi",
                "gözlerini kapatmamak / stay open"
            ),
            (
                "Al contrario, proprio quando riconosciamo i nostri limiti, il mondo terreno riacquista tutta la sua densità luminosa.",
                "Tam tersine, sınırlarımızı tanıdığımız anda yeryüzü dünyası tüm o aydınlık yoğunluğunu yeniden kazanır.",
                "On the contrary, precisely when we recognize our limits, the earthly world regains all its luminous density.",
                "al contrario = tam tersine | il limite = sınır | riacquistare = yeniden kazanmak",
                "riconoscere i limiti",
                "sınırları tanımak / know limits"
            ),
            (
                "Nel chiostro silenzioso della basilica della Santissima Annunziata a Firenze, Camus legge le iscrizioni sulle tombe.",
                "Floransa'daki Santissima Annunziata bazilikasının sessiz revak avlusu içinde Camus mezar taşlarındaki yazıtları okur.",
                "In the silent cloister of the Santissima Annunziata basilica in Florence, Camus reads the tomb inscriptions.",
                "il chiostro = manastır avlusu | l'iscrizione = yazıt | la tomba = mezar",
                "nel chiostro silenzioso",
                "sessiz avluda / silent cloister"
            ),
            (
                "Fuori dai muri del chiostro, intanto, i ragazzi fiorentini ridono al sole e le rondini tagliano il cielo azzurro.",
                "Bu sırada revak duvarlarının dışında Floransalı gençler güneşin altında güler ve kırlangıçlar mavi gökyüzünü yarar.",
                "Outside the cloister walls, meanwhile, Florentine youths laugh in the sun and swallows cleave the blue sky.",
                "intanto = bu sırada | la rondine = kırlangıç | tagliare = kesmek/yarmak",
                "ridere al sole",
                "güneşte gülmek / laugh in sun"
            ),
            (
                "L'Italia mediterranea insegna a Camus il «pensiero meridiano»: il senso della misura contro ogni fanatismo.",
                "Akdeniz İtalyası Camus'ye «güney düşüncesini» (pensiero meridiano) öğretir: her türlü fanatizme karşı ölçü duygusu.",
                "Mediterranean Italy teaches Camus 'meridian thought': a sense of measure against every fanaticism.",
                "meridiano = güneye özgü/öğle | la misura = ölçü/denge | contro = karşı",
                "il senso della misura",
                "ölçü duygusu / sense of measure"
            ),
            (
                "Salendo sulla collina di Fiesole sopra Firenze, lo sguardo abbraccia i tetti rossi, l'Arno e gli ulivi argentei.",
                "Floransa'nın üzerindeki Fiesole tepesine çıkarken bakışlar kırmızı çatıları, Arno'yu ve gümüşi zeytin ağaçlarını kucaklar.",
                "Climbing the hill of Fiesole above Florence, one's gaze embraces red roofs, the Arno, and silvery olive trees.",
                "lo sguardo = bakış | abbracciare = kucaklamak | l'ulivo = zeytin ağacı",
                "lo sguardo abbraccia",
                "bakışlar kucaklar / gaze holds"
            ),
            (
                "Qui la bellezza non promette un altro mondo: chiede soltanto la nostra presenza lucida e appassionata nell'oggi.",
                "Burada güzellik başka bir dünya vaat etmez; yalnızca bugünün içinde bizim berrak ve tutkulu varlığımızı ister.",
                "Here beauty does not promise another world: it asks only for our lucid and passionate presence in today.",
                "promettere = vaat etmek | soltanto = yalnızca | la presenza = varlık/mevcudiyet",
                "presenza lucida",
                "berrak mevcudiyet / clear mind"
            ),
            (
                "Come Sisifo che spinge la sua pietra sulla montagna, l'uomo libero trasforma la fatica in consapevolezza.",
                "Kayasını dağa doğru iten Sisifos gibi özgür insan da emeği ve zahmeti bilince dönüştürür.",
                "Like Sisyphus pushing his stone up the mountain, the free human transforms toil into awareness.",
                "spingere = itmek | la fatica = zahmet/emek | la consapevolezza = bilinç/farkındalık",
                "trasformare la fatica",
                "emeği dönüştürmek / transform"
            ),
            (
                "«Non c'è amore di vivere senza disperazione di vivere» scrive Camus: ed è da questa verità che nasce il coraggio.",
                "«Yaşama umutsuzluğu olmadan yaşama sevgisi olmaz» diye yazar Camus; ve cesaret işte bu hakikatten doğar.",
                "\"There is no love of life without despair of life,\" writes Camus: and from this truth courage is born.",
                "l'amore di vivere = yaşama sevgisi | la verità = hakikat | il coraggio = cesaret",
                "l'amore di vivere",
                "yaşama sevgisi / love of life"
            ),
        ],
    },
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    assert len(TEXTS) == 12, f"Expected 12 texts, got {len(TEXTS)}"

    total_segments = sum(len(t["segments"]) for t in TEXTS)
    print(f"Building {OUT_PATH}: {len(TEXTS)} texts, {total_segments} total segments")

    for t in TEXTS:
        if len(t["subtitle"].encode("utf-8")) >= 48:
            t["subtitle"] = t["subtitle"].split(" ve ")[0]
        new_segs = []
        for it, tr, en, vn, cf, cb in t["segments"]:
            if len(cb.encode("utf-8")) >= 32 and " / " in cb:
                tr_part, en_part = cb.split(" / ", 1)
                en_words = en_part.split()
                while en_words and len((tr_part + " / " + " ".join(en_words)).encode("utf-8")) >= 32:
                    en_words.pop()
                cb = (tr_part + " / " + " ".join(en_words)) if en_words else tr_part
            if len(cb.encode("utf-8")) >= 32:
                cb = cb.encode("utf-8")[:31].decode("utf-8", errors="ignore").rsplit(" ", 1)[0]
            new_segs.append((it, tr, en, vn, cf, cb))
        t["segments"] = new_segs

    # Verify all string lengths strictly fit inside struct limits
    for t in TEXTS:
        assert len(t["title"].encode("utf-8")) < 48, f"Title too long: {t['title']}"
        assert len(t["subtitle"].encode("utf-8")) < 48, f"Subtitle too long ({len(t['subtitle'].encode('utf-8'))}B): {t['subtitle']}"
        assert len(t["level"].encode("utf-8")) < 8, f"Level too long: {t['level']}"
        for idx, seg in enumerate(t["segments"]):
            it, tr, en, vn, cf, cb = seg
            assert len(it.encode("utf-8")) < 220, f"Italian too long ({len(it.encode('utf-8'))}B) in {t['title']}#{idx}"
            assert len(tr.encode("utf-8")) < 220, f"Turkish too long ({len(tr.encode('utf-8'))}B) in {t['title']}#{idx}"
            assert len(en.encode("utf-8")) < 160, f"English too long ({len(en.encode('utf-8'))}B) in {t['title']}#{idx}"
            assert len(vn.encode("utf-8")) < 104, f"vocabNotes too long ({len(vn.encode('utf-8'))}B) in {t['title']}#{idx}: {vn}"
            assert len(cf.encode("utf-8")) < 32, f"cardFront too long ({len(cf.encode('utf-8'))}B) in {t['title']}#{idx}: {cf}"
            assert len(cb.encode("utf-8")) < 32, f"cardBack too long ({len(cb.encode('utf-8'))}B) in {t['title']}#{idx}: {cb}"

    out = bytearray()
    # Header (16 bytes): char magic[8] = "CNBL0001", uint16_t textCount, uint16_t totalSegments, uint32_t reserved = 0
    out += struct.pack("<8sHHI", b"CNBL0001", len(TEXTS), total_segments, 0)
    assert len(out) == 16

    # Text Metadata Table (textCount * 128 bytes)
    first_seg = 0
    for t in TEXTS:
        seg_cnt = len(t["segments"])
        meta = bytearray()
        meta += pack_utf8(t["title"], 48)
        meta += pack_utf8(t["subtitle"], 48)
        meta += pack_utf8(t["level"], 8)
        meta += struct.pack("<HH20s", first_seg, seg_cnt, b"\x00" * 20)
        assert len(meta) == 128
        out += meta
        first_seg += seg_cnt

    assert len(out) == 16 + 12 * 128

    # Segment Records (totalSegments * 768 bytes)
    for t in TEXTS:
        for it, tr, en, vn, cf, cb in t["segments"]:
            srec = bytearray()
            srec += pack_utf8(it, 220)
            srec += pack_utf8(tr, 220)
            srec += pack_utf8(en, 160)
            srec += pack_utf8(vn, 104)
            srec += pack_utf8(cf, 32)
            srec += pack_utf8(cb, 32)
            assert len(srec) == 768
            out += srec

    expected_size = 16 + 12 * 128 + total_segments * 768
    assert len(out) == expected_size

    with open(OUT_PATH, "wb") as f:
        f.write(out)

    print(f"Successfully wrote {OUT_PATH}: {len(out)} bytes")

if __name__ == "__main__":
    main()
