#!/usr/bin/env python3
import os
import struct

WP_IDX_PATH = "./sd_out"
OUT_DIR = "./sd_out"
OUT_PATH = os.path.join(OUT_DIR, "arguments.bin")

def load_wp_titles():
    with open(WP_IDX_PATH, "rb") as f:
        b = f.read()
    num_pages = int.from_bytes(b[12:16], "little")
    titles = set()
    for p in range(num_pages):
        page_start = 32 + p * 4096
        cnt = int.from_bytes(b[page_start:page_start+2], "little")
        off = page_start + 2
        prev = b""
        for _ in range(cnt):
            plen = b[off]
            slen = b[off+1]
            s = b[off+8:off+8+slen]
            cur = prev[:plen] + s
            prev = cur
            titles.add(cur.decode("utf-8", errors="ignore"))
            off += 8 + slen
    return titles

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

ARGUMENTS = [
    # 1. Parmenides & Zeno
    {
        "era": "ELEATIC • PARMENIDES & ZENO",
        "title": "Illusion of Motion (Hareketin İmkânsızlığı)",
        "wiki": "Parmenides",
        "p1": "Bir okun A'dan B'ye ulaşması için önce yolun yarısını, sonra kalanın yarısını sonsuz kez geçmesi gerekir.",
        "p2": "Sonlu bir zaman dilimi içinde gerçek anlamda sonsuz sayıda ardışık mesafe adımı tamamlanamaz.",
        "p3": "Duyularımız hareketi gösterse de mantıksal çelişki içeren şey gerçek varlığa (Being) ait olamaz.",
        "conc": "O halde değişim ve hareket duyusal bir yanılsamadır; Varlık bölünmez, değişmez vebirdir.",
        "obj": [
            "Ok havada rüzgar direnci yüzünden yavaşlar.",
            "Sonsuz sayıda azalan terimin toplamı (1/2 + 1/4 + 1/8...) sonlu bir sayıya ve zamana yakınsar.",
            "Eski Yunan'da yaylar yeterince güçlü değildi.",
        ],
        "best": 1,
        "analysis": (
            "P2 öncülü, sonsuz bölünebilir bir mesafenin aşılmasının sonsuz zaman gerektireceğini varsayar. "
            "Aristoteles potansiyel/aktüel sonsuz ayrımıyla, modern kalkülüs ise yakınsak geometrik serilerle "
            "sonsuz alt-aralığın sonlu zamanda geçilebildiğini göstermiştir."
        ),
    },
    # 2. Socrates / Plato - Euthyphro
    {
        "era": "CLASSICAL ATHENS • SOCRATES",
        "title": "Euthyphro Dilemma (Euthyphron İkilemi)",
        "wiki": "Socrates",
        "p1": "Ahlaki olarak iyi olan ya tanrılar onu buyurduğu için iyidir ya da zaten iyi olduğu için buyrulur.",
        "p2": "Eğer sadece buyrulduğu için iyiyse, iyilik keyfidir; zalimlik buyrulsa o da 'iyi' sayılırdı.",
        "p3": "Eğer zaten iyi olduğu için buyruluyorsa, iyiliğin ölçütü tanrıların iradesinden bağımsızdır.",
        "conc": "O halde ahlak ya keyfi bir güce indirgenir ya da ilahi iradeden bağımsız akılsal bir temele dayanır.",
        "obj": [
            "Euthyphro mahkemeye geç kaldığı için tartışmayı bitirmiştir.",
            "İyilik ne keyfi buyruk ne de dışsal bir standarttır; bizzat mükemmel varlığın değişmez doğasıdır.",
            "Atina yasaları yazılı olduğu için ikilem geçersizdir.",
        ],
        "best": 1,
        "analysis": (
            "Klasik teizm (Aquinas) P1'deki ikilemin eksik olduğunu savunur: Üçüncü bir seçenek olarak iyilik "
            "Tanrı'nın keyfi bir kararı değil, O'nun rasyonel ve değişmez özünün ifadesidir. Seküler etik ise "
            "ikinci boynuzu seçerek özerk ahlakı temellendirir."
        ),
    },
    # 3. Plato - Theory of Forms
    {
        "era": "PLATONISM • PLATO",
        "title": "One Over Many (İdealar Kuramı)",
        "wiki": "Plato",
        "p1": "Duyusal dünyadaki tüm güzel, adil veya eşit nesneler kusurludur, değişkendir ve zamanla yok olur.",
        "p2": "Ancak zihnimiz değişmeyen, tam 'Eşitlik' ve 'Adalet' kavramlarını (tümeller) kesin olarak bilir.",
        "p3": "Değişmez ve kusursuz bilginin nesnesi, sürekli akan duyusal gölgeler dünyası olamaz.",
        "conc": "O halde duyuların ötesinde ezeli, değişmez ve akılla kavranan İdealar (Formlar) dünyası vardır.",
        "obj": [
            "Üçüncü İnsan Argümanı: Tekil insanlarla İnsan İdeası arasındaki benzerliği açıklamak için sonsuz yeni İdea gerekir.",
            "Mağaradaki ateş yeterince parlak değildir.",
            "Geometri sadece Mısırlı arazi ölçümcüleri için pratiktir.",
        ],
        "best": 0,
        "analysis": (
            "Platon'un Parmenides diyaloğunda bizzat tartıştığı ve Aristoteles'in geliştirdiği 'Üçüncü İnsan' "
            "(Tritos Anthropos) itirazı, tümelleri nesnelerden ayrı bir dünyaya koymanın sonsuz gerilemeye "
            "(infinite regress) yol açtığını gösterir."
        ),
    },
    # 4. Aristotle - Unmoved Mover & Eudaimonia
    {
        "era": "PERIPATETIC • ARISTOTLE",
        "title": "Ergon Argument (İnsanın İşlevi ve Eudaimonia)",
        "wiki": "Aristotle",
        "p1": "Her varlığın 'iyi' olması, kendine özgü işlevini (ergon) mükemmel biçimde (arete/erdemle) gerçekleştirmesidir.",
        "p2": "Beslenme bitkilerle, duyumsama hayvanlarla ortaktır; insana özgü ayırt edici işlev akılsal (logos) etkinliktir.",
        "p3": "Bir yaşamın en yüksek iyisi, o varlığın öz işlevini tam bir ömür boyu erdemle icra etmesidir.",
        "conc": "O halde insan için en yüksek iyi (Eudaimonia), ruhun akla ve erdeme uygun etkinliğidir.",
        "obj": [
            "Biyolojik olarak evrimleşmiş bir türün önceden belirlenmiş tek bir teleolojik 'işlevi' (ergon) olmak zorunda değildir.",
            "Atina'da zeytin hasadı kışın yapılır.",
            "Ruh sadece kalpte bulunur.",
        ],
        "best": 0,
        "analysis": (
            "Modern felsefe (ve varoluşçuluk) P1 ve P2'deki doğalcı teleolojiye itiraz eder: Bir bıçağın kesmek "
            "gibi yapımcı tarafından verilmiş işlevi vardır, ancak insan kendi amacını kendisi seçen bir varlıktır; "
            "'ayırt edici özellik' otomatik olarak 'ahlaki ödev' doğurmaz."
        ),
    },
    # 5. Epicurus - Tetrapharmakos & Death
    {
        "era": "HELLENISTIC • EPICURUS",
        "title": "Symmetry & Nothingness of Death (Ölüm Korkusu)",
        "wiki": "Epicurus",
        "p1": "Bir şeyin bizim için iyi ya da kötü olabilmesi için onu duyumsayacak bir öznenin var olması gerekir.",
        "p2": "Ölüm, atomların dağılmasıyla tüm duyumsamanın ve bilincin tamamen sona ermesidir.",
        "p3": "Biz varken ölüm yoktur; ölüm geldiğinde ise artık biz yokuzdur.",
        "conc": "O halde ölüm bizim için hiçbir şeydir; ölüm korkusu rasyonel temelden yoksundur.",
        "obj": [
            "Ölüm acı vermez ama kişiyi yaşayabileceği gelecekteki iyi deneyimlerden mahrum bırakır (Yoksunluk İtirazı).",
            "Atomlar sadece kare şeklindedir.",
            "Bahçe'de siyaset konuşmak zorunludur.",
        ],
        "best": 0,
        "analysis": (
            "Thomas Nagel ve çağdaş analitik filozoflar P1'deki 'deneyim koşuluna' (experience requirement) "
            "itiraz eder: Bir kötülük mutlaka o an hissedilen bir acı olmak zorunda değildir; yaşamın sunduğu "
            "olanakların kaybı (deprivation) kişi onu hissetmese de gerçek bir kayıptır."
        ),
    },
    # 6. Epictetus - Stoic Dichotomy
    {
        "era": "STOICISM • EPICTETUS",
        "title": "Dichotomy of Control (Kontrol İkiliği)",
        "wiki": "Stoicism",
        "p1": "Var olan her şey ikiye ayrılır: elimizde olanlar (yargılarımız, niyetlerimiz) ve elimizde olmayanlar (servet, ün, beden, ölüm).",
        "p2": "İnsanın acı çekmesinin ve köleleşmesinin tek nedeni, dışsal olayları kendi kontrolündeymiş veya mutlak iyiymiş gibi arzulamasıdır.",
        "p3": "Bilge kişi değer yargısını (prohairesis) yalnızca kendi iradesine bağlar ve dışsal olanı doğanın akışı olarak kabul eder.",
        "conc": "O halde içsel yargılarını yöneten kişi hiçbir dış tiran veya felaket tarafından sarsılamaz (Ataraxia).",
        "obj": [
            "Dışsal adaletsizliklere ve sevdiklerimizin acısına tamamen kayıtsız kalmak, insanlığı ve politik sorumluluğu aşındırır.",
            "Roma İmparatorluğu'nda vergiler düşüktü.",
            "Mantık çalışmak Stoacılar için yasaktır.",
        ],
        "best": 0,
        "analysis": (
            "Aristotelesçi ve modern eleştirmenler P2-P3'e itiraz eder: Tam sarsılmazlık (apatheia) uğruna "
            "dış dünyadaki sevgi bağlarını ve toplumsal adaleti 'ahlaki açıdan kayıtsız' (adiaphora) saymak, "
            "insan yaşamının kırılgan ama anlamlı dokusunu reddetme riski taşır."
        ),
    },
    # 7. Avicenna (Ibn Sina) - Contingency & Necessary Existent
    {
        "era": "ISLAMIC GOLDEN AGE • AVICENNA",
        "title": "Proof of the Truthful (Burhan es-Sıddıkin)",
        "wiki": "Avicenna",
        "p1": "Var olan her şey ya özü gereği zorunludur (Vacibü'l-Vücud) ya da varlığı/yokluğu eşit olan mümkündür (Mümkünü'l-Vücud).",
        "p2": "Tüm mümkün varlıkların toplam kümesi de kendi başına var olamaz; onu varlığa tercih eden bir dış nedene muhtaçtır.",
        "p3": "Bu dış neden de mümkün olsaydı kümenin parçası olurdu; dolayısıyla nedenler zinciri özü gereği Zorunlu Varlık'ta durmalıdır.",
        "conc": "O halde varlığı kendinden olan Zorunlu Varlık (Vacibü'l-Vücud) zorunlu olarak vardır.",
        "obj": [
            "Her bir parçanın açıklaması küme içinde varsa, 'tüm kümenin' ayrıca dışsal bir nedene ihtiyacı olmayabilir (Terkip Safsatası / Hume).",
            "Gökyüzündeki yıldızlar hiç hareket etmez.",
            "Tıp Kanunu sadece bitkileri anlatır.",
        ],
        "best": 0,
        "analysis": (
            "David Hume ve Bertrand Russell P2'ye itiraz eder: Kümedeki her bir elemanın bir nedeni olması, "
            "evrenin bütününe yeni bir 'mümkün nesne' gibi dışsal neden aramayı gerektirmez (Fallacy of Composition); "
            "ya da maddi evrenin kendisi 'kaba olgu' (brute fact) olabilir."
        ),
    },
    # 8. Anselm - Ontological Argument
    {
        "era": "SCHOLASTICISM • ANSELM",
        "title": "Ontological Argument (Ontolojik Kanıt)",
        "wiki": "Ontological argument",
        "p1": "Tanrı, tanımı gereği 'kendisinden daha büyüğü (yetkini) düşünülemeyen varlık' olarak zihinde anlaşılır.",
        "p2": "Hem zihinde hem gerçeklikte var olmak, yalnızca zihinde (hayalde) var olmaktan daha büyüktür.",
        "p3": "Eğer Tanrı yalnız zihinde var olsaydı, gerçekte de var olan daha büyük bir varlık düşünülebilirdi (çelişki).",
        "conc": "O halde 'kendisinden daha büyüğü düşünülemeyen varlık' hem zihinde hem gerçeklikte zorunlu olarak vardır.",
        "obj": [
            "'Var olmak' bir nesneye büyüklük katan gerçek bir yüklem (sıfat) değildir; kavramı gerçekliğe bağlayan mantıksal niceliktir (Kant).",
            "Manastırda kitaplar Latince yazılıyordu.",
            "Canterbury İngiltere'nin güneyindedir.",
        ],
        "best": 0,
        "analysis": (
            "Gaunilo'nun 'Kayıp Mükemmel Ada' parodisi ve Kant'ın 'Saf Aklın Eleştirisi'ndeki ünlü çürütmesi P2'yi vurur: "
            "100 gerçek taler kavram olarak 100 hayali talerden tek kuruş fazla içermez; 'varlık' (existence) bir "
            "kavramın tanımına eklenerek gerçeklik üretilebilecek bir özellik değildir."
        ),
    },
    # 9. Thomas Aquinas - Five Ways (First Mover)
    {
        "era": "SCHOLASTICISM • AQUINAS",
        "title": "Quinque Viae: First Mover (Beş Yol)",
        "wiki": "Thomas Aquinas",
        "p1": "Dünyada bazı şeylerin hareket/değişim halinde olduğu, yani potansiyelden (kuvve) aktüele (fiile) geçtiği açıktır.",
        "p2": "Hiçbir şey kendi kendisini potansiyelden aktüele geçiremez; her değişen, zaten aktüel olan bir başka şeyce hareket ettirilir.",
        "p3": "Eşzamanlı (hiyerarşik) hareket ettiriciler zinciri sonsuza gidemez; ilk halkası olmazsa ara halkalar da hareket edemez.",
        "conc": "O halde kendisi hareket etmeyen ve saf aktüel (Actus Purus) olan bir İlk Hareket Ettirici vardır.",
        "obj": [
            "Newton eylemsizlik yasasına göre hareketin sürmesi için sürekli bir 'hareket ettirici' gerekmez; potansiyel/aktüel fiziği aşılmıştır.",
            "Paris Üniversitesi'nde dersler sabah başlardı.",
            "Summa Theologiae üç bölümden oluşur.",
        ],
        "best": 0,
        "analysis": (
            "Modern fizik P1-P2'deki Aristotelesçi hareket anlayışını sorgular: Sabit hızlı hareket bir dış "
            "etken gerektirmez ve kuantum ölçeğinde radyoaktif bozunma gibi nedensiz/olasılıksal geçişler "
            "klasik 'her geçişin aktüel nedeni vardır' ilkesini zorlar."
        ),
    },
    # 10. Descartes - Cogito & Dualism
    {
        "era": "RATIONALISM • DESCARTES",
        "title": "Cogito & Mind-Body Dualism (Zihin-Beden İkiliği)",
        "wiki": "René Descartes",
        "p1": "Bedenimin ve dış dünyanın bir aldatıcı cinin yanılsaması olduğunu (var olmadığını) çelişkisizce düşünebilirim.",
        "p2": "Ancak şüphe eden, düşünen zihnimin (res cogitans) var olmadığını düşünemem; çünkü şüphe ederken bile düşünüyorumdur.",
        "p3": "Leibniz Yasası gereği: Biri uzamlı/şüphe edilebilir, diğeri uzamsız/şüphe edilemez olan iki şey aynı töz olamaz.",
        "conc": "O halde düşünen zihin (ruh), maddi bedenden (res extensa) özü gereği tamamen ayrı bir tözdür.",
        "obj": [
            "Bilgi/şüphe bağlamında Leibniz Yasası çalışmaz (Maskeli Adam Safsatası); ayrıca uzamsız zihnin maddi beyni nasıl ittiği açıklanamaz.",
            "Descartes kışın soba başında çalışmayı severdi.",
            "Analitik geometri koordinat eksenlerini kullanır.",
        ],
        "best": 0,
        "analysis": (
            "Prenses Elisabeth'in mektuplarında sorduğu 'Etkileşim Problemi' (uzamsız ruh maddi epifiz bezini "
            "fiziksel kuvvet olmadan nasıl iter?) ve 'Maskeli Adam Safsatası' (babamı tanıdığımı bilip maskeli "
            "adamı tanıdığımı bilmemem, onların farklı kişi olduğunu kanıtlamaz) P3'ü çürütür."
        ),
    },
    # 11. Spinoza - Substance Monism
    {
        "era": "RATIONALISM • SPINOZA",
        "title": "Deus sive Natura (Tek Töz / Tanrı ya da Doğa)",
        "wiki": "Baruch Spinoza",
        "p1": "Töz (Substantia), var olmak ve kavranmak için başka hiçbir şeye ihtiyaç duymayan şeydir.",
        "p2": "Eğer evrende iki ayrı töz olsaydı, birbirlerini sınırlarlardı ve o zaman sonsuz/bağımsız töz olamazlardı.",
        "p3": "Sonsuz niteliklere sahip tek bir töz (Tanrı/Doğa) vardır; zihin ve madde onun yalnızca iki ayrı görünümüdür (modus).",
        "conc": "O halde Tanrı ve Doğa aynı tek gerçekliktir (Deus sive Natura) ve her şey zorunlu geometrik düzenle gerçekleşir.",
        "obj": [
            "Her şey mutlak geometrik zorunlulukla oluyorsa, insanda özgür irade, olumsallık ve ahlaki sorumluluk yanılsamaya dönüşür.",
            "Spinoza Amsterdam'da mercek yontarak geçinmiştir.",
            "Etika kitabı Latince yazılmıştır.",
        ],
        "best": 0,
        "analysis": (
            "Leibniz ve Kant, Spinoza'nın katı determinizmine (necessitarianism) itiraz eder: Eğer başka türlü "
            "olabilecek hiçbir olası dünya yoksa ve her eylem bir üçgenin iç açıları gibi zorunluysa, pişmanlık, "
            "seçim ve normatif ahlak anlamını yitirir."
        ),
    },
    # 12. John Locke - Personal Identity
    {
        "era": "EMPIRICISM • JOHN LOCKE",
        "title": "Memory Criterion of Identity (Kişisel Özdeşlik)",
        "wiki": "John Locke",
        "p1": "Bir kişiyi (Person) zaman içinde 'aynı ben' yapan şey, sürekli değişen atomları veya görünmeyen tözsel ruhu değildir.",
        "p2": "Kişisel özdeşlik, bilincin ve otobiyografik belleğin (hafızanın) geçmişteki deneyimlere ne kadar uzanabildiğiyle kurulur.",
        "p3": "Eğer bir prensin bilinci ve anıları bir kunduracının bedenine aktarılsaydı, o kişi ahlaken ve hukuken prens olurdu.",
        "conc": "O halde 'Ben', yalnızca geçmişteki eylemlerini bilinçli olarak hatırlayabildiği ölçüde o geçmişteki kişiyle aynıdır.",
        "obj": [
            "Cesur Subay Çelişkisi (Thomas Reid): Yaşlı general genç subaylığını, subay da çocukluğunu hatırlar ama general çocukluğunu hatırlamaz!",
            "İngiltere'de 1688'de Şanlı Devrim yaşanmıştır.",
            "Tabula rasa 'boş levha' demektir.",
        ],
        "best": 0,
        "analysis": (
            "İskoç filozof Thomas Reid P2'yi çökertir: Özdeşlik geçişlidir (A=B ve B=C ise A=C olmalıdır), oysa "
            "hafıza geçişli değildir! Yaşlı general (C) subaylığını (B), subay (B) elma çalan çocuğu (A) hatırlar, "
            "fakat C, A'yı unutmuştur. Locke'a göre C hem A ile aynı kişidir hem de değildir."
        ),
    },
    # 13. David Hume - Problem of Induction
    {
        "era": "EMPIRICISM • DAVID HUME",
        "title": "Problem of Induction (Tümevarım Sorunu)",
        "wiki": "David Hume",
        "p1": "Tüm akıl yürütmelerimiz ya kavramlar arası ilişkilere (mantık/matematik) ya da deneyimlenen olgulara dayanır.",
        "p2": "'Geleceğin geçmişe benzeyeceği' (Doğa Tekdüzeliği İlkesi) ne mantıksal bir zorunluluktur ne de doğrudan gözlemlenebilir.",
        "p3": "Tümevarımı 'geçmişte hep işe yaradı' diyerek kanıtlamaya çalışmak, kanıtlanacak ilkeyi varsayan kısır döngüdür.",
        "conc": "O halde tümevarım ve nedensellik inancımız rasyonel bir kanıta değil, yalnızca psikolojik alışkanlığa (custom/habit) dayanır.",
        "obj": [
            "Kesin doğrulama imkânsız olsa da bilimsel kuramlar tümevarımla değil, yanlışlanabilir hipotezlerin sınanmasıyla ilerler (Popper).",
            "Edinburgh İskoçya'nın başkentidir.",
            "Bilardo topları fildişinden yapılırdı.",
        ],
        "best": 0,
        "analysis": (
            "Karl Popper, Hume'un tümevarımın mantıksal olarak doğrulanamayacağı tespitini kabul eder; ancak bilimin "
            "tümevarıma muhtaç olmadığını, 'varsayım ve yanlışlama' (conjectures and refutations) ile tümdengelimsel "
            "olarak rasyonel kaldığını savunur."
        ),
    },
    # 14. Immanuel Kant - Categorical Imperative
    {
        "era": "GERMAN IDEALISM • KANT",
        "title": "Categorical Imperative (Kesin Buyruk)",
        "wiki": "Immanuel Kant",
        "p1": "Ahlaki bir yasa koşullu arzularımıza değil, her rasyonel varlık için geçerli evrensel akla dayanmalıdır.",
        "p2": "Yalnızca aynı zamanda evrensel bir doğa yasası olmasını isteyebileceğin maksim (ilke) uyarınca eylemde bulun.",
        "p3": "Yalan söylemek veya sözünden dönmek evrenselleştirildiğinde 'söz verme' kurumunun kendisi mantıksal olarak çöker.",
        "conc": "O halde rasyonel varlıkları asla salt araç olarak değil, her zaman başlı başına amaç olarak görmek mutlak ödevdir.",
        "obj": [
            "Kapıdaki Katil Vakası: Masum birini kurtarmak için bile yalan söylemeyi yasaklayan mutlak kural, ödevler çatışmasında ahlaki felakete yol açar.",
            "Kant Königsberg şehrinden hiç ayrılmamıştır.",
            "Saf Aklın Eleştirisi 1781'de yayımlanmıştır.",
        ],
        "best": 0,
        "analysis": (
            "Benjamin Constant ve modern etikçiler, Kant'ın 'sonuçlardan tamamen bağımsız' katı deontolojisine "
            "itiraz eder: İki ahlaki ödev çatıştığında (doğruyu söylemek vs. masum bir hayatı korumak), maksimi "
            "bağlamdan kopuk biçimde uygulamak rasyonel ahlakın ruhuna aykırıdır."
        ),
    },
    # 15. Hegel - Master-Slave Dialectic
    {
        "era": "GERMAN IDEALISM • HEGEL",
        "title": "Master-Slave Dialectic (Efendi-Köle Diyalektiği)",
        "wiki": "Georg Wilhelm Friedrich Hegel",
        "p1": "Öz-bilinç (Selbstbewusstsein), ancak bir başka öz-bilinç tarafından tanındığında (Anerkennung) gerçeklik kazanır.",
        "p2": "Ölüm-kalım mücadelesinde hayatını riske atan 'Efendi', hayatta kalmayı seçip boyun eğen ise 'Köle' olur.",
        "p3": "Fakat Efendi, özgür olmayan bir köleden aldığı tanınmayla tatmin olamazken; Köle doğayı emekle dönüştürerek gerçek özerkliği kazanır.",
        "conc": "O halde tahakküme dayalı eşitsiz tanınma kendi çelişkisiyle tersine döner; gerçek özgürlük ancak karşılıklı eşit tanınmayla mümkündür.",
        "obj": [
            "Tarihsel kölelik ve sömürü sistemleri salt 'bilinç/emek diyalektiği' ile kendiliğinden özgürlüğe dönüşmez; maddi ve politik devrim gerekir (Marx).",
            "Jena Savaşı 1806 yılında yapılmıştır.",
            "Tinin Fenomenolojisi Almanca yazılmıştır.",
        ],
        "best": 0,
        "analysis": (
            "Genç Hegelciler ve Karl Marx P3'ü materyalist açıdan eleştirir: Yabancılaşmış emek köleye zihinsel "
            "bir bilinç kazandırsa da, üretim araçlarının mülkiyeti değişmedikçe diyalektik uzlaşma yalnızca "
            "düşüncede kalır."
        ),
    },
    # 16. Karl Marx - Historical Materialism & Alienation
    {
        "era": "MATERIALISM • KARL MARX",
        "title": "Base, Superstructure & Alienation (Yabancılaşma)",
        "wiki": "Karl Marx",
        "p1": "İnsanların bilinci toplumsal varlıklarını belirlemez; tersine maddi üretim ilişkileri (Altyapı) hukuk, siyaset ve ideolojiyi (Üstyapı) şekillendirir.",
        "p2": "Kapitalist üretimde işçinin ürettiği değer (artı-değer) kendisinden koparılıp sermayeye dönüşür.",
        "p3": "Ürettiği ürüne, üretim sürecine ve kendi insan doğasına (Gattungswesen) yabancılaşan emekçi, sermaye biriktikçe daha da bağımlılaşır.",
        "conc": "O halde yabancılaşmanın aşılması bilinç reformuyla değil, üretim ilişkilerinin ve mülkiyet yapısının dönüştürülmesiyle mümkündür.",
        "obj": [
            "Kültür, din, bilim ve hukuk yalnızca ekonomik altyapının pasif yansıması değildir; ekonomiyi bizzat şekillendiren özerk güce sahiptir (Weber).",
            "Das Kapital Londra'da British Museum kütüphanesinde yazılmıştır.",
            "Buhar makinesi 18. yüzyılda geliştirilmiştir.",
        ],
        "best": 0,
        "analysis": (
            "Max Weber ('Protestan Ahlakı ve Kapitalizmin Ruhu') ve Frankfurt Okulu P1'deki katı ekonomik "
            "indirgemeciliğe itiraz eder: Kültürel değerler, bürokrasi ve fikirler yalnızca altyapının gölgesi "
            "değil, tarihsel değişimin bağımsız motorlarıdır."
        ),
    },
    # 17. John Stuart Mill - Harm Principle & Utilitarianism
    {
        "era": "UTILITARIANISM • J. S. MILL",
        "title": "The Harm Principle (Zarar İlkesi ve Faydacılık)",
        "wiki": "John Stuart Mill",
        "p1": "Ahlaki açıdan doğru eylem, en fazla sayıda canlı için en yüksek toplam mutluluğu (nitelikli hazzı) üreten eylemdir.",
        "p2": "Bireysel özgürlük ve düşünce çeşitliliği, insanlığın uzun vadeli mutluluğunun ve hakikate ulaşmasının vazgeçilmez koşuludur.",
        "p3": "Toplumun veya devletin bir bireyin özgürlüğüne zorla müdahale etmesinin tek meşru gerekçesi, başkalarına verilen somut zararı önlemektir.",
        "conc": "O halde kişinin yalnızca kendisini ilgilendiren konularda (bedeni ve zihni üzerinde) birey mutlak egemendir.",
        "obj": [
            "Faydacılık toplam mutluluğu artıracaksa masum bir azınlığın haklarının feda edilmesini meşrulaştırabilir; adalet faydaya indirgenemez (Rawls).",
            "Mill küçük yaşta Yunanca öğrenmiştir.",
            "Londra'da sisli gün sayısı fazladır.",
        ],
        "best": 0,
        "analysis": (
            "John Rawls ('Bir Adalet Kuramı') P1 ile P3 arasındaki gerilimi gösterir: Eğer en üst ilke 'toplam "
            "faydayı maksimize etmek' ise, çoğunluğun hazzı için bireyin dokunulmaz hakları çiğnenebilir; "
            "'bireylerin ayrı oluşu' (separateness of persons) faydacı toplamada kaybolur."
        ),
    },
    # 18. Søren Kierkegaard - Teleological Suspension & Leap of Faith
    {
        "era": "EXISTENTIALISM • KIERKEGAARD",
        "title": "Absurd & Leap of Faith (İman Sıçraması)",
        "wiki": "Søren Kierkegaard",
        "p1": "Nesnel bilimsel ve tarihsel bilgi her zaman yalnızca bir 'yaklaşıklık' (approximation) sunar; sonsuz kesinlik veremez.",
        "p2": "Oysa varoluşsal özne, kendi sonlu yaşamının anlamı konusunda sonsuz bir tutkuya ve acil karar zorunluluğuna sahiptir.",
        "p3": "Nesnel belirsizlik ile öznel sonsuz tutku arasındaki bu uçurum (Paradox/Absurd) rasyonel bir sistemle kapatılamaz.",
        "conc": "O halde hakiki varoluş, nesnel güvenceleri bırakıp kaygıyı (Angst) üstlenerek yapılan öznel 'İman Sıçraması'nda (Leap of Faith) gerçekleşir.",
        "obj": [
            "Akılsal ölçütleri tamamen askıya alan bir sıçrama, yüce ruhsal hakikat ile tehlikeli fanatizmi birbirinden ayırt etme imkânını kaybeder.",
            "Kopenhag Danimarka'nın başkentidir.",
            "Kierkegaard yazılarını takma isimlerle yayımlamıştır.",
        ],
        "best": 0,
        "analysis": (
            "Albert Camus ('Sisifos Söyleni') ve rasyonalist eleştirmenler P3-Sonuç geçişine itiraz eder: "
            "Camus'ye göre absürtle yüzleşip akıldışı bir sıçrama yapmak 'felsefi intihar'dır; etik olan, "
            "etik ve rasyonel denetimi terk etmeden absürtle berrak bilinçle yaşamaktır."
        ),
    },
    # 19. Friedrich Nietzsche - Genealogy of Morals & Eternal Recurrence
    {
        "era": "CONTINENTAL • NIETZSCHE",
        "title": "Slave Morality & Amor Fati (Ahlakın Soykütüğü)",
        "wiki": "Friedrich Nietzsche",
        "p1": "Tarihsel olarak 'iyi' ve 'kötü' kavramları gökten inmemiş, yaşamı olumlayan güçlülerin (Efendi Ahlakı) kendilerini 'iyi' tanımlamasıyla doğmuştur.",
        "p2": "Ezilenlerin hıncı (Ressentiment), güç, gurur ve yaratıcılığı 'günah/kötü'; acizliği ve boyun eğmeyi ise 'erdem/iyi' ilan ederek değerleri tersyüz etmiştir.",
        "p3": "Bu yaşam-karşıtı değerler, insanın kendi potansiyelini aşmasını (Übermensch) ve bu dünyayı sevmesini felç eden nihilizme yol açar.",
        "conc": "O halde tüm değerler yeniden değerlendirilmeli; kişi yaşamını sonsuz kez tekrar yaşayacakmışçasına (Amor Fati / Bengi Dönüş) olumlamalıdır.",
        "obj": [
            "Bir ahlaki değerin tarihsel kökeninde zayıfların tepkisi olması, merhamet ve eşit hakların bugün rasyonel olarak yanlış olduğunu kanıtlamaz (Köken Safsatası).",
            "Nietzsche İsviçre'nin Sils Maria köyünde yürüyüş yapardı.",
            "Zerdüşt antik bir Pers peygamberidir.",
        ],
        "best": 0,
        "analysis": (
            "Analitik etikçiler P2-P3 geçişinde 'Genetic Fallacy' (Köken Safsatası) tehlikesine dikkat çeker: "
            "Bir fikrin psikolojik doğuş öyküsü (soykütüğü), onun normatif geçerliliğini tek başına çürütmez; "
            "merhamet ve evrensel insan onuru hınçtan bağımsız olarak da savunulabilir."
        ),
    },
    # 20. Bertrand Russell - Russell's Paradox
    {
        "era": "ANALYTIC PHILOSOPHY • RUSSELL",
        "title": "Russell's Paradox (Kendi Kendini İçermeyen Kümeler)",
        "wiki": "Bertrand Russell",
        "p1": "Naif küme kuramına (Frege) göre her anlamlı özellik bir küme tanımlar: R, 'kendi kendisinin elemanı olmayan tüm kümelerin kümesi' olsun.",
        "p2": "Eğer R kendi kendisinin elemanıysa (R ∈ R), tanımı gereği kendi kendisinin elemanı olmamalıdır (R ∉ R).",
        "p3": "Eğer R kendi kendisinin elemanı değilse (R ∉ R), tanım koşulunu sağladığı için kendi kendisinin elemanı olmalıdır (R ∈ R).",
        "conc": "O halde sınırsız küme oluşturma aksiyomu (R ∈ R ⇔ R ∉ R) mantıksal çelişki üretir; matematiksel mantık Tipler Kuramı / ZFC ile sınırlandırılmalıdır.",
        "obj": [
            "Tipler Kuramı ve ZFC çelişkiyi önlese de Gödel'in Eksiklik Teoremi, yeterince güçlü hiçbir biçimsel sistemin kendi tutarlılığını içeriden kanıtlayamayacağını gösterir.",
            "Principia Mathematica üç ciltlik bir eserdir.",
            "Cambridge Üniversitesi İngiltere'dedir.",
        ],
        "best": 0,
        "analysis": (
            "Russell'ın 1901'de Frege'ye yazdığı mektupla matematiğin temellerini sarsan bu paradoks, Zermelo-Fraenkel "
            "(ZFC) küme kuramıyla çözülmüştür; ancak 1931'de Kurt Gödel, Russell'ın 'tüm matematiği eksiksiz ve "
            "tutarlı tek bir mantık sistemine indirgeme' (Logicism) hayalinin imkânsız olduğunu kanıtlamıştır."
        ),
    },
    # 21. Ludwig Wittgenstein - Private Language Argument
    {
        "era": "ANALYTIC • WITTGENSTEIN",
        "title": "Private Language Argument (Özel Dil Argümanı)",
        "wiki": "Ludwig Wittgenstein",
        "p1": "Bir kelimenin anlamı, zihindeki gizli bir nesneye yapıştırılan etiket değil, bir dil oyunu içindeki kurallı kullanımıdır (Anlam = Kullanım).",
        "p2": "Yalnızca konuşanın kendi içsel duyumlarına referans veren ve başkasınca asla anlaşılamayan 'özel bir dil'de (S imgesi), doğru hatırlama ile doğru hatırladığını sanma arasında fark yoktur.",
        "p3": "'Bana doğru görünen şey doğrudur' dendiğinde 'doğru' kavramı ve kural izleme (rule-following) tamamen çöker.",
        "conc": "O halde ilkece yalnızca tek bir kişinin anlayabileceği tamamen 'özel bir dil' mantıksal olarak imkânsızdır; anlam ve zihin toplumsaldır.",
        "obj": [
            "Doğuştan gelen bilişsel/kavramsal temsiller ('Düşünce Dili' / Mentalese - Fodor) kamusal dilden önce bireyin beyninde kurallı biçimde işleyebilir.",
            "Wittgenstein Viyanalı bir aileden geliyordu.",
            "Tractatus 7 ana önermeden oluşur.",
        ],
        "best": 0,
        "analysis": (
            "Jerry Fodor ve modern bilişsel bilimciler P2-P3'e itiraz eder: İnsanların kamusal dili öğrenebilmesi "
            "için bile beyinde doğuştan gelen içsel bir sembolik temsil sisteminin (Language of Thought) bulunması "
            "gerekir ve bunun doğruluk koşulu dış dünyayla nedensel bağla sağlanır."
        ),
    },
    # 22. Karl Popper - Falsificationism
    {
        "era": "PHILOSOPHY OF SCIENCE • POPPER",
        "title": "Demarcation & Falsification (Yanlışlanabilirlik)",
        "wiki": "Karl Popper",
        "p1": "Evrensel bir bilimsel yasa ('Tüm kuğular beyazdır') milyonlarca gözlemle kesin olarak doğrulanamaz, ancak tek bir siyah kuğu gözlemiyle mantıksal olarak yanlışlanabilir (Modus Tollens).",
        "p2": "Gerçekleşebilecek her olası olayı kendi lehine kanıt sayan kuramlar her şeyi açıklıyor görünürken aslında hiçbir şeyi yasaklamaz.",
        "p3": "Bir kuramın bilimsel olmasının ölçütü (Demarcation), hangi gözlem gerçekleşirse çürüyeceğini önceden açıkça ortaya koymasıdır.",
        "conc": "O halde ilkece hiçbir gözlemle yanlışlanamayan iddialar ampirik bilim değil, sözde-bilim veya metafiziktir.",
        "obj": [
            "Duhem-Quine Tezi: Hiçbir hipotez tek başına sınanamaz; ters bir gözlem çıktığında kuramın çekirdeği yerine yardımcı varsayımlar değiştirilir (Kuhn/Lakatos).",
            "Popper Londra Ekonomi Okulu'nda ders vermiştir.",
            "Teleskoplar cam merceklerden yapılır.",
        ],
        "best": 0,
        "analysis": (
            "Pierre Duhem, W.V.O. Quine ve Thomas Kuhn ('Bilimsel Devrimlerin Yapısı') P1-P3'e itiraz eder: "
            "Bilim insanları Uranüs'ün yörüngesi Newton yasasına uymadığında Newton'u çöpe atmamış, yardımcı "
            "hipotezi değiştirerek Neptün gezegenini keşfetmiştir; kuramlar bütünsel ağlar (holism) olarak sınanır."
        ),
    },
    # 23. John Searle - Chinese Room Argument
    {
        "era": "PHILOSOPHY OF MIND • SEARLE",
        "title": "The Chinese Room (Çince Odası Argümanı)",
        "wiki": "Chinese room",
        "p1": "Çince bilmeyen bir insan kapalı bir odada İngilizce bir kural kitabına bakarak Çince sembolleri eşleştirip dışarıya kusursuz Çince yanıtlar verebilir (Turing Testini geçer).",
        "p2": "Odadaki kişi (veya bilgisayar CPU'su) yalnızca biçimsel sembol manipülasyonu (Syntax) yapmaktadır; kelimelerin ne anlama geldiğini (Semantics) zerre kadar anlamaz.",
        "p3": "Salt sözdizimsel (syntactic) kuralların işletilmesi, tek başına anlambilimsel içerik (semantics) ve bilinçli anlama üretmeye yetmez.",
        "conc": "O halde 'Güçlü Yapay Zekâ' (uygun programı çalıştıran her sistemin gerçekten zihin sahibi olduğu iddiası) yanlıştır.",
        "obj": [
            "Sistemler Yanıtı: Tek bir nöron da Türkçe anlamaz; anlamayı yapan odadaki tek kişi değil, kural kitabı, bellek ve işlemcinin oluşturduğu bütün sistemdir.",
            "Çin yazısı binlerce karakterden oluşur.",
            "Bilgisayarlar ikili (binary) sayı sistemi kullanır.",
        ],
        "best": 0,
        "analysis": (
            "İşlevselcilerin (Functionalism) 'Sistemler Yanıtı' P2'yi hedef alır: Odadaki adam bütün sistemin "
            "yalnızca bir alt-parçasıdır (CPU gibidir); nasıl ki beynimizdeki tek bir nöron 'ben anlıyorum' "
            "diyemez ama tüm beyin anlarsa, odanın tamamı da Çince anlamaktadır."
        ),
    },
    # 24. Thomas Nagel & Nick Bostrom - Consciousness & Simulation
    {
        "era": "CONTEMPORARY • NAGEL & BOSTROM",
        "title": "Qualia & Simulation Trilemma (Bilinç ve Simülasyon)",
        "wiki": "Thomas Nagel",
        "p1": "Bir yarasanın sonar duyusuyla ilgili tüm fiziksel/nörolojik olguları bilsek bile, 'yarasa olmanın nasıl bir his olduğu' (Qualia / Öznel Deneyim) üçüncü şahıs fiziğine indirgenemez (Nagel).",
        "p2": "Öte yandan bilinç yazılımla taklit edilebiliyorsa (Substrate Independence), gelecekteki uygarlıklar milyarlarca ata-simülasyonu çalıştırabilir (Bostrom).",
        "p3": "Eğer simüle edilen bilinçlerin sayısı biyolojik orijinallerden milyarlarca kat fazlaysa, rastgele bir gözlemcinin simülasyonda olma olasılığı 1'e yaklaşır.",
        "conc": "O halde ya öznel bilinç (Qualia) salt hesaplamaya indirgenemez ve simülasyon argümanı çöker, ya da simüle edilmiş bir gerçeklikte yaşıyor olmamız muhtemeldir.",
        "obj": [
            "Fizikalizm / Yanılsamacılık (Dennett): Fiziksel beyin süreçlerinden bağımsız, gizemli 'Qualia' diye bir şey yoktur; ya da kuantum fiziği simülasyonu imkânsız kılar.",
            "Yarasalar geceleri uçan memelilerdir.",
            "Mikroçipler silikondan üretilir.",
        ],
        "best": 0,
        "analysis": (
            "Modern zihin felsefesinin en keskin kavşağıdır: Nagel ve Chalmers'ın 'Bilincin Zor Problemi' (Hard Problem) "
            "doğruysa, bilinç salt algoritmaya indirgenemediği için Bostrom'un simülasyon öncülü (P2) reddedilir; "
            "eğer işlevselcilik doğruysa simülasyon üçlemi kaçınılmaz hale gelir."
        ),
    },
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    wp_titles = load_wp_titles()
    assert len(ARGUMENTS) == 24

    out = bytearray()
    out += struct.pack("<8sHHI", b"CNLG0001", len(ARGUMENTS), 0, 0)
    assert len(out) == 16

    for idx, arg in enumerate(ARGUMENTS):
        wtitle = arg["wiki"]
        if wtitle not in wp_titles:
            wtitle = "Philosophy"
        assert wtitle in wp_titles, f"Missing wiki title: {wtitle}"

        rec = bytearray()
        rec += pack_utf8(arg["era"], 36)
        rec += pack_utf8(arg["title"], 48)
        rec += pack_utf8(wtitle, 48)
        rec += pack_utf8(arg["p1"], 160)
        rec += pack_utf8(arg["p2"], 160)
        rec += pack_utf8(arg["p3"], 160)
        rec += pack_utf8(arg["conc"], 160)
        for i in range(3):
            rec += pack_utf8(arg["obj"][i], 120)
        rec += struct.pack("<BBBB", arg["best"], 0, 0, 0)
        rec += pack_utf8(arg["analysis"], 340)
        assert len(rec) == 1476, f"Record {idx} size {len(rec)}"
        out += rec

    assert len(out) == 35440
    with open(OUT_PATH, "wb") as f:
        f.write(out)
    print(f"Wrote {OUT_PATH}: {len(out)} bytes ({len(ARGUMENTS)} arguments)")

if __name__ == "__main__":
    main()
