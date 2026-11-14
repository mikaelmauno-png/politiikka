"""Which election-compass statements form the two nelikenttä axes, per election.

Each entry: (start of the statement text as Yle wrote it, direction).
direction +1: agreeing moves the candidate RIGHT (economy) / CONSERVATIVE (values).
direction -1: agreeing moves the candidate LEFT / LIBERAL.

Climate and environment statements are deliberately left out of both axes.
Statements are matched by their beginning; a statement that matches nothing (or several
columns) stops the build, so a typo can never silently drop an item.
"""

ELECTIONS = [
    {
        "key": "e2019", "label": "Eduskuntavaalit 2019", "short": "EK 2019", "date": "2019-04",
        "economy": [
            ("Kun valtion menoja ja tuloja tasapainotetaan, se on tehtävä mieluummin menoja karsimalla", +1),
            ("Sosiaali- ja terveyspalvelut on tuotettava ensisijaisesti julkisina palveluina", -1),
            ("Vanhustenhoidon ulkoistamista yksityisille toimijoille tulee lisätä", +1),
            ("On oikein, että yhteiskunnassa jotkut ryhmät ovat paremmassa asemassa kuin toiset", +1),
        ],
        "values": [
            ("Parantumattomasti sairaalla on oltava oikeus eutanasiaan", -1),
            ("Sukupuolen korjaamisen tulee olla mahdollista myös alle 18-vuotiaille", -1),
            ("Viinit ja vahvat oluet pitää saada ruokakauppoihin", -1),
            ("Perhevapaita pitää uudistaa niin, että vapaat jakautuvat tasan", -1),
            ("Maahanmuuttajien määrän kasvu on lisännyt turvattomuutta", +1),
            ("Vihapuhe tulee määritellä ja asettaa rangaistavaksi", -1),
            ("Perinteiset arvot ovat hyvän elämän perusta", +1),
            ("Suomessa tarvitaan nyt koviakin keinoja järjestyksen", +1),
            ("On olemassa pyhiä tai muuten yksilöä suurempia asioita", +1),
        ],
    },
    {
        "key": "k2021", "label": "Kuntavaalit 2021", "short": "KV 2021", "date": "2021-06",
        "economy": [
            ("Eniten ansaitsevat ihmiset voisivat maksaa enemmän kuntaveroa", -1),
            ("Kun kunnan menoja ja tuloja tasapainotetaan, se on tehtävä mieluummin menoja karsimalla", +1),
            ("Kaikille vanhuksille on taattava oikeus palvelukotipaikkaan", -1),
            ("Lähikirjastoja tarvitaan nykyistä vähemmän", +1),
        ],
        "values": [
            ("Kuntani pärjäisi hyvin ilman maahanmuuttoa", +1),
            ("Kuntani pitää edistää oleskeluluvan saaneiden turvapaikanhakijoiden kotoutumista", -1),
            ("Kuntani pitää tarjota maksuton ehkäisy alle 25-vuotiaille", -1),
            ("Kuntani pitää järjestää huumeidenkäyttäjille mahdollisuus vaihtaa", -1),
            ("Koulun on pidettävä yllä kristillisiä perinteitä", +1),
            ("Politiikassa tarvitaan vahvoja johtajia", +1),
            ("Kuntani pitää järjestää liputus Pride-tapahtuman kunniaksi", -1),
            ("Äänioikeuden ikäraja kuntavaaleissa pitäisi laskea 16 vuoteen", -1),
        ],
    },
    {
        "key": "e2023", "label": "Eduskuntavaalit 2023", "short": "EK 2023", "date": "2023-04",
        "economy": [
            ("Suomessa on liian helppo elää yhteiskunnan tukien varassa", +1),
            ("Kun valtion menoja ja tuloja tasapainotetaan, se on tehtävä mieluummin menoja vähentämällä", +1),
            ("Valtion on mieluummin otettava lisää velkaa kuin vähennettävä palveluita", -1),
            ("Pääomatulojen verotusta on kiristettävä", -1),
            ("Palkoista pitäisi sopia ensisijaisesti työpaikoilla", +1),
            ("Ansiosidonnaisen työttömyysturvan kestoa pitää lyhentää", +1),
            ("Eläkeläisköyhyyttä pitää vähentää korottamalla takuueläkettä", -1),
            ("Sosiaali- ja terveyspalvelut on tuotettava ensisijaisesti julkisina palveluina", -1),
            ("Korkeakouluissa on otettava käyttöön lukukausimaksut", +1),
        ],
        "values": [
            ("Suomen pitää ottaa käyttöön kolmas virallinen sukupuoli", -1),
            ("Kannabiksen käyttö pitää laillistaa", -1),
            ("Suomeen ei pidä avata huumeiden käyttöhuoneita", +1),
            ("Viinin myynti pitää sallia jatkossakin vain Alkossa", +1),
            ("Suomen pitää vastaanottaa nykyistä vähemmän kiintiöpakolaisia", +1),
            ("Työperäistä maahanmuuttoa tarvitaan", -1),
            ("Suomen pitää pystyä karkottamaan nykyistä helpommin rikoksia tehneitä", +1),
        ],
    },
    {
        "key": "a2025", "label": "Alue- ja kuntavaalit 2025", "short": "AV 2025", "date": "2025-04",
        "economy": [
            ("Julkisen terveydenhuollon asiakasmaksuja pitäisi alentaa", -1),
            ("On oikein, että julkisella rahalla tuetaan ihmisten käymistä yksityisessä terveydenhuollossa", +1),
            ("Vanhusten ympärivuorokautiseen palveluasumiseen pitää lisätä paikkoja", -1),
            ("Jos kunnan tuloja ja menoja tasapainotetaan, se on tehtävä mieluummin menoja leikkaamalla", +1),
            ("Pääomatulot on pidettävä kunnallisverotuksen ulkopuolella", +1),
            ("Kunnan on ostettava ensisijaisesti palveluita omistamiltaan yhtiöiltä", -1),
            ("Hyvinvointialueiden pitää tehdä säästöt vaaditussa ajassa", +1),
            ("Kirjastoja pitäisi muuttaa itsepalvelukirjastoiksi", +1),
        ],
        "values": [
            ("Hyvinvointialueeni on tarjottava paperittomille ihmisille", -1),
            ("Hyvinvointialueen pitäisi luopua nuorten maksuttomasta ehkäisystä", +1),
            ("Hyvinvointialueeni pitää järjestää koulutusta seksuaalisen suuntautumisen", -1),
            ("Huumeidenkäyttäjillä pitää olla mahdollisuus vaihtaa likaiset neulat", -1),
            ("Koulun on pidettävä yllä kristillisiä perinteitä", +1),
            ("Maahanmuuttajat vahvistavat kotikuntani elinvoimaa", -1),
            ("Kuntani pitää kieltäytyä vastaanottamasta kiintiöpakolaisia", +1),
            ("Kuntani pitää rahoittaa tapahtumia, jotka lisäävät erilaisten kulttuurien", -1),
            ("Kuntani pitää säästää maahanmuuttajien kotouttamisen palveluista", +1),
            ("Kotikuntani olisi hyvä osoittaa tukensa sukupuoli- ja seksuaalivähemmistöille", -1),
        ],
    },
]

# Party names in Yle's files -> our abbreviations
PARTY_ALIASES = {
    "Kokoomus": "KOK", "Perussuomalaiset": "PS", "SDP": "SDP", "Sosialidemokraatit": "SDP",
    "Keskusta": "KESK", "Vasemmistoliitto": "VAS", "Vihreät": "VIHR", "RKP": "RKP",
    "Kristillisdemokraatit": "KD", "Liike Nyt": "LIIK",
}
